from datetime import datetime
import enum
from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey, func, Enum, DECIMAL
from sqlalchemy.orm import Mapped, relationship, mapped_column

from src.database.models.base import Base


class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELED = "CANCELED"


if TYPE_CHECKING:
    from src.database.models.accounts import UserModel
    from src.database.models.movies import Movie


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="orders")
    order_items: Mapped[list["OrderItemModel"]] = relationship("OrderItemModel", back_populates="order")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum),
        nullable=False,
        default=StatusEnum.PENDING,
        server_default=StatusEnum.PENDING
    )
    total_amount: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2))


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    price_at_order: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2))

    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="order_items")
    movie: Mapped["Movie"] = relationship("Movie", back_populates="order_items")
