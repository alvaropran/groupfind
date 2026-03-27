"""Celery task: Classify events/venues using LLM entity extraction."""

import asyncio
import logging
from decimal import Decimal
from uuid import UUID

from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.event import DiscoveredEventModel
from src.models.message import ExtractedMessageModel
from src.models.reel import ExtractedReelModel
from src.pipeline.utils.entity_extractor import extract_entities
from src.pipeline.utils.geocoder import geocode
from src.pipeline.utils.url_generator import generate_calendar_url, generate_maps_url
from src.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=15)
def classify_events_task(self, previous_result: dict) -> dict:
    """Extract and classify venues/events from messages and reel captions.

    Args:
        previous_result: Output from extract_reels_task with job_id.

    Returns:
        Dict with job_id and event counts.
    """
    job_id = previous_result["job_id"]
    focus = previous_result.get("focus")
    db = SessionLocal()
    try:
        job_repo = JobRepository(db)
        job_repo.update_status(
            UUID(job_id),
            status="classifying",
            progress_message="Identifying venues and events...",
            progress_percent=50,
        )

        # Gather all messages
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

        # Gather reel captions
        reels = (
            db.query(ExtractedReelModel)
            .filter(
                ExtractedReelModel.job_id == UUID(job_id),
                ExtractedReelModel.extraction_status == "success",
            )
            .all()
        )

        captions = [r.caption for r in reels if r.caption]

        # Run entity extraction (async -> sync bridge for Celery)
        entities = asyncio.run(extract_entities(message_dicts, captions, focus=focus))

        job_repo.update_status(
            UUID(job_id),
            status="classifying",
            progress_message=f"Found {len(entities)} venues/events, generating links...",
            progress_percent=65,
        )

        # Insert discovered events with geocoding
        for i, entity in enumerate(entities):
            # Build the best address we have
            has_specific_address = entity.address and entity.city
            geocode_query = entity.address if has_specific_address else (
                f"{entity.name}, {entity.city}, {entity.country}" if entity.city and entity.country
                else f"{entity.name}, {entity.city}" if entity.city
                else None
            )

            latitude = None
            longitude = None
            resolved_address = entity.address

            # Only geocode if we have enough location info (not just a name)
            if geocode_query and entity.city:
                job_repo.update_status(
                    UUID(job_id),
                    status="classifying",
                    progress_message=f"Geocoding '{entity.name}' ({i + 1}/{len(entities)})...",
                    progress_percent=60 + int((i / max(len(entities), 1)) * 8),
                )

                geo_result = asyncio.run(geocode(geocode_query))
                if geo_result:
                    latitude = Decimal(str(geo_result.latitude))
                    longitude = Decimal(str(geo_result.longitude))
                    resolved_address = geo_result.display_name

            display_address = resolved_address or (
                f"{entity.city}, {entity.country}" if entity.city and entity.country
                else entity.city
            )

            maps_url = generate_maps_url(entity.name, display_address)
            calendar_url = generate_calendar_url(
                entity.name,
                location=display_address,
                description=entity.description,
            )

            event = DiscoveredEventModel(
                job_id=UUID(job_id),
                name=entity.name,
                category=entity.category,
                description=entity.description,
                city=entity.city,
                address=display_address,
                latitude=latitude,
                longitude=longitude,
                confidence_score=Decimal(str(round(entity.confidence, 2))),
                source_type="chat_message",
                google_maps_url=maps_url,
                google_calendar_url=calendar_url,
            )
            db.add(event)

        db.commit()

        logger.info("Classified %d events for job %s", len(entities), job_id)

        return {
            "job_id": job_id,
            "event_count": len(entities),
        }

    except Exception as e:
        logger.error("Event classification failed for job %s: %s", job_id, e)
        job_repo.update_status(
            UUID(job_id),
            status="failed",
            error_message=f"Event classification failed: {e}",
        )
        raise
    finally:
        db.close()
