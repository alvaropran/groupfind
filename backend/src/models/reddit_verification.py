import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin


class RedditVerificationModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "reddit_verifications"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovered_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subreddit: Mapped[str] = mapped_column(String(255), nullable=False)
    post_title: Mapped[str] = mapped_column(Text, nullable=False)
    post_url: Mapped[str] = mapped_column(Text, nullable=False)
    post_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_snippet: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sentiment: Mapped[str] = mapped_column(String(50), default="mixed", nullable=False)
    search_query: Mapped[str] = mapped_column(Text, nullable=False)
    search_source: Mapped[str] = mapped_column(String(50), nullable=False)

    event: Mapped["DiscoveredEventModel"] = relationship(  # noqa: F821
        back_populates="reddit_verifications"
    )
