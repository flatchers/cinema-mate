from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, EmailStr

from src.database.models.accounts import UserGroupEnum


class UserCreate(BaseModel):
    email: EmailStr

    class Config:
        from_attributes: bool = True


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreateResponse(UserCreate):
    id: int


class TokenActivationRequest(UserCreate):
    token: str


class TokenResetPasswordRequest(UserCreate):
    pass


class TokenResetPasswordCompleteRequest(BaseModel):
    email: EmailStr
    password: str
    token: str


class MessageResponse(BaseModel):
    message: str


class UserLoginRequest(UserCreate):
    password: str


class UserLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str


class EmailSchema(BaseModel):
    email: List[EmailStr]


class AdminUpdateRequest(BaseModel):
    group: Literal["user", "moderator", "admin"]
    is_active: bool
