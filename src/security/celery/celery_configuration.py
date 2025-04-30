from celery.schedules import crontab

from src.security.celery.celery import celery_app

celery_app.conf.beat_schedule = {
    # Executes every Day morning at 0:00 a.m.
    "add-every-monday-morning": {
        "task": "src.security.celery.delete_tokens",
        "schedule": crontab(hour=0, minute=0),
    },
}
