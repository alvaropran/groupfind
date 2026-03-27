"""Celery Beat task: Clean up expired sessions and their data."""

import logging

from src.celery_app import celery_app
from src.database import SessionLocal
from src.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_expired_sessions() -> dict:
    """Delete sessions that have exceeded their 24h TTL.

    CASCADE deletes will clean up jobs, messages, reels, events,
    and reddit_verifications automatically.
    """
    db = SessionLocal()
    try:
        repo = SessionRepository(db)
        deleted_count = repo.delete_expired()
        logger.info("Cleaned up %d expired sessions", deleted_count)
        return {"deleted_sessions": deleted_count}
    finally:
        db.close()
