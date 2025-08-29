from src.config.settings import settings


if settings.MODE == "TEST":
    from src.database.session_sqlite import (
        get_sqlite_db_contextmanager as get_db_contextmanager,
        get_db
    )
if settings.MODE == "DEV":
    from src.database.session_postgresql import (
        get_postgresql_db_contextmanager as get_db_contextmanager,
        get_postgresql_db as get_db
    )
