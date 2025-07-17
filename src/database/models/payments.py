from datetime import datetime
import enum
from typing import Optional

from sqlalchemy import Integer, ForeignKey, func, Enum, DECIMAL, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models import OrderModel, UserModel
from src.database.models.base import Base


class PaymentStatus(str, enum.Enum):
    SUCCESSFUL = "SUCCESSFUL"
    CANCELED = "CANCELED"
    REFUNDED = "REFUNDED"


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.SUCCESSFUL,
        server_default=PaymentStatus.SUCCESSFUL
    )
    amount: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2))
    external_payment_id: Mapped[Optional[str]] = mapped_column(String)

    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="payments")
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="payments")
