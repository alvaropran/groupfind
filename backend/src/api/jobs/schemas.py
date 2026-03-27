from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class JobStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"


class TripDetails(BaseModel):
    destination: str
    start_date: str  # ISO date string
    num_days: int
    num_travelers: int
    vibes: list[str]


class CreateJobRequest(BaseModel):
    file_url: str
    chat_dir: str | None = None
    trip_details: TripDetails | None = None


class CreateJobResponse(BaseModel):
    job_id: UUID
    session_id: UUID


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    progress_message: str | None = None
    progress_percent: int = 0
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
