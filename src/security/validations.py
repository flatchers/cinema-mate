import re

from fastapi import HTTPException
from starlette import status


def email_validator_func(email):
    pattern = (r"^(?!\.)(?!.*\.\.)[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"

               r"@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$")
    return re.match(pattern, email) is not None


def password_validator_func(password):
    if len(password) < 8:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Make sure your password is at lest 8 letters"
        )
    elif re.search('[0-9]', password) is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Make sure your password has a number in it"
        )
    elif re.search('[A-Z]', password) is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Make sure your password has a capital letter in it"
        )
    return password
