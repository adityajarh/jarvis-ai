import datetime
import os

from flask import Flask, render_template, request, jsonify, session
from brain import (
    process_command, get_notes, send_feedback_email,
    create_user, verify_login, find_user_by_email,
    generate_reset_code, verify_reset_code, is_reset_verified,
    update_user_password, clear_reset_code, send_otp_email
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "jarvis-dev-secret-change-this")

conversation_history = {}

def write_log(user_command, jarvis_response):
    logs_folder = "logs"
    os.makedirs(logs_folder, exist_ok=True)

    log_file = os.path.join(logs_folder, "jarvis.log")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_file, "a", encoding="utf-8") as file:
        file.write(f"{timestamp} | USER: {user_command} | JARVIS: {jarvis_response}\n")

@app.route("/")
def home():
    if "user_id" not in session:
        return render_template("auth.html")
    return render_template("index.html")


@app.route("/notes", methods=["GET"])
def get_notes_api():

    try:
        if "user_id" not in session:
            return jsonify({"success": False, "error": "Not logged in"})

        notes = get_notes(session["user_id"])

        return jsonify({
            "success": True,
            "notes": notes
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })
    
@app.route("/notes/delete/<int:note_id>", methods=["DELETE"])
def delete_note_api(note_id):

    try:

        from brain import delete_note

        message = delete_note(note_id)

        return jsonify({
            "success": True,
            "message": message
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route("/signup", methods=["POST"])
def signup():
    try:
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            return jsonify({"success": False, "message": "All fields are required."})

        if len(password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters."})

        user, error = create_user(name, email, password)

        if error:
            return jsonify({"success": False, "message": error})

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session.permanent = True

        return jsonify({"success": True, "message": "Account created!", "name": user["name"]})

    except Exception as e:
        print("SIGNUP ERROR:", e)
        return jsonify({"success": False, "message": "Something went wrong."})

@app.route("/login", methods=["POST"])
def login():
    try:
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required."})

        user = verify_login(email, password)

        if not user:
            return jsonify({"success": False, "message": "Incorrect email or password."})

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session.permanent = True

        return jsonify({"success": True, "name": user["name"]})

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"success": False, "message": "Something went wrong."})
    
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/forgot-password/send-code", methods=["POST"])
def forgot_password_send_code():
    try:
        email = request.form.get("email", "").strip()

        if not email:
            return jsonify({"success": False, "message": "Email is required."})

        user = find_user_by_email(email)

        if not user:
            return jsonify({"success": False, "message": "No account found with this email."})

        code = generate_reset_code(email)
        sent = send_otp_email(user["name"], email, code)

        if not sent:
            return jsonify({"success": False, "message": "Could not send code. Try again."})

        return jsonify({"success": True, "message": "Code sent to your email."})

    except Exception as e:
        print("SEND CODE ERROR:", e)
        return jsonify({"success": False, "message": "Something went wrong."})
    
@app.route("/forgot-password/verify-code", methods=["POST"])
def forgot_password_verify_code():
    try:
        email = request.form.get("email", "").strip()
        code = request.form.get("code", "").strip()

        if not email or not code:
            return jsonify({"success": False, "message": "Code is required."})

        result = verify_reset_code(email, code)

        if result == "correct":
            return jsonify({"success": True, "message": "Code verified."})
        elif result == "blocked":
            return jsonify({"success": False, "message": "Too many attempts. Try again in 10 minutes.", "blocked": True})
        elif result == "expired":
            return jsonify({"success": False, "message": "Code expired. Request a new one."})
        elif result == "incorrect":
            return jsonify({"success": False, "message": "Incorrect code. Try again."})
        else:
            return jsonify({"success": False, "message": "No code was requested for this email."})

    except Exception as e:
        print("VERIFY CODE ERROR:", e)
        return jsonify({"success": False, "message": "Something went wrong."})

@app.route("/forgot-password/reset", methods=["POST"])
def forgot_password_reset():
    try:
        email = request.form.get("email", "").strip()
        new_password = request.form.get("password", "").strip()

        if not email or not new_password:
            return jsonify({"success": False, "message": "Password is required."})

        if len(new_password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters."})

        if not is_reset_verified(email):
            return jsonify({"success": False, "message": "Please verify your code first."})

        updated = update_user_password(email, new_password)

        if not updated:
            return jsonify({"success": False, "message": "Could not update password."})

        clear_reset_code(email)

        return jsonify({"success": True, "message": "Password updated!"})

    except Exception as e:
        print("RESET PASSWORD ERROR:", e)
        return jsonify({"success": False, "message": "Something went wrong."})    

@app.route("/backup-data-temp-xyz123")
def backup_data():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            users_data = f.read()
        with open("notes.json", "r", encoding="utf-8") as f:
            notes_data = f.read()
        return f"<h3>USERS:</h3><pre>{users_data}</pre><h3>NOTES:</h3><pre>{notes_data}</pre>"
    except Exception as e:
        return f"Error: {e}"            


@app.route("/feedback", methods=["POST"])
def feedback():
    try:
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        image_data = request.form.get("image_data", "").strip()
        image_filename = request.form.get("image_filename", "").strip()

        if not name or not description:
            return jsonify({
                "success": False,
                "message": "Name and description are required."
            })

        sent = send_feedback_email(
            name,
            description,
            image_data if image_data else None,
            image_filename if image_filename else None
        )

        if sent:
            return jsonify({
                "success": True,
                "message": "Feedback sent."
            })
        else:
            return jsonify({
                "success": False,
                "message": "Could not send feedback. Try again."
            })

    except Exception as e:
        print("FEEDBACK ROUTE ERROR:", e)
        return jsonify({
            "success": False,
            "message": "Something went wrong."
        })

@app.route("/command", methods=["POST"])
def command():
    try:
        if "user_id" not in session:
            return jsonify({"success": False, "response": "Please log in."})

        user_id = session["user_id"]
        username = session.get("user_name", "Friend")

        user_command = request.form.get("command", "").strip()

        if not user_command:
            return jsonify({
                "success": False,
                "response": "Please type a command."
            })

        if user_id not in conversation_history:
            conversation_history[user_id] = []

        response = process_command(user_command, conversation_history[user_id], username, user_id)

        conversation_history[user_id].append({"role": "user", "content": user_command})
        conversation_history[user_id].append({"role": "assistant", "content": response})

        if len(conversation_history[user_id]) > 20:
            conversation_history[user_id] = conversation_history[user_id][-20:]

        write_log(user_command, response)

        return jsonify({
            "success": True,
            "response": response
        })

    except Exception as e:
        print("APP ERROR:", e)

        error_response = "Something went wrong inside JARVIS."
        write_log("APP ERROR", str(e))

        return jsonify({
            "success": False,
            "response": error_response
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)