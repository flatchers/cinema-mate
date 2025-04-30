import requests


def send_email_sendgrid(to_email: str, subject: str, body: str):
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": "Bearer YOUR_SENDGRID_API_KEY",
        "Content-Type": "application/json"
    }
    data = {
        "personalizations": [{
            "to": [{"email": to_email}],
            "subject": subject
        }],
        "from": {"email": "noreply@example.com"},
        "content": [{
            "type": "text/plain",
            "value": body
        }]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code
