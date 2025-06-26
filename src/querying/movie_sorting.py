from enum import StrEnum, auto, Enum
from typing import List, Optional

from fastapi import Query
from pydantic import BaseModel


class SortOption(StrEnum):
    desc = auto()
    asc = auto()
    NONE = auto()


class OrderBy(str, Enum):
    id = "id"
    name = "name"
    year = "year"
    imdb = "imdb"
    price = "price"


class ItemQueryParams(BaseModel):
    order_by: OrderBy = OrderBy.id
    descending: bool = False
