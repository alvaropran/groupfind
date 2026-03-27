from uuid import UUID

from src.api.jobs.schemas import CreateJobResponse, JobStatus, JobStatusResponse, TripDetails
from src.repositories.job_repository import JobRepository
from src.repositories.session_repository import SessionRepository


class JobService:
    def __init__(
        self,
        session_repo: SessionRepository,
        job_repo: JobRepository,
    ) -> None:
        self._session_repo = session_repo
        self._job_repo = job_repo

    def create_job(
        self,
        file_url: str,
        chat_dir: str | None = None,
        trip_details: TripDetails | None = None,
    ) -> CreateJobResponse:
        session = self._session_repo.create(file_url=file_url)
        job = self._job_repo.create(session_id=session.id)

        from src.pipeline.orchestrator import process_upload

        trip_dict = trip_details.model_dump() if trip_details else None
        process_upload(str(job.id), file_url, chat_dir=chat_dir, trip_details=trip_dict)

        return CreateJobResponse(job_id=job.id, session_id=session.id)

    def get_job_status(self, job_id: UUID) -> JobStatusResponse | None:
        job = self._job_repo.get_by_id(job_id)
        if job is None:
            return None
        return JobStatusResponse(
            job_id=job.id,
            status=JobStatus(job.status),
            progress_message=job.progress_message,
            progress_percent=job.progress_percent,
            error_message=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
