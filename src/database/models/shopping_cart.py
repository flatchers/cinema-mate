from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship
from src.database.models.base import Base

if TYPE_CHECKING:
    from .accounts import UserModel
    from .movies import Movie


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="cart", uselist=False)
    cart_items: Mapped[list["CartItemsModel"]] = relationship("CartItemsModel", back_populates="cart")


class CartItemsModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    cart: Mapped["CartModel"] = relationship("CartModel", back_populates="cart_items")
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    movie: Mapped["Movie"] = relationship("Movie", back_populates="cart_items")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("cart_id", "movie_id"),)
