"""Pipeline orchestrator — runs processing in a background thread.

No Celery, no Redis needed. Uses threading so the API returns
immediately while work happens in the background.
"""

import logging
import threading

logger = logging.getLogger(__name__)


def _run_pipeline(job_id: str, file_url: str, chat_dir: str | None, trip_details: dict | None) -> None:
    from src.pipeline.runner import run_parse_zip, run_process_activities

    try:
        parse_result = run_parse_zip(job_id, file_url, chat_dir, trip_details)
        run_process_activities(parse_result)
    except Exception as e:
        logger.error("Pipeline failed for job %s: %s", job_id, e)


def process_upload(
    job_id: str,
    file_url: str,
    chat_dir: str | None = None,
    trip_details: dict | None = None,
) -> None:
    """Kick off processing in a background thread."""
    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, file_url, chat_dir, trip_details),
        daemon=True,
    )
    thread.start()
