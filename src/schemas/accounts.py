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
