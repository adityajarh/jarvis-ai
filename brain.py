import datetime
import os
import re
import random
import webbrowser
import base64
import smtplib
import requests

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import quote_plus
from dotenv import load_dotenv
from groq import Groq
from models import db, User, Note, ResetCode

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

pending_shutdown = False


def find_user_by_email(email):
    email = email.strip().lower()
    return User.query.filter_by(email=email).first()


def create_user(name, email, password):
    email = email.strip().lower()

    if find_user_by_email(email):
        return None, "This email is already registered."

    user = User(
        name=name.strip().split(" ")[0],
        email=email,
        password_hash=generate_password_hash(password)
    )

    db.session.add(user)
    db.session.commit()

    return user, None


def verify_login(email, password):
    user = find_user_by_email(email)

    if not user:
        return None

    if not check_password_hash(user.password_hash, password):
        return None

    return user


def update_user_password(email, new_password):
    user = find_user_by_email(email)

    if not user:
        return False

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    return True


def add_note(text, user_id=None):
    note = Note(
        user_id=user_id,
        text=text
    )

    db.session.add(note)
    db.session.commit()

    return "Note saved successfully."


def get_notes(user_id=None):
    notes = Note.query.filter_by(user_id=user_id).order_by(Note.created_at.desc()).all()

    return [
        {
            "id": n.id,
            "text": n.text,
            "archived": n.archived,
            "created_at": n.created_at.strftime("%d %b %Y %H:%M")
        }
        for n in notes
    ]


def delete_note(note_id):
    note = Note.query.get(note_id)

    if note:
        db.session.delete(note)
        db.session.commit()
        return "Note deleted successfully."

    return "Note not found."


def clear_notes():
    Note.query.delete()
    db.session.commit()
    return "All notes cleared."


def generate_reset_code(email):
    email = email.strip().lower()

    ResetCode.query.filter_by(email=email).delete()

    code = str(random.randint(100000, 999999))
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

    reset_entry = ResetCode(
        email=email,
        code=code,
        expires_at=expires_at,
        attempts=0,
        verified=False
    )

    db.session.add(reset_entry)
    db.session.commit()

    return code


def verify_reset_code(email, entered_code):
    email = email.strip().lower()
    entry = ResetCode.query.filter_by(email=email).first()

    if not entry:
        return "not_found"

    if entry.attempts >= 5:
        return "blocked"

    if datetime.datetime.utcnow() > entry.expires_at:
        return "expired"

    if entry.code == entered_code:
        entry.verified = True
        db.session.commit()
        return "correct"

    entry.attempts += 1
    db.session.commit()
    return "incorrect"


def is_reset_verified(email):
    email = email.strip().lower()
    entry = ResetCode.query.filter_by(email=email).first()

    if not entry:
        return False

    return entry.verified


def clear_reset_code(email):
    email = email.strip().lower()
    ResetCode.query.filter_by(email=email).delete()
    db.session.commit()


def send_otp_email(name, email, code, purpose="reset"):
    try:
        api_key = os.getenv("BREVO_API_KEY")

        if purpose == "signup":
            subject = "Your JARVIS Verification Code"
            intro = "Welcome to JARVIS.<br><br>Your verification code is:"
            footer = "If you didn't request this verification, you can safely ignore this email."
        else:
            subject = "Your JARVIS Password Reset Code"
            intro = "Your password reset code is:"
            footer = "If you didn't request a password reset, you can safely ignore this email."

        greeting = f"Hi {name}," if name else "Hi,"

        html_content = f"""
        <p>{greeting}</p>
        <p>{intro}</p>
        <h2>{code}</h2>
        <p>This code will expire in 10 minutes.</p>
        <p>For your security, never share this code with anyone.</p>
        <p>{footer}</p>
        <p>— JARVIS</p>
        """

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json",
            },
            json={
                "sender": {"name": "JARVIS", "email": "jarhisdevil@gmail.com"},
                "to": [{"email": email}],
                "subject": subject,
                "htmlContent": html_content,
            },
            timeout=10,
        )

        if response.status_code in (200, 201):
            return True
        else:
            print("BREVO API ERROR:", response.status_code, response.text)
            return False

    except Exception as e:
        print("OTP EMAIL ERROR:", e)
        return False

def has_word(text, word):
    return re.search(rf"\b{re.escape(word)}\b", text) is not None

def is_command(text, phrases):
    return any(text == phrase for phrase in phrases)

def open_website(url, message):
    webbrowser.open(url)
    return message

def open_app(command, message):
    os.system(command)
    return message

def open_windows_app(app_id, message):
    os.system(rf'explorer shell:AppsFolder\{app_id}')
    return message

def open_folder(folder_path, message):
    os.startfile(folder_path)
    return message

def open_onedrive_desktop_shortcut(shortcut_name, message):
    shortcut_path = os.path.join(
        os.environ["USERPROFILE"],
        "OneDrive",
        "Desktop",
        shortcut_name
    )
    os.startfile(shortcut_path)
    return message

def google_search(query, message=None):
    safe_query = quote_plus(query)
    webbrowser.open(f"https://www.google.com/search?q={safe_query}")

    if message:
        return message

    return f"Searching Google for {query}"


def ask_ai(command, history=None):
    if history is None:
        history = []

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are JARVIS, a helpful AI assistant created by Aditya.\n\n"

                    "IMPORTANT CONVERSATION RULES:\n"
                    "1. Always read the user's ENTIRE latest message before answering.\n"
                    "2. Never answer only the first word, greeting, or first phrase of the message.\n"
                    "3. A message may contain one question, multiple questions, multiple requests, "
                    "or a greeting followed by questions. Understand all of them.\n"
                    "4. If there are multiple questions or requests, answer ALL of them.\n"
                    "5. Preserve the order of the user's questions/requests when answering them.\n"
                    "6. If the user asks 2, 3, 10, or even 20 things in one message, handle as many "
                    "as are reasonably possible instead of ignoring the rest.\n"
                    "7. A greeting such as 'hey', 'hi', or 'hello' at the beginning of a longer "
                    "message is NOT the main request. Do not stop after replying to the greeting.\n"
                    "8. If a greeting is followed by a question, acknowledge the greeting briefly "
                    "and then answer the actual question.\n"
                    "9. If several questions are clearly connected, give one coherent answer. "
                    "Otherwise, answer them separately in the same order.\n"
                    "10. Do not repeat the user's entire message unnecessarily.\n\n"

                    "STYLE:\n"
                    "Keep answers short, clear, natural, and friendly.\n"
                    "For normal questions, usually answer in 2 to 5 lines per topic unless "
                    "the user asks for detail.\n"
                    "Use bullets or numbering when there are multiple questions so the answers "
                    "are easy to follow.\n\n"

                    "TONE:\n"
                    "Read the user's tone from their latest message.\n"
                    "If the user is casual and uses friendly Hindi/Hinglish slang among friends, "
                    "match that energy naturally and warmly.\n"
                    "If the user seems genuinely upset, stressed, or serious, be warm and supportive.\n"
                    "If the user is formal or professional, stay clean and professional.\n"
                    "When unsure, default to friendly and respectful.\n\n"

                    "LANGUAGE:\n"
                    "Detect the language from ONLY the latest user message.\n"
                    "If it is fully English, reply only in English.\n"
                    "If it contains Hindi/Hinglish words such as kya, hai, bhai, ka, ko, me, mujhe, "
                    "bata, samjha, reply naturally in Hinglish.\n"
                    "Keep technical words in English.\n\n"

                    "REASONING:\n"
                    "Use conversation history to understand follow-up questions.\n"
                    "If the user challenges your answer, re-check logically instead of simply agreeing.\n"
                    "Do not change your answer just to please the user.\n"
                    "If a question is ambiguous, ask one short clarification question or use the "
                    "most likely context.\n"
                    "Do not invent live/current information such as weather, news, prices, cricket "
                    "scores, train status, or other changing facts. Say when live information is needed."
                )
            }
        ]

        # Add previous conversation history
        messages.extend(history)

        # Add the COMPLETE latest user message as one message
        messages.append({
            "role": "user",
            "content": command
        })

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("GROQ ERROR:", e)
        return "Sorry, I couldn't connect to my AI brain right now."


def process_command(command, history=None, username="Friend", user_id=None):
    if history is None:
        history = []

    global pending_shutdown

    command = command.lower().strip()

    if not command:
        return "Please type a command."

    note_prefixes = [
        "note ",
        "save note ",
        "add note ",
        "remember ",
        "write down ",
        "yaad rakh ",
        "likh lo "
    ]

    for prefix in note_prefixes:
        if command.startswith(prefix):

            note_text = command[len(prefix):].strip()

            if not note_text:
                return "What should I save?"

            return add_note(note_text, user_id)

    if has_word(command, "hello"):
        return f"Hello {username}!"

    elif has_word(command, "hi"):
        return f"Hi {username}!"

    elif has_word(command, "hey"):
        return f"Hey {username}!"


    elif command == "clear notes":
        return clear_notes()
    
    elif command in ["help", "commands", "what can you do"]:
        return (
            "Try: yt, yt search song, search cats, weather in Saharsa, "
            "news, cricket score, calc, docs, wa, gpt, mail, codex, "
            "spotify, notepad, vscode, downloads, desktop, lock, shutdown."
        )
    
    elif "weather" in command:
        location = command.replace("weather", "").replace("today", "").strip()

        if location.startswith("in "):
            location = location[3:].strip()

        if not location:
            return "Please tell me the city. Example: weather in Saharsa"

        return google_search(
            f"weather {location}",
            f"Opening weather for {location}",
        )

    elif "cricket score" in command or "today cricket score" in command:
        return google_search(
            "today cricket score",
            "Opening today's cricket score",
        )

    elif "news" in command:
        topic = command.replace("news", "").replace("today", "").strip()

        if topic:
            return google_search(
                f"{topic} news today",
                f"Opening latest news for {topic}",
            )

        return open_website(
            "https://news.google.com",
            "Opening Google News",
        )

    elif "pin code" in command or "pincode" in command:
        query = command.replace("pin code", "").replace("pincode", "").strip()

        if not query:
            return "Please tell me the place. Example: Saharsa pincode"

        return google_search(
            f"{query} pincode",
            f"Searching pincode for {query}",
        )

    elif "youtube search" in command or command.startswith("yt search"):
        query = command.replace("youtube search", "").replace("yt search", "").strip()

        if not query:
            return "What should I search on YouTube?"

        safe_query = quote_plus(query)
        return open_website(
            f"https://www.youtube.com/results?search_query={safe_query}",
            f"Searching YouTube for {query}",
        )

    elif has_word(command, "youtube") or is_command(command, ["yt", "open yt"]):
        return open_website("https://youtube.com", "Opening YouTube")
    
    elif "search" in command:
        query = command.replace("search", "").strip()

        if not query:
            return "Please tell me what to search."

        return google_search(query)

    elif "google" in command:
        return open_website("https://google.com", "Opening Google")

    elif has_word(command, "calculator") or is_command(command, ["calc", "open calc"]):
        return open_app("calc", "Opening Calculator")

    elif "notepad" in command:
        return open_app("notepad", "Opening Notepad")

    elif "vs code" in command or has_word(command, "vscode") or "code editor" in command:
        return open_app("code", "Opening Visual Studio Code")

    elif has_word(command, "downloads") or "download folder" in command:
        downloads_path = os.path.join(os.environ["USERPROFILE"], "Downloads")
        return open_folder(downloads_path, "Opening Downloads Folder")

    elif "chrome" in command:
        return open_app("start chrome", "Opening Chrome")

    elif has_word(command, "chatgpt") or "chat gpt" in command or is_command(command, ["gpt", "open gpt"]):
        return open_windows_app(
            "OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0!ChatGPT",
            "Opening ChatGPT"
        )

    elif has_word(command, "whatsapp") or is_command(command, ["wa", "open wa"]):
        return open_windows_app(
            "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
            "Opening WhatsApp"
        )

    elif "codex" in command:
        return open_windows_app(
            "OpenAI.Codex_2p2nqsd0c76g0!App",
            "Opening Codex"
        )

    elif "documents" in command or "docs" in command:
        documents_path = os.path.join(os.environ["USERPROFILE"], "Documents")
        return open_folder(documents_path, "Opening Documents Folder")

    elif has_word(command, "gmail") or is_command(command, ["mail", "open mail"]):
        return open_onedrive_desktop_shortcut("Gmail.lnk", "Opening Gmail")

    elif "spotify" in command:
        return open_onedrive_desktop_shortcut("Spotify.lnk", "Opening Spotify")

    elif "desktop" in command:
        desktop_path = os.path.join(
            os.environ["USERPROFILE"],
            "OneDrive",
            "Desktop"
        )
        return open_folder(desktop_path, "Opening Desktop")
    
    elif "how are you" in command:
        return "Systems operational. Feeling awesome."

    elif "date" in command and "time" in command:
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        return f"Current date is {current_date} and time is {current_time}"

    elif "time" in command:
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        return f"Current time is {current_time}"

    elif "date" in command:
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        return f"Current date is {current_date}"

    elif "creator" in command:
        return "My creator is Aditya."

    elif "who are you" in command:
        return "I am JARVIS, created by Aditya."

    elif "who made you" in command:
        return "I was made by Aditya."

    elif "lock" in command:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Locking the system."

    elif "confirm shutdown" in command:
        if pending_shutdown:
            pending_shutdown = False
            os.system("shutdown /s /t 5")
            return "Shutting down in 5 seconds."

        return "No shutdown was requested."

    elif "cancel shutdown" in command:
        pending_shutdown = False
        return "Shutdown cancelled."

    elif "shutdown" in command:
        pending_shutdown = True
        return "Are you sure? Type 'confirm shutdown' to proceed or 'cancel shutdown' to cancel."

    else:
        return ask_ai(command, history)