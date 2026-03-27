"""Celery task: Extract reel metadata via Instaloader."""

import logging
from uuid import UUID

from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.reel import ExtractedReelModel
from src.pipeline.utils.reel_fetcher import fetch_reel_metadata, ReelFetchError
from src.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)

import time

RATE_LIMIT_SECONDS = 3.0


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def extract_reels_task(self, previous_result: dict) -> dict:
    """Extract metadata for all pending reels in a job.

    Args:
        previous_result: Output from parse_zip_task with job_id.

    Returns:
        Dict with job_id and extraction counts.
    """
    job_id = previous_result["job_id"]
    db = SessionLocal()
    try:
        job_repo = JobRepository(db)
        job_repo.update_status(
            UUID(job_id),
            status="extracting_reels",
            progress_message="Extracting reel metadata...",
            progress_percent=25,
        )

        # Get all pending reels for this job
        reels = (
            db.query(ExtractedReelModel)
            .filter(
                ExtractedReelModel.job_id == UUID(job_id),
                ExtractedReelModel.extraction_status == "pending",
            )
            .all()
        )

        total = len(reels)
        success_count = 0
        fail_count = 0

        for i, reel in enumerate(reels):
            job_repo.update_status(
                UUID(job_id),
                status="extracting_reels",
                progress_message=f"Extracting reel {i + 1}/{total}...",
                progress_percent=25 + int((i / max(total, 1)) * 20),
            )

            try:
                metadata = fetch_reel_metadata(reel.reel_url)
                reel.caption = metadata.caption
                reel.location_tag = metadata.location_name
                reel.hashtags = metadata.hashtags
                reel.owner_username = metadata.owner_username
                reel.extraction_status = "success"
                reel.raw_metadata = {
                    "shortcode": metadata.shortcode,
                    "caption": metadata.caption,
                    "location": metadata.location_name,
                    "hashtags": metadata.hashtags,
                    "owner": metadata.owner_username,
                }
                success_count += 1
            except ReelFetchError as e:
                logger.warning("Failed to extract reel %s: %s", reel.reel_url, e)
                reel.extraction_status = "failed"
                reel.extraction_error = str(e)
                fail_count += 1

            db.commit()

            # Rate limit between requests
            if i < total - 1:
                time.sleep(RATE_LIMIT_SECONDS)

        job_repo.update_status(
            UUID(job_id),
            status="extracting_reels",
            progress_message=f"Extracted {success_count}/{total} reels",
            progress_percent=45,
        )

        logger.info(
            "Reel extraction for job %s: %d success, %d failed out of %d",
            job_id, success_count, fail_count, total,
        )

        return {
            "job_id": job_id,
            "reels_extracted": success_count,
            "reels_failed": fail_count,
        }

    except Exception as e:
        logger.error("Reel extraction failed for job %s: %s", job_id, e)
        job_repo.update_status(
            UUID(job_id),
            status="failed",
            error_message=f"Reel extraction failed: {e}",
        )
        raise
    finally:
        db.close()
