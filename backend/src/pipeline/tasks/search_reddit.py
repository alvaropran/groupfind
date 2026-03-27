"""Celery task: Search Reddit for event/venue verification."""

import asyncio
import logging
from uuid import UUID

from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.event import DiscoveredEventModel
from src.models.reddit_verification import RedditVerificationModel
from src.pipeline.utils.reddit_searcher import search_reddit
from src.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)

MINIMUM_CONFIDENCE = 0.5


@celery_app.task(bind=True, max_retries=2, default_retry_delay=15)
def search_reddit_task(self, previous_result: dict) -> dict:
    """Search Reddit for each discovered event with sufficient confidence.

    Args:
        previous_result: Output from classify_events_task with job_id.

    Returns:
        Dict with job_id and verification counts.
    """
    job_id = previous_result["job_id"]
    db = SessionLocal()
    try:
        job_repo = JobRepository(db)
        job_repo.update_status(
            UUID(job_id),
            status="searching_reddit",
            progress_message="Searching Reddit for reviews...",
            progress_percent=70,
        )

        events = (
            db.query(DiscoveredEventModel)
            .filter(
                DiscoveredEventModel.job_id == UUID(job_id),
                DiscoveredEventModel.confidence_score >= MINIMUM_CONFIDENCE,
            )
            .all()
        )

        total = len(events)
        verified_count = 0

        for i, event in enumerate(events):
            job_repo.update_status(
                UUID(job_id),
                status="searching_reddit",
                progress_message=f"Searching Reddit for '{event.name}' ({i + 1}/{total})...",
                progress_percent=70 + int((i / max(total, 1)) * 20),
            )

            try:
                results = asyncio.run(
                    search_reddit(event.name, city=event.city, limit=5)
                )

                if results:
                    verified_count += 1

                    # Determine overall sentiment from scores
                    avg_score = sum(r.post_score for r in results) / len(results)
                    if avg_score >= 10:
                        sentiment = "positive"
                    elif avg_score >= 0:
                        sentiment = "mixed"
                    else:
                        sentiment = "negative"

                    event.reddit_sentiment = sentiment
                    event.reddit_mention_count = len(results)

                    for result in results:
                        verification = RedditVerificationModel(
                            event_id=event.id,
                            subreddit=result.subreddit,
                            post_title=result.post_title,
                            post_url=result.post_url,
                            post_score=result.post_score,
                            comment_snippet=result.comment_snippet,
                            sentiment=sentiment,
                            search_query=event.name,
                            search_source=result.search_source,
                        )
                        db.add(verification)

                    db.commit()

            except Exception as e:
                logger.warning(
                    "Reddit search failed for event '%s': %s", event.name, e
                )
                continue

        # Mark job as complete
        job_repo.update_status(
            UUID(job_id),
            status="complete",
            progress_message=f"Done! Found {total} events, {verified_count} verified on Reddit",
            progress_percent=100,
        )

        logger.info(
            "Reddit search for job %s: %d events searched, %d verified",
            job_id, total, verified_count,
        )

        return {
            "job_id": job_id,
            "events_searched": total,
            "events_verified": verified_count,
        }

    except Exception as e:
        logger.error("Reddit search failed for job %s: %s", job_id, e)
        job_repo.update_status(
            UUID(job_id),
            status="failed",
            error_message=f"Reddit search failed: {e}",
        )
        raise
    finally:
        db.close()
