from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.jobs.schemas import CreateJobRequest, CreateJobResponse, JobStatusResponse
from src.api.jobs.service import JobService
from src.dependencies import get_job_service

router = APIRouter()


@router.post("", response_model=CreateJobResponse, status_code=201)
async def create_job(
    request: CreateJobRequest,
    service: JobService = Depends(get_job_service),
) -> CreateJobResponse:
    return service.create_job(
        file_url=request.file_url,
        chat_dir=request.chat_dir,
        trip_details=request.trip_details,
    )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    result = service.get_job_status(job_id=job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result
