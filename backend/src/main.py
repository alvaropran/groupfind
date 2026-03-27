from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="GroupFind API",
        description="Instagram group chat activity planner backend",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
