import secrets


def generate_token():
    """
    Generate a secure random token.

    Returns:
        str: Securely generated token.
    """
    return secrets.token_urlsafe(32)
