from typing import Annotated

from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models.base import Base

SQL_DB_URL = "sqlite+aiosqlite:///./online_cinema.db"

engine = create_async_engine(SQL_DB_URL, echo=False)
AsyncSQLiteSessionLocal = sessionmaker(  # type: ignore
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    async with AsyncSQLiteSessionLocal() as session:
        yield session

AsyncSessionDepends = Annotated[AsyncSession, Depends(get_db)]


async def reset_sqlite_database() -> None:
    """
    Reset the SQLite database.

    This function drops all existing tables and recreates them.
    It is useful for testing purposes or when resetting the database is required.

    Warning: This action is irreversible and will delete all stored data.

    :return: None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
