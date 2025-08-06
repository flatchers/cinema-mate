from datetime import datetime

from pydantic import BaseModel

from src.database.models.order import StatusEnum


class OrderSchemaResponse(BaseModel):
    id: int
    created_at: datetime
    count_films: int
    total_amount: float
    status: StatusEnum
