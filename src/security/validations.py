import re

from fastapi import HTTPException
from starlette import status
from passlib.context import CryptContext
import bcrypt


bcrypt.__about__ = bcrypt


def email_validator_func(email):
    pattern = (
        r"^(?!\.)(?!.*\.\.)[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
        r"@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$"
    )
    return re.match(pattern, email) is not None


def password_validator_func(password):
    if len(password) < 8:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Make sure your password is at lest 8 letters",
        )
    elif re.search("[0-9]", password) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Make sure your password has a number in it",
        )
    elif re.search("[A-Z]", password) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Make sure your password has a capital letter in it",
        )
    return password


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def password_hash_pwd(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
