import smtplib
from email.mime.text import MIMEText
import secrets


def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "noreply@example.com"
    msg["To"] = to_email

    with smtplib.SMTP("smtp.example.com", 587) as server:
        server.starttls()
        server.login("user@example.com", "password")
        server.send_message(msg)


def generate_token():
    return secrets.token_urlsafe(32)
