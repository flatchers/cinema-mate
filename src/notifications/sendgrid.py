import requests

from src.config.settings import settings


def send_email_sendgrid(to_email: str, subject: str, body: str):
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "personalizations": [{"to": [{"email": to_email}], "subject": subject}],
        "from": {"email": "your@mail.example"},
        "content": [{"type": "text/plain", "value": body}],
    }
    response = requests.post(url, headers=headers, json=data)
    print(f"[DEBUG] SendGrid response: " f"{response.status_code} - {response.text}")
    return response.status_code
