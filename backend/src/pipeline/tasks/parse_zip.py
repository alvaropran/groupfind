"""Celery task: Parse Instagram data export ZIP file."""

import logging
from uuid import UUID

from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.message import ExtractedMessageModel
from src.models.reel import ExtractedReelModel
from src.models.session import SessionModel
from src.pipeline.utils.instagram_parser import parse_chat_from_zip
from src.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def parse_zip_task(self, job_id: str, file_url: str, chat_dir: str | None = None, trip_details: dict | None = None) -> dict:
    """Parse an Instagram export ZIP and extract messages + reel URLs.

    Args:
        job_id: UUID of the processing job.
        file_url: Local path to the uploaded ZIP file.
        chat_dir: Specific chat directory to parse. None = largest chat.
        trip_details: Dict with destination, start_date, num_days, etc.

    Returns:
        Dict with job_id, counts, and trip_details for the next task.
    """
    db = SessionLocal()
    try:
        job_repo = JobRepository(db)
        job_repo.update_status(
            UUID(job_id),
            status="parsing",
            progress_message="Parsing Instagram export...",
            progress_percent=10,
        )

        # Parse the ZIP
        chat = parse_chat_from_zip(file_url, chat_dir=chat_dir)

        # Update session with chat info
        job = job_repo.get_by_id(UUID(job_id))
        if job:
            session = db.get(SessionModel, job.session_id)
            if session:
                session.group_chat_name = chat.title
                session.participant_count = len(chat.participants)
                db.commit()

        # Insert extracted messages
        message_ids: dict[int, UUID] = {}  # timestamp_ms -> message_id
        for msg in chat.messages:
            message = ExtractedMessageModel(
                job_id=UUID(job_id),
                sender_name=msg.sender_name,
                content=msg.content,
                timestamp_ms=msg.timestamp_ms,
                message_type=msg.message_type,
                raw_json=msg.raw_json,
            )
            db.add(message)
            db.flush()
            message_ids[msg.timestamp_ms] = message.id

        # Insert extracted reels
        reel_count = 0
        for url in chat.reel_urls:
            reel = ExtractedReelModel(
                job_id=UUID(job_id),
                reel_url=url,
                extraction_status="pending",
            )
            db.add(reel)
            reel_count += 1

        db.commit()

        job_repo.update_status(
            UUID(job_id),
            status="parsing",
            progress_message=f"Parsed {len(chat.messages)} messages, found {reel_count} reels",
            progress_percent=20,
        )

        logger.info(
            "Parsed ZIP for job %s: %d messages, %d reels",
            job_id, len(chat.messages), reel_count,
        )

        return {
            "job_id": job_id,
            "message_count": len(chat.messages),
            "reel_count": reel_count,
            "trip_details": trip_details or {},
        }

    except Exception as e:
        logger.error("Failed to parse ZIP for job %s: %s", job_id, e)
        job_repo.update_status(
            UUID(job_id),
            status="failed",
            error_message=f"Failed to parse Instagram export: {e}",
        )
        raise
    finally:
        db.close()
