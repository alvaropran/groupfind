import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin


class DiscoveredEventModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "discovered_events"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="other", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8), nullable=True)
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.00"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extracted_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_reel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extracted_reels.id", ondelete="SET NULL"),
        nullable=True,
    )
    google_maps_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_calendar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reddit_sentiment: Mapped[str] = mapped_column(
        String(50), default="not_found", nullable=False
    )
    reddit_mention_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    reddit_verifications: Mapped[list["RedditVerificationModel"]] = relationship(  # noqa: F821
        back_populates="event"
    )
