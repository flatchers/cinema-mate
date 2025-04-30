import enum
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import hashlib

from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Boolean, Date, DateTime, func, text
from sqlalchemy.orm import relationship, mapped_column, Mapped
from src.database.models.base import Base
from src.security import validations
from src.security.utils import generate_token
from src.security.validations import password_hash_pwd, verify_password


class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum),
        nullable=False,
        unique=True,
    )

    users: Mapped[List["UserModel"]] = relationship("UserModel", back_populates="group")


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    _hashed_password: Mapped[str] = mapped_column("hashed_password", String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False)
    group: Mapped["UserGroup"] = relationship("UserGroup", back_populates="users")
    profile: Mapped["UserProfileModel"] = relationship("UserProfileModel", back_populates="user")
    activation_token: Mapped[Optional["ActivationTokenModel"]] = relationship(
        "ActivationTokenModel", back_populates="user"
    )
    password_reset_token: Mapped[Optional["PasswordResetTokenModel"]] = relationship(
        "PasswordResetTokenModel",
        back_populates="user"
    )
    refresh_token: Mapped[Optional["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel",
        back_populates="user"
    )

    @property
    def password(self):
        raise AttributeError("Password is write-only. Use the setter to set the password.")

    @password.setter
    def password(self, raw_password: str) -> None:
        validations.password_validator_func(raw_password)
        self._hashed_password = password_hash_pwd(raw_password)

    def verify_password_pwd(self, raw_password):
        return verify_password(raw_password, self._hashed_password)


class UserProfileModel(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional[GenderEnum]] = mapped_column(Enum(GenderEnum))
    date_of_birth: Mapped[Optional[Date]] = mapped_column(Date)
    info: Mapped[Optional[str]] = mapped_column(String(255))

    user_id: Mapped[int] = mapped_column(ForeignKey(
        "users.id",
        ondelete="CASCADE"
    ),
        nullable=False,
        unique=True
    )
    user: Mapped[UserModel] = relationship("UserModel", back_populates="profile")


class ActivationTokenModel(Base):
    __tablename__ = "activation_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, default=generate_token)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped[UserModel] = relationship("UserModel", back_populates="activation_token")


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, default=generate_token)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped[UserModel] = relationship("UserModel", back_populates="password_reset_token")


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(512), unique=True, default=generate_token)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped[UserModel] = relationship("UserModel", back_populates="refresh_token")
