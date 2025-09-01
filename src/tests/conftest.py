import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine

from src.database.session_sqlite import reset_sqlite_database, get_sqlite_db_contextmanager
from src.main import app


@pytest_asyncio.fixture(scope="function", autouse=True)
async def reset_db():
    await reset_sqlite_database()
    yield


@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_session():
    async with get_sqlite_db_contextmanager() as session:
        yield session


@pytest_asyncio.fixture(scope="function", autouse=True)
async def client(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
