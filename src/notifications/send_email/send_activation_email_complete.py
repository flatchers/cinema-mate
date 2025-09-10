from src.notifications.sendgrid import send_email_sendgrid


def send_activation_email_confirm(user_email: str, token: str):
    subject = "Account Login"
    body = (
        f"Please click the following link to login your account: "
        f"https://127.0.0.1/accounts/login?token={token}"
    )
    send_email_sendgrid(user_email, subject, body)
