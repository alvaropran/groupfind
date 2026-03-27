from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin


def _default_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=24)


class SessionModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sessions"

    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    group_chat_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    participant_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_default_expiry,
        nullable=False,
    )

    jobs: Mapped[list["JobModel"]] = relationship(back_populates="session")  # noqa: F821
