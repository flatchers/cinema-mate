from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreateResponse(UserCreate):
    id: int


class TokenActivationRequest(UserCreate):
    token: str

