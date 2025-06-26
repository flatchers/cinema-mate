import smtplib
from email.mime.text import MIMEText
import secrets


def send_email(to_email: str, subject: str, body: str):
    print(f"[DEBUG] Sending email to {to_email} with subject '{subject}' and body:\n{body}")


def generate_token():
    return secrets.token_urlsafe(32)
