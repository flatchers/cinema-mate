from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    __abstract__ = True

    @classmethod
    def default_order_by(cls):
        return None
