from datetime import datetime
import enum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey, func, Enum, DECIMAL, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base


if TYPE_CHECKING:
    from src.database.models.order import OrderModel, OrderItemModel
    from src.database.models.accounts import UserModel


class PaymentStatus(str, enum.Enum):
    SUCCESSFUL = "SUCCESSFUL"
    CANCELED = "CANCELED"
    REFUNDED = "REFUNDED"


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        default=func.now()
    )

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.SUCCESSFUL,
        server_default=PaymentStatus.SUCCESSFUL
    )

    amount: Mapped[DECIMAL] = mapped_column(
        DECIMAL(10, 2),
        nullable=False
    )

    external_payment_id: Mapped[Optional[str]] = mapped_column(
        String
    )

    # Relationships
    order: Mapped["OrderModel"] = relationship(
        "OrderModel",
        back_populates="payments"
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="payments"
    )

    payment_items: Mapped[List["PaymentItemModel"]] = relationship(
        "PaymentItemModel",
        back_populates="payment",
        cascade="all, delete-orphan"
    )


class PaymentItemModel(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False
    )

    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False
    )

    price_at_payment: Mapped[DECIMAL] = mapped_column(
        DECIMAL(10, 2),
        nullable=False
    )

    # Relationships
    payment: Mapped["PaymentModel"] = relationship(
        "PaymentModel",
        back_populates="payment_items"
    )

    order_item: Mapped["OrderItemModel"] = relationship(
        "OrderItemModel",
        back_populates="payment_items"
    )
