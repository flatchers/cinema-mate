from src.config.settings import settings  # noqa: F401
from src.database.models.accounts import UserModel  # noqa: F401
from src.database.models.movies import Movie, Genre  # noqa: F401
from src.database.models.order import OrderModel, OrderItemModel  # noqa: F401
from src.database.models.payments import PaymentModel  # noqa: F401


if settings.MODE == "TEST":
    from src.database.session_sqlite import (
        get_sqlite_db_contextmanager as get_db_contextmanager,
        get_db,
    )
else:
    from src.database.session_postgresql import (
        get_postgresql_db_contextmanager as get_db_contextmanager,
        get_postgresql_db as get_db,
    )

__all__ = ["get_db_contextmanager", "get_db"]
