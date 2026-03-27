from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.job import JobModel
from src.repositories.base import BaseRepository


class JobRepository(BaseRepository[JobModel]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, JobModel)

    def create(self, session_id: UUID) -> JobModel:
        return self.create_from_dict({"session_id": session_id, "status": "pending"})

    def update_status(
        self,
        job_id: UUID,
        *,
        status: str,
        progress_message: str | None = None,
        progress_percent: int | None = None,
        error_message: str | None = None,
    ) -> JobModel | None:
        job = self.get_by_id(job_id)
        if job is None:
            return None

        job.status = status
        if progress_message is not None:
            job.progress_message = progress_message
        if progress_percent is not None:
            job.progress_percent = progress_percent
        if error_message is not None:
            job.error_message = error_message

        if status == "pending" and job.started_at is None:
            job.started_at = datetime.now(timezone.utc)
        if status in ("complete", "failed"):
            job.completed_at = datetime.now(timezone.utc)

        self._db.commit()
        self._db.refresh(job)
        return job
