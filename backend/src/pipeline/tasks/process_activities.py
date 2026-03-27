"""Celery task: Extract activities, verify with reviews, find booking links."""

import asyncio
import logging
from decimal import Decimal
from uuid import UUID

from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.activity import ActivityModel
from src.models.message import ExtractedMessageModel
from src.pipeline.utils.activity_extractor import extract_activities
from src.pipeline.utils.review_searcher import search_reviews, search_booking_links
from src.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=15)
def process_activities_task(self, previous_result: dict) -> dict:
    """Extract activities from chat, verify with reviews, find booking links.

    Three phases:
    1. Extract activities/tours from messages using LLM
    2. Web search for reviews of each activity
    3. Find booking links for each activity
    """
    job_id = previous_result["job_id"]
    trip_details = previous_result.get("trip_details", {})
    destination = trip_details.get("destination", "")

    db = SessionLocal()
    try:
        job_repo = JobRepository(db)

        # --- Phase 1: Extract activities ---
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

        # Pre-filter: only keep messages that mention the destination or related terms
        destination_lower = destination.lower()
        # Build keyword list from destination (e.g., "Bali, Indonesia" → ["bali", "indonesia"])
        keywords = [w.strip().lower() for w in destination_lower.replace(",", " ").split() if len(w.strip()) > 2]

        relevant_messages = []
        all_messages_with_content = [m for m in messages if m.content]

        for i, m in enumerate(all_messages_with_content):
            content_lower = m.content.lower()
            if any(kw in content_lower for kw in keywords):
                # Include this message + surrounding context (5 before, 5 after)
                start = max(0, i - 5)
                end = min(len(all_messages_with_content), i + 6)
                for j in range(start, end):
                    relevant_messages.append(all_messages_with_content[j])

        # Deduplicate while preserving order
        seen_ids: set[int] = set()
        unique_messages = []
        for m in relevant_messages:
            if id(m) not in seen_ids:
                seen_ids.add(id(m))
                unique_messages.append(m)

        message_dicts = [
            {"sender_name": m.sender_name, "content": m.content}
            for m in unique_messages
        ]

        logger.info(
            "Filtered %d → %d relevant messages for '%s'",
            len(all_messages_with_content), len(message_dicts), destination,
        )

        activities = asyncio.run(extract_activities(message_dicts, destination))

        job_repo.update_status(
            UUID(job_id),
            status="extracting",
            progress_message=f"Found {len(activities)} activities from your group chat",
            progress_percent=45,
        )

        logger.info("Extracted %d activities for job %s", len(activities), job_id)

        # --- Phase 2 & 3: Reviews + Booking for each activity ---
        total = len(activities)
        for i, activity in enumerate(activities):
            job_repo.update_status(
                UUID(job_id),
                status="verifying",
                progress_message=f"Checking reviews for '{activity.name}' ({i + 1}/{total})...",
                progress_percent=45 + int((i / max(total, 1)) * 45),
            )

            # Search reviews
            review = asyncio.run(
                search_reviews(activity.name, destination)
            )

            # Search booking links
            bookings = asyncio.run(
                search_booking_links(activity.name, destination)
            )

            # Save to database
            booking_json = [
                {
                    "provider": b.provider,
                    "url": b.url,
                    "title": b.title,
                    "price": b.price,
                }
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

        # Mark complete
        job_repo.update_status(
            UUID(job_id),
            status="complete",
            progress_message=f"Found {total} activities with reviews and booking links!",
            progress_percent=100,
        )

        logger.info(
            "Activity processing complete for job %s: %d activities",
            job_id, total,
        )

        return {"job_id": job_id, "activity_count": total}

    except Exception as e:
        logger.error("Activity processing failed for job %s: %s", job_id, e)
        job_repo.update_status(
            UUID(job_id),
            status="failed",
            error_message=f"Activity processing failed: {e}",
        )
        raise
    finally:
        db.close()
