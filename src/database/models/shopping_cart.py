from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from src.database.models import UserModel
from src.database.models.base import Base


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="cart")
    cart_items: Mapped[list["CartItemsModel"]] = relationship("CartItemsModel", back_populates="cart")
