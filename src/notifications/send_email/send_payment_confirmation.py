from src.notifications.sendgrid import send_email_sendgrid


def send_payment_confirmation_email(user_email: str):
    """
    Sends a payment confirmation email to the specified user.

    Parameters:
        user_email (str): The recipient's email address.

    Behavior:
        Composes a simple email with the subject "Payment Confirmation" and
        body "Payment was successful", then sends it to the provided email
        address using the send_email() function.

    Example:
        send_payment_confirmation_email("user@example.com")
    """
    subject = "✅ Payment Confirmation"
    body = "🎉 Payment was successful"
    send_email_sendgrid(user_email, subject, body)
