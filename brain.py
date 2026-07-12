import datetime
import os
import re
import webbrowser
import json
import base64
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import quote_plus
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

pending_shutdown = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_FILE = os.path.join(BASE_DIR, "notes.json")


def load_notes():
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return []


def save_notes(notes):
    with open(NOTES_FILE, "w", encoding="utf-8") as file:
        json.dump(notes, file, indent=4)

USERS_FILE = os.path.join(BASE_DIR, "users.json")


def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, indent=4)


def find_user_by_email(email):
    users = load_users()
    email = email.strip().lower()

    for user in users:
        if user["email"] == email:
            return user

    return None


def create_user(name, email, password):
    users = load_users()
    email = email.strip().lower()

    if find_user_by_email(email):
        return None, "This email is already registered."

    new_id = max((u["id"] for u in users), default=0) + 1

    user = {
        "id": new_id,
        "name": name.strip().split(" ")[0],
        "email": email,
        "password_hash": generate_password_hash(password),
        "created_at": datetime.datetime.now().strftime("%d %b %Y %H:%M")
    }

    users.append(user)
    save_users(users)

    return user, None


def verify_login(email, password):
    user = find_user_by_email(email)

    if not user:
        return None

    if not check_password_hash(user["password_hash"], password):
        return None

    return user


def update_user_password(email, new_password):
    users = load_users()
    email = email.strip().lower()

    for user in users:
        if user["email"] == email:
            user["password_hash"] = generate_password_hash(new_password)
            save_users(users)
            return True

    return False

RESET_CODES_FILE = os.path.join(BASE_DIR, "reset_codes.json")


def load_reset_codes():
    try:
        with open(RESET_CODES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return []


def save_reset_codes(codes):
    with open(RESET_CODES_FILE, "w", encoding="utf-8") as file:
        json.dump(codes, file, indent=4)


def generate_reset_code(email):
    import random

    email = email.strip().lower()
    codes = load_reset_codes()

    codes = [c for c in codes if c["email"] != email]

    code = str(random.randint(100000, 999999))
    expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()

    codes.append({
        "email": email,
        "code": code,
        "expires_at": expires_at,
        "attempts": 0,
        "verified": False
    })

    save_reset_codes(codes)
    return code


def verify_reset_code(email, entered_code):
    email = email.strip().lower()
    codes = load_reset_codes()

    for entry in codes:
        if entry["email"] == email:

            if entry["attempts"] >= 5:
                return "blocked"

            if datetime.datetime.now() > datetime.datetime.fromisoformat(entry["expires_at"]):
                return "expired"

            if entry["code"] == entered_code:
                entry["verified"] = True
                save_reset_codes(codes)
                return "correct"

            entry["attempts"] += 1
            save_reset_codes(codes)
            return "incorrect"

    return "not_found"


def is_reset_verified(email):
    email = email.strip().lower()
    codes = load_reset_codes()

    for entry in codes:
        if entry["email"] == email:
            return entry.get("verified", False)

    return False


def clear_reset_code(email):
    email = email.strip().lower()
    codes = load_reset_codes()
    codes = [c for c in codes if c["email"] != email]
    save_reset_codes(codes)

def send_feedback_email(name, description, image_data=None, image_filename=None):
    try:
        sender_email = os.getenv("EMAIL_USER")
        sender_password = os.getenv("EMAIL_APP_PASSWORD")

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = sender_email
        msg["Subject"] = f"JARVIS Feedback from {name}"

        timestamp = datetime.datetime.now().strftime("%d %b %Y %H:%M")

        body = f"Name: {name}\nTime: {timestamp}\n\nFeedback:\n{description}"
        msg.attach(MIMEText(body, "plain"))

        if image_data:
            image_bytes = base64.b64decode(image_data.split(",")[1])
            image = MIMEImage(image_bytes)
            image.add_header("Content-Disposition", "attachment", filename=image_filename or "screenshot.png")
            msg.attach(image)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False
    
def send_otp_email(name, email, code):
    try:
        sender_email = os.getenv("EMAIL_USER")
        sender_password = os.getenv("EMAIL_APP_PASSWORD")

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = "Your JARVIS password reset code"

        body = f"""Hi {name},

Your password reset code is:

    {code}

This code will expire in 10 minutes. If you didn't request this, you can safely ignore this email.

— JARVIS"""

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


def add_note(text, user_id=None):
    notes = load_notes()

    new_id = max((n["id"] for n in notes), default=0) + 1

    note = {
        "id": new_id,
        "text": text,
        "archived": False,
        "created_at": datetime.datetime.now().strftime("%d %b %Y %H:%M"),
        "user_id": user_id
    }

    notes.append(note)
    save_notes(notes)

    return "Note saved successfully."


def get_notes(user_id=None):
    notes = load_notes()
    return [n for n in notes if n.get("user_id") == user_id]


def clear_notes():
    save_notes([])
    return "All notes cleared."

def delete_note(note_id):

    notes = load_notes()

    notes = [
        note
        for note in notes
        if note["id"] != note_id
    ]

    save_notes(notes)

    return "Note deleted successfully."

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