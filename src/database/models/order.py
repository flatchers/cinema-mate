from datetime import datetime
import enum

from sqlalchemy import Integer, ForeignKey, func, Enum, DECIMAL
from sqlalchemy.orm import Mapped, relationship, mapped_column

from src.database.models import UserModel
from src.database.models.base import Base


class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELED = "CANCELED"


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="orders")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum),
        nullable=False,
        default=StatusEnum.PENDING,
        server_default=StatusEnum.PENDING
    )
    total_amount: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2))


