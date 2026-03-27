"""Plain pipeline functions — no Celery, no Redis.

These are the same logic as the old Celery tasks but as regular functions.
Called by the orchestrator in a background thread.
"""

import asyncio
import logging
from decimal import Decimal
from uuid import UUID

from src.database import SessionLocal
from src.models.activity import ActivityModel
from src.models.message import ExtractedMessageModel
from src.models.reel import ExtractedReelModel
from src.models.session import SessionModel
from src.pipeline.utils.activity_extractor import extract_activities
from src.pipeline.utils.instagram_parser import parse_chat_from_zip
from src.pipeline.utils.review_searcher import search_booking_links, search_reviews
from src.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


def run_parse_zip(
    job_id: str,
    file_url: str,
    chat_dir: str | None = None,
    trip_details: dict | None = None,
) -> dict:
    """Parse an Instagram export ZIP and extract messages."""
    db = SessionLocal()
    try:
        job_repo = JobRepository(db)
        job_repo.update_status(
            UUID(job_id),
            status="parsing",
            progress_message="Parsing Instagram export...",
            progress_percent=10,
        )

        chat = parse_chat_from_zip(file_url, chat_dir=chat_dir)

        job = job_repo.get_by_id(UUID(job_id))
        if job:
            session = db.get(SessionModel, job.session_id)
            if session:
                session.group_chat_name = chat.title
                session.participant_count = len(chat.participants)
                db.commit()

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

        logger.info("Parsed ZIP for job %s: %d messages, %d reels", job_id, len(chat.messages), reel_count)

        return {
            "job_id": job_id,
            "message_count": len(chat.messages),
            "reel_count": reel_count,
            "trip_details": trip_details or {},
        }

    except Exception as e:
        logger.error("Failed to parse ZIP for job %s: %s", job_id, e)
        job_repo.update_status(UUID(job_id), status="failed", error_message=f"Failed to parse Instagram export: {e}")
        raise
    finally:
        db.close()


def run_process_activities(previous_result: dict) -> dict:
    """Extract activities, get reviews, find booking links."""
    job_id = previous_result["job_id"]
    trip_details = previous_result.get("trip_details", {})
    destination = trip_details.get("destination", "")

    db = SessionLocal()
    try:
        job_repo = JobRepository(db)

        job_repo.update_status(
            UUID(job_id),
            status="extracting",
            progress_message=f"Reading your chat for {destination} activities...",
            progress_percent=25,
        )

        messages = (
            db.query(ExtractedMessageModel)
            .filter(ExtractedMessageModel.job_id == UUID(job_id))
            .order_by(ExtractedMessageModel.timestamp_ms)
            .all()
        )

        # Pre-filter to relevant messages only
        destination_lower = destination.lower()
        keywords = [w.strip().lower() for w in destination_lower.replace(",", " ").split() if len(w.strip()) > 2]

        all_with_content = [m for m in messages if m.content]
        relevant = []
        for i, m in enumerate(all_with_content):
            if any(kw in m.content.lower() for kw in keywords):
                start = max(0, i - 5)
                end = min(len(all_with_content), i + 6)
                for j in range(start, end):
                    relevant.append(all_with_content[j])

        seen_ids: set[int] = set()
        unique = []
        for m in relevant:
            if id(m) not in seen_ids:
                seen_ids.add(id(m))
                unique.append(m)

        message_dicts = [{"sender_name": m.sender_name, "content": m.content} for m in unique]
        logger.info("Filtered %d → %d relevant messages for '%s'", len(all_with_content), len(message_dicts), destination)

        activities = asyncio.run(extract_activities(message_dicts, destination))

        job_repo.update_status(
            UUID(job_id),
            status="extracting",
            progress_message=f"Found {len(activities)} activities",
            progress_percent=45,
        )

        total = len(activities)
        for i, activity in enumerate(activities):
            job_repo.update_status(
                UUID(job_id),
                status="verifying",
                progress_message=f"Checking reviews for '{activity.name}' ({i + 1}/{total})...",
                progress_percent=45 + int((i / max(total, 1)) * 45),
            )

            review = asyncio.run(search_reviews(activity.name, destination))
            bookings = asyncio.run(search_booking_links(activity.name, destination))

            booking_json = [
                {"provider": b.provider, "url": b.url, "title": b.title, "price": b.price}
                for b in bookings
            ]

            activity_row = ActivityModel(
                job_id=UUID(job_id),
                name=activity.name,
                activity_type=activity.type,
                area=activity.area,
                destination=destination,
                who_suggested=activity.who_suggested,
                what_they_said=activity.what_they_said,
                details=activity.details,
                review_rating=Decimal(str(review.rating)) if review else None,
                review_summary=review.summary if review else None,
                review_pros=review.pros if review else None,
                review_cons=review.cons if review else None,
                review_best_tip=review.best_tip if review else None,
                review_sources=review.sources if review else None,
                booking_options=booking_json if booking_json else None,
            )
            db.add(activity_row)
            db.commit()

        job_repo.update_status(
            UUID(job_id),
            status="complete",
            progress_message=f"Found {total} activities with reviews and booking links!",
            progress_percent=100,
        )

        logger.info("Activity processing complete for job %s: %d activities", job_id, total)
        return {"job_id": job_id, "activity_count": total}

    except Exception as e:
        logger.error("Activity processing failed for job %s: %s", job_id, e)
        job_repo.update_status(UUID(job_id), status="failed", error_message=f"Activity processing failed: {e}")
        raise
    finally:
        db.close()
