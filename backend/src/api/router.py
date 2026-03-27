from fastapi import APIRouter

from src.api.chats.router import router as chats_router
from src.api.health.router import router as health_router
from src.api.jobs.router import router as jobs_router
from src.api.results.router import router as results_router
from src.api.upload.router import router as upload_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(chats_router, prefix="/chats", tags=["chats"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
api_router.include_router(upload_router, prefix="/upload", tags=["upload"])
api_router.include_router(results_router, prefix="/results", tags=["results"])
