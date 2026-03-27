import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin


class ItineraryModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "itineraries"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    num_days: Mapped[int] = mapped_column(Integer, nullable=False)
    num_travelers: Mapped[int] = mapped_column(Integer, nullable=False)
    vibes: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    raw_recommendations: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    days: Mapped[list["ItineraryDayModel"]] = relationship(
        back_populates="itinerary",
        order_by="ItineraryDayModel.day_number",
        cascade="all, delete-orphan",
    )


class ItineraryDayModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "itinerary_days"

    itinerary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    itinerary: Mapped["ItineraryModel"] = relationship(back_populates="days")
    slots: Mapped[list["ItinerarySlotModel"]] = relationship(
        back_populates="day",
        order_by="ItinerarySlotModel.sort_order",
        cascade="all, delete-orphan",
    )


class ItinerarySlotModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "itinerary_slots"

    day_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("itinerary_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    time_of_day: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    who_suggested: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tip: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_maps_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_calendar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    day: Mapped["ItineraryDayModel"] = relationship(back_populates="slots")
