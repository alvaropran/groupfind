from collections.abc import Generator

from sqlalchemy.orm import Session

from src.api.jobs.service import JobService
from src.database import SessionLocal
from src.repositories.job_repository import JobRepository
from src.repositories.session_repository import SessionRepository


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_job_service() -> Generator[JobService, None, None]:
    db = SessionLocal()
    try:
        session_repo = SessionRepository(db)
        job_repo = JobRepository(db)
        yield JobService(session_repo=session_repo, job_repo=job_repo)
    finally:
        db.close()
