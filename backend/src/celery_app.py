from celery import Celery
from celery.schedules import crontab

from src.config import settings

celery_app = Celery(
    "groupfind",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.pipeline.tasks.parse_zip",
        "src.pipeline.tasks.process_activities",
        "src.pipeline.tasks.cleanup_sessions",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "cleanup-expired-sessions": {
            "task": "src.pipeline.tasks.cleanup_sessions.cleanup_expired_sessions",
            "schedule": crontab(minute=0),
        },
    },
)
