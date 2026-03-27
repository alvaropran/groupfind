"""Celery task: Generate a day-by-day itinerary from chat messages."""

import asyncio
import json
import logging
from datetime import date, timedelta
from uuid import UUID

from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.itinerary import ItineraryDayModel, ItineraryModel, ItinerarySlotModel
from src.models.message import ExtractedMessageModel
from src.pipeline.utils.itinerary_generator import extract_recommendations, generate_itinerary
from src.pipeline.utils.url_generator import generate_calendar_url, generate_maps_url
from src.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=15)
def generate_itinerary_task(self, previous_result: dict) -> dict:
    """Extract recommendations from chat and generate a day-by-day itinerary.

    Two-phase LLM approach:
    Phase A — Extract what friends recommended from messages
    Phase B — Plan the itinerary using those recommendations + trip details
    """
    job_id = previous_result["job_id"]
    trip_details = previous_result.get("trip_details", {})

    destination = trip_details.get("destination", "")
    start_date_str = trip_details.get("start_date", "")
    num_days = trip_details.get("num_days", 7)
    num_travelers = trip_details.get("num_travelers", 2)
    vibes = trip_details.get("vibes", [])

    db = SessionLocal()
    try:
        job_repo = JobRepository(db)

        # --- Phase A: Extract recommendations ---
        job_repo.update_status(
            UUID(job_id),
            status="extracting",
            progress_message=f"Reading your chat for {destination} recommendations...",
            progress_percent=30,
        )

        messages = (
            db.query(ExtractedMessageModel)
            .filter(ExtractedMessageModel.job_id == UUID(job_id))
            .order_by(ExtractedMessageModel.timestamp_ms)
            .all()
        )

        message_dicts = [
            {"sender_name": m.sender_name, "content": m.content}
            for m in messages
            if m.content
        ]

        recommendations = asyncio.run(
            extract_recommendations(message_dicts, destination)
        )

        job_repo.update_status(
            UUID(job_id),
            status="extracting",
            progress_message=f"Found {len(recommendations)} recommendations from your friends",
            progress_percent=55,
        )

        logger.info(
            "Phase A for job %s: extracted %d recommendations",
            job_id, len(recommendations),
        )

        # --- Phase B: Generate itinerary ---
        job_repo.update_status(
            UUID(job_id),
            status="planning",
            progress_message=f"Planning your {num_days}-day {destination} itinerary...",
            progress_percent=65,
        )

        result = asyncio.run(generate_itinerary(
            recommendations=recommendations,
            destination=destination,
            start_date=start_date_str,
            num_days=num_days,
            num_travelers=num_travelers,
            vibes=vibes,
        ))

        job_repo.update_status(
            UUID(job_id),
            status="planning",
            progress_message="Saving your itinerary...",
            progress_percent=90,
        )

        # --- Save to database ---
        start_date = date.fromisoformat(start_date_str) if start_date_str else date.today()

        # Serialize recommendations for storage
        recs_json = [
            {
                "name": r.name,
                "type": r.type,
                "who_said": r.who_said,
                "what_they_said": r.what_they_said,
                "tips": r.tips,
                "area": r.area,
            }
            for r in result.recommendations
        ]

        itinerary = ItineraryModel(
            job_id=UUID(job_id),
            destination=destination,
            start_date=start_date,
            num_days=num_days,
            num_travelers=num_travelers,
            vibes=vibes,
            raw_recommendations={"recommendations": recs_json},
        )
        db.add(itinerary)
        db.flush()

        for day_data in result.days:
            day_date = start_date + timedelta(days=day_data.day_number - 1)

            day = ItineraryDayModel(
                itinerary_id=itinerary.id,
                day_number=day_data.day_number,
                date=day_date,
                title=day_data.title,
                notes=day_data.notes,
            )
            db.add(day)
            db.flush()

            for i, slot_data in enumerate(day_data.slots):
                maps_url = None
                calendar_url = None

                if slot_data.location:
                    maps_url = generate_maps_url(
                        slot_data.activity_name, slot_data.location
                    )

                calendar_url = generate_calendar_url(
                    slot_data.activity_name,
                    location=slot_data.location,
                    description=slot_data.description,
                )

                slot = ItinerarySlotModel(
                    day_id=day.id,
                    time_of_day=slot_data.time_of_day,
                    sort_order=i,
                    activity_name=slot_data.activity_name,
                    description=slot_data.description,
                    who_suggested=slot_data.who_suggested,
                    tip=slot_data.tip,
                    location=slot_data.location,
                    google_maps_url=maps_url,
                    google_calendar_url=calendar_url,
                )
                db.add(slot)

        db.commit()

        # Mark complete
        job_repo.update_status(
            UUID(job_id),
            status="complete",
            progress_message=f"Your {num_days}-day {destination} itinerary is ready!",
            progress_percent=100,
        )

        logger.info(
            "Itinerary generated for job %s: %d days, %d recommendations",
            job_id, len(result.days), len(result.recommendations),
        )

        return {
            "job_id": job_id,
            "days": len(result.days),
            "recommendations": len(result.recommendations),
        }

    except Exception as e:
        logger.error("Itinerary generation failed for job %s: %s", job_id, e)
        job_repo.update_status(
            UUID(job_id),
            status="failed",
            error_message=f"Itinerary generation failed: {e}",
        )
        raise
    finally:
        db.close()
