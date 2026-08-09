import os
import base64
import requests
import datetime

def send_feedback_email(name, description, image_data=None, image_filename=None):
    try:
        api_key = os.getenv("BREVO_API_KEY")
        sender_email = os.getenv("EMAIL_USER")

        timestamp = datetime.datetime.now().strftime('%d %b %Y %H:%M')

        html_content = f"""
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Time:</strong> {timestamp}</p>
        <p><strong>Feedback:</strong></p>
        <p>{description}</p>
        """

        payload = {
            "sender": {"name": "JARVIS", "email": sender_email},
            "to": [{"email": sender_email}],
            "subject": f"JARVIS Feedback from {name}",
            "htmlContent": html_content,
        }

        if image_data:
            image_base64 = image_data.split(',')[1] if ',' in image_data else image_data
            payload["attachment"] = [{
                "content": image_base64,
                "name": image_filename or "screenshot.png"
            }]

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json",
            },
            json=payload,
            timeout=10,
        )

        if response.status_code in (200, 201):
            return True
        else:
            print("BREVO FEEDBACK ERROR:", response.status_code, response.text)
            return False

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False