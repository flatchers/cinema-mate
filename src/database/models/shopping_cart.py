from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    Integer,
    ForeignKey,
    DateTime,
    func,
    UniqueConstraint,
    Table,
    Column,
)
from sqlalchemy.orm import mapped_column, Mapped, relationship
from src.database.models.base import Base

if TYPE_CHECKING:
    from .accounts import UserModel
    from .movies import Movie

NotificationModeratorsModel = Table(
    "notification_moderators",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column(
        "notifications_delete_id",
        ForeignKey("notifications_delete.id"),
        primary_key=True,
        nullable=False,
    ),
)


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="cart", uselist=False
    )
    cart_items: Mapped[list["CartItemsModel"]] = relationship(
        "CartItemsModel", back_populates="cart"
    )


class CartItemsModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    cart: Mapped["CartModel"] = relationship("CartModel", back_populates="cart_items")
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    movie: Mapped["Movie"] = relationship("Movie", back_populates="cart_items")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    notifications_delete: Mapped[List["NotificationDeleteModel"]] = relationship(
        "NotificationDeleteModel", back_populates="cart_items"
    )

    __table_args__ = (UniqueConstraint("cart_id", "movie_id"),)


class NotificationDeleteModel(Base):
    __tablename__ = "notifications_delete"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_items_id: Mapped[int] = mapped_column(
        ForeignKey("cart_items.id", ondelete="CASCADE"), nullable=True
    )

    comment: Mapped[str] = mapped_column()
    users: Mapped[List["UserModel"]] = relationship(
        "UserModel",
        secondary=NotificationModeratorsModel,
        back_populates="notifications_delete",
    )
    cart_items: Mapped["CartItemsModel"] = relationship(
        "CartItemsModel", back_populates="notifications_delete"
    )
