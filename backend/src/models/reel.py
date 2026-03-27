import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDPrimaryKeyMixin


class ExtractedReelModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "extracted_reels"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extracted_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    reel_url: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_tag: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    owner_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extraction_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
