from src.notifications.sendgrid import send_email_sendgrid


def send_activation_email(user_email: str, token: str):
    subject = "Account Activation"
    body = (
        f"Please click the following link to activate your account: "
        f"https://127.0.0.1/accounts/activate?token={token}"
    )
    send_email_sendgrid(user_email, subject, body)
