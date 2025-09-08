import asyncio
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy import select

from src.database.models.accounts import ActivationTokenModel
from ...database.session_postgresql import get_postgresql_db

celery_app = Celery(
    "cinema_mate",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)


@celery_app.task
def delete_tokens():
    asyncio.run(_celery_delete_token())


async def _celery_delete_token():
    async with (get_postgresql_db() as db):
        now = datetime.now(timezone.utc)
        stmt = (
            select(ActivationTokenModel)
            .where(ActivationTokenModel.expires_at < now)
        )
        result = await db.execute(stmt)
        expired_tokens = result.scalars().all()
        count = len(expired_tokens)

        for token in expired_tokens:
            await db.delete(token)

    await db.commit()
    print(f"delete {count} tokens")
