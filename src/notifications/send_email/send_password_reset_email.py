from src.notifications.emails import send_email


def send_password_reset_email(user_email: str, token: str):
    subject = "Password Reset"
    body = f"To reset your password, click this link: http://127.0.0.1/accounts/activate/"
    send_email(user_email, subject, body)
