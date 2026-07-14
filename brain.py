import datetime
import os
import re
import random
import webbrowser
import base64
import smtplib

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
        sender_email = os.getenv("EMAIL_USER")
        sender_password = os.getenv("EMAIL_APP_PASSWORD")

        if purpose == "signup":
            subject = "Your JARVIS Verification Code"
            intro = "Welcome to JARVIS.\n\nYour verification code is:"
            footer = "If you didn't request this verification, you can safely ignore this email."
        else:
            subject = "Your JARVIS Password Reset Code"
            intro = "Your password reset code is:"
            footer = "If you didn't request a password reset, you can safely ignore this email."

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = subject

        greeting = f"Hi {name}," if name else "Hi,"

        body = f"""{greeting}

{intro}

    {code}

This code will expire in 10 minutes.

For your security, never share this code with anyone.

{footer}

— JARVIS
"""

        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return True

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
    "You are JARVIS, a helpful AI assistant created by Aditya. "
    "Keep answers short, clear, and friendly. "
    "Use conversation history to understand follow-up questions. "
"If the user challenges your answer, re-check logically instead of simply agreeing. "
"Do not change your answer just to please the user. "
"If a question is ambiguous, ask one short clarification question or answer using the most likely context. "
"For safety, rules, legal, medical, or practical advice, be careful and mention uncertainty when needed. "
    "For normal questions, answer in 2 to 5 lines unless the user asks for detail. "
    "Strict language rule: detect only the latest user message language. "
    "If the latest user message is fully English, reply only in English. Do not use Hindi or Hinglish. "
    "If the latest user message contains Hindi words like kya, hai, bhai, ka, ko, me, mujhe, bata, samjha, reply in natural Hinglish. "
    "Keep technical words in English, for example force, gravity, energy, mass, speed, current, voltage, law, system, input, output. "
    "Do not over-translate technical words into pure Hindi. "
    "Do not guess live information like weather, PIN codes, news, "
    "prices, cricket scores, train status, or current facts. "
    "If the user asks for live/current/local information, say that "
    "you need live search or an API to answer accurately."
                ),
            }
        ]

        messages.extend(history)
        messages.append({"role": "user", "content": command})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )

        return response.choices[0].message.content

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