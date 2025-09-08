from src.notifications.sendgrid import send_email_sendgrid


def send_password_reset_email(user_email: str, token: str):
    subject = "Password Reset"
    body = (
        f"To reset your password, click this link: "
        f"http://127.0.0.1/accounts/password-reset/request/?token={token}"
    )
    send_email_sendgrid(user_email, subject, body)
