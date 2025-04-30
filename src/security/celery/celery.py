import asyncio
from datetime import datetime, timezone
import time

from celery import Celery
from celery.bin import celery


from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.accounts import ActivationTokenModel

celery_app = Celery(
    "cinema_mate",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)


@celery_app.task
def delete_tokens():
    asyncio.run(_celery_delete_token())


@celery_app.task
async def _celery_delete_token(db: AsyncSession):
    now = datetime.now(timezone.utc)
    stmt = select(ActivationTokenModel).where(ActivationTokenModel.expires_at < now)
    result = await db.execute(stmt)
    expired_tokens = result.scalars().all()
    count = len(expired_tokens)

    for token in expired_tokens:
        await db.delete(token)

    await db.commit()
    print(f"delete {count} tokens")

