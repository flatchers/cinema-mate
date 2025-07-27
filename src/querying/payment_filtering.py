import datetime
from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter

from src.database.models.payments import PaymentStatus, PaymentModel


class PaymentFilter(Filter):
    user_id: Optional[int] = None
    created_at: Optional[datetime.date] = None
    created_at__gte: Optional[datetime.date] = None
    created_at__lte: Optional[datetime.date] = None
    status: Optional[PaymentStatus] = None

    class Constants(Filter.Constants):
        model = PaymentModel
