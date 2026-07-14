import os
import base64
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def send_feedback_email(name, description, image_data=None, image_filename=None):
    try:
        sender_email = os.getenv('EMAIL_USER')
        sender_password = os.getenv('EMAIL_APP_PASSWORD')

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = sender_email
        msg['Subject'] = f'JARVIS Feedback from {name}'

        timestamp = datetime.datetime.now().strftime('%d %b %Y %H:%M')
        body = f'Name: {name}\nTime: {timestamp}\n\nFeedback:\n{description}'
        msg.attach(MIMEText(body, 'plain'))

        if image_data:
            image_bytes = base64.b64decode(image_data.split(',')[1])
            image = MIMEImage(image_bytes)
            image.add_header('Content-Disposition', 'attachment', filename=image_filename or 'screenshot.png')
            msg.attach(image)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        print('EMAIL ERROR:', e)
        return False