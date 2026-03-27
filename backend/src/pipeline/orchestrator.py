"""Pipeline orchestrator — 2-task chain for activity extraction + verification."""

from celery import chain

from src.pipeline.tasks.parse_zip import parse_zip_task
from src.pipeline.tasks.process_activities import process_activities_task


def process_upload(
    job_id: str,
    file_url: str,
    chat_dir: str | None = None,
    trip_details: dict | None = None,
) -> None:
    """Kick off: parse ZIP → extract + verify activities."""
    pipeline = chain(
        parse_zip_task.s(job_id, file_url, chat_dir, trip_details),
        process_activities_task.s(),
    )
    pipeline.apply_async()
