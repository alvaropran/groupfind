import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDPrimaryKeyMixin


class ActivityModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "activities"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    area: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    who_suggested: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_they_said: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Review data
    review_rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_pros: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    review_cons: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    review_best_tip: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_sources: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Booking links stored as JSON array
    booking_options: Mapped[list | None] = mapped_column(JSON, nullable=True)
