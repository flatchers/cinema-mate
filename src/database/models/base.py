from typing import Annotated

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase


str_255 = Annotated[str, 255]


class Base(DeclarativeBase):
    type_annotation_map = {
        str_255: String(255)
    }

    @classmethod
    def default_order_by(cls):
        return None
