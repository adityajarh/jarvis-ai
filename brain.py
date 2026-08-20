import datetime
import os
import re
import random
import time
import logging
import webbrowser
import requests

from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import quote_plus
from dotenv import load_dotenv
from groq import Groq
from models import db, User, Note, ResetCode

load_dotenv()

logger = logging.getLogger("jarvis.brain")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

pending_shutdown = False


# =========================================================
# AUTH / USER
# =========================================================

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


# =========================================================
# NOTES
# =========================================================

def add_note(text, user_id=None):
    note = Note(user_id=user_id, text=text)
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


# =========================================================
# PASSWORD RESET / OTP
# =========================================================

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

        logger.error("BREVO API ERROR: %s %s", response.status_code, response.text)
        return False

    except Exception as e:
        logger.error("OTP EMAIL ERROR: %s", e)
        return False


# =========================================================
# LOW-LEVEL ACTION HELPERS
# =========================================================

def has_word(text, word):
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


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
    return message if message else f"Searching Google for {query}"


def strip_words(text, words):
    """Remove whole-word occurrences of the given words from text."""
    for word in words:
        text = re.sub(rf"\b{re.escape(word)}\b", "", text)
    return re.sub(r"\s+", " ", text).strip()


# =========================================================
# INTENT MATCHERS
# =========================================================
# Small composable matchers instead of one giant if/elif chain.
# Each matcher takes the lowercased command string and returns True/False.

def match_contains(*keywords):
    def matcher(command):
        return any(kw in command for kw in keywords)
    return matcher


def match_word(*words):
    def matcher(command):
        return any(has_word(command, w) for w in words)
    return matcher


def match_exact(*phrases):
    def matcher(command):
        return command in phrases
    return matcher


def match_startswith(*prefixes):
    def matcher(command):
        return any(command.startswith(p) for p in prefixes)
    return matcher


def match_all(*matchers):
    def matcher(command):
        return all(m(command) for m in matchers)
    return matcher


def match_greeting(*words):
    def matcher(command):
        return any(has_word(command, w) for w in words)
    return matcher


# =========================================================
# INTENT HANDLERS
# =========================================================

def handle_help(command, username, user_id):
    return (
        "Try: yt, yt search song, search cats, weather in Saharsa, "
        "news, cricket score, calc, docs, wa, gpt, mail, codex, "
        "spotify, notepad, vscode, downloads, desktop, lock, shutdown."
    )


def handle_clear_notes(command, username, user_id):
    return clear_notes()


def handle_weather(command, username, user_id):
    location = strip_words(command, ["weather", "today", "whats", "what's", "what", "is"])
    location = re.sub(r"^(in|for)\s+", "", location).strip()

    if not location:
        return "Please tell me the city. Example: weather in Saharsa"

    return google_search(f"weather {location}", f"Opening weather for {location}")


def handle_cricket_score(command, username, user_id):
    return google_search("today cricket score", "Opening today's cricket score")


def handle_news(command, username, user_id):
    topic = strip_words(command, ["news", "today"])

    if topic:
        return google_search(f"{topic} news today", f"Opening latest news for {topic}")

    return open_website("https://news.google.com", "Opening Google News")


def handle_pincode(command, username, user_id):
    query = strip_words(command, ["pin code", "pincode"])

    if not query:
        return "Please tell me the place. Example: Saharsa pincode"

    return google_search(f"{query} pincode", f"Searching pincode for {query}")


def handle_youtube_search(command, username, user_id):
    query = strip_words(command, ["youtube search", "yt search"])

    if not query:
        return "What should I search on YouTube?"

    safe_query = quote_plus(query)
    return open_website(
        f"https://www.youtube.com/results?search_query={safe_query}",
        f"Searching YouTube for {query}",
    )


def handle_youtube_open(command, username, user_id):
    return open_website("https://youtube.com", "Opening YouTube")


def handle_search(command, username, user_id):
    query = strip_words(command, ["search"])

    if not query:
        return "Please tell me what to search."

    return google_search(query)


def handle_google(command, username, user_id):
    return open_website("https://google.com", "Opening Google")


def handle_calculator(command, username, user_id):
    return open_app("calc", "Opening Calculator")


def handle_notepad(command, username, user_id):
    return open_app("notepad", "Opening Notepad")


def handle_vscode(command, username, user_id):
    return open_app("code", "Opening Visual Studio Code")


def handle_downloads(command, username, user_id):
    downloads_path = os.path.join(os.environ["USERPROFILE"], "Downloads")
    return open_folder(downloads_path, "Opening Downloads Folder")


def handle_chrome(command, username, user_id):
    return open_app("start chrome", "Opening Chrome")


def handle_chatgpt(command, username, user_id):
    return open_windows_app(
        "OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0!ChatGPT",
        "Opening ChatGPT"
    )


def handle_whatsapp(command, username, user_id):
    return open_windows_app(
        "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
        "Opening WhatsApp"
    )


def handle_codex(command, username, user_id):
    return open_windows_app(
        "OpenAI.Codex_2p2nqsd0c76g0!App",
        "Opening Codex"
    )


def handle_documents(command, username, user_id):
    documents_path = os.path.join(os.environ["USERPROFILE"], "Documents")
    return open_folder(documents_path, "Opening Documents Folder")


def handle_gmail(command, username, user_id):
    return open_onedrive_desktop_shortcut("Gmail.lnk", "Opening Gmail")


def handle_spotify(command, username, user_id):
    return open_onedrive_desktop_shortcut("Spotify.lnk", "Opening Spotify")


def handle_desktop(command, username, user_id):
    desktop_path = os.path.join(os.environ["USERPROFILE"], "OneDrive", "Desktop")
    return open_folder(desktop_path, "Opening Desktop")


def handle_how_are_you(command, username, user_id):
    return "Systems operational. Feeling awesome."


def handle_date_and_time(command, username, user_id):
    now = datetime.datetime.now()
    return f"Current date is {now.strftime('%Y-%m-%d')} and time is {now.strftime('%H:%M:%S')}"


def handle_time(command, username, user_id):
    return f"Current time is {datetime.datetime.now().strftime('%H:%M:%S')}"


def handle_date(command, username, user_id):
    return f"Current date is {datetime.datetime.now().strftime('%Y-%m-%d')}"


def handle_creator(command, username, user_id):
    return "My creator is Aditya."


def handle_who_are_you(command, username, user_id):
    return "I am JARVIS, created by Aditya."


def handle_who_made_you(command, username, user_id):
    return "I was made by Aditya."


def handle_lock(command, username, user_id):
    os.system("rundll32.exe user32.dll,LockWorkStation")
    return "Locking the system."


def handle_confirm_shutdown(command, username, user_id):
    global pending_shutdown

    if pending_shutdown:
        pending_shutdown = False
        os.system("shutdown /s /t 5")
        return "Shutting down in 5 seconds."

    return "No shutdown was requested."


def handle_cancel_shutdown(command, username, user_id):
    global pending_shutdown
    pending_shutdown = False
    return "Shutdown cancelled."


def handle_shutdown(command, username, user_id):
    global pending_shutdown
    pending_shutdown = True
    return "Are you sure? Type 'confirm shutdown' to proceed or 'cancel shutdown' to cancel."


def handle_hello(command, username, user_id):
    return f"Hello {username}!"


def handle_hi(command, username, user_id):
    return f"Hi {username}!"


def handle_hey(command, username, user_id):
    return f"Hey {username}!"

def handle_good_morning(command, username, user_id):
    return f"Good morning, {username}!"


def handle_good_evening(command, username, user_id):
    return f"Good evening, {username}!"


def handle_good_afternoon(command, username, user_id):
    return f"Good afternoon, {username}!"


# =========================================================
# INTENT REGISTRY
# =========================================================
# Order matters: evaluated top to bottom, first match wins.
# Specific / real questions are placed before greetings on purpose,
# so a message like "hey buddy who made you" matches "who made you"
# before it ever reaches the greeting check.

INTENTS = [
    (match_exact("clear notes"), handle_clear_notes),
    (match_exact("help", "commands", "what can you do"), handle_help),

    (match_contains("weather"), handle_weather),
    (match_contains("cricket score"), handle_cricket_score),
    (match_contains("news"), handle_news),
    (match_contains("pin code", "pincode"), handle_pincode),

    (match_all(match_contains("youtube"), match_contains("search")), handle_youtube_search),
    (match_startswith("yt search"), handle_youtube_search),
    (match_all(match_word("youtube"), match_exact("yt", "open yt")), handle_youtube_open),
    (match_word("youtube"), handle_youtube_open),
    (match_exact("yt", "open yt"), handle_youtube_open),

    (match_contains("search"), handle_search),
    (match_contains("google"), handle_google),

    (match_all(match_word("calculator"), match_exact("calc", "open calc")), handle_calculator),
    (match_word("calculator"), handle_calculator),
    (match_exact("calc", "open calc"), handle_calculator),

    (match_contains("notepad"), handle_notepad),
    (match_contains("vs code"), handle_vscode),
    (match_word("vscode"), handle_vscode),
    (match_contains("code editor"), handle_vscode),

    (match_word("downloads"), handle_downloads),
    (match_contains("download folder"), handle_downloads),

    (match_contains("chrome"), handle_chrome),

    (match_word("chatgpt"), handle_chatgpt),
    (match_contains("chat gpt"), handle_chatgpt),
    (match_exact("gpt", "open gpt"), handle_chatgpt),

    (match_word("whatsapp"), handle_whatsapp),
    (match_exact("wa", "open wa"), handle_whatsapp),

    (match_contains("codex"), handle_codex),

    (match_contains("documents", "docs"), handle_documents),

    (match_word("gmail"), handle_gmail),
    (match_exact("mail", "open mail"), handle_gmail),

    (match_contains("spotify"), handle_spotify),
    (match_contains("desktop"), handle_desktop),

    (match_contains("how are you"), handle_how_are_you),

    (match_all(match_contains("date"), match_contains("time")), handle_date_and_time),
    (match_contains("time"), handle_time),
    (match_contains("date"), handle_date),

    (match_contains("creator"), handle_creator),
    (match_contains("who made you"), handle_who_made_you),
    (match_contains("who are you"), handle_who_are_you),

    (match_contains("lock"), handle_lock),
    (match_contains("confirm shutdown"), handle_confirm_shutdown),
    (match_contains("cancel shutdown"), handle_cancel_shutdown),
    (match_contains("shutdown"), handle_shutdown),

    # Greetings LAST - only fire for short, standalone greetings.
    # Anything longer (a real question) is already handled above.
    (match_contains("good morning"), handle_good_morning),
    (match_contains("good evening"), handle_good_evening),
    (match_contains("good afternoon"), handle_good_afternoon),
    (match_greeting("hello"), handle_hello),
    (match_greeting("hi"), handle_hi),
    (match_greeting("hey"), handle_hey),
    (match_short_greeting("hello"), handle_hello),
    (match_short_greeting("hi"), handle_hi),
    (match_short_greeting("hey"), handle_hey),
]


NOTE_PREFIXES = [
    "note ",
    "save note ",
    "add note ",
    "remember ",
    "write down ",
    "yaad rakh ",
    "likh lo "
]


def try_note_command(command, user_id):
    for prefix in NOTE_PREFIXES:
        if command.startswith(prefix):
            note_text = command[len(prefix):].strip()

            if not note_text:
                return "What should I save?"

            return add_note(note_text, user_id)

    return None


# =========================================================
# AI FALLBACK
# =========================================================

SYSTEM_PROMPT = (
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


def ask_ai(command, history=None):
    if history is None:
        history = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": command})

    last_error = None

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            last_error = e
            status_code = getattr(e, "status_code", None)
            logger.error("GROQ ERROR (attempt %s): %s", attempt + 1, e)

            if status_code == 401:
                return "My AI connection isn't set up correctly right now. Please tell Aditya."

            if status_code == 429:
                return "I'm getting a lot of requests right now. Please try again in a moment."

            if attempt == 0:
                time.sleep(1)
                continue

    logger.error("GROQ ERROR (final): %s", last_error)
    return "Sorry, I couldn't connect to my AI brain right now."


# =========================================================
# MAIN ENTRY POINT
# =========================================================

def process_command(command, history=None, username="Friend", user_id=None):
    if history is None:
        history = []

    command = command.lower().strip()

    if not command:
        return "Please type a command."

    note_response = try_note_command(command, user_id)
    if note_response is not None:
        return note_response

    for matcher, handler in INTENTS:
        if matcher(command):
            return handler(command, username, user_id)

    return ask_ai(command, history)