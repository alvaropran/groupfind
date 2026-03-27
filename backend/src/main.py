import logging

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.config import settings

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    """Auto-run alembic migrations on startup."""
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed")
    except Exception as e:
        logger.error("Migration failed: %s", e)


def create_app() -> FastAPI:
    _run_migrations()

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
