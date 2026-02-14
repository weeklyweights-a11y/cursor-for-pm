from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Theme(Base, TimestampMixin):
    """Clustered theme of feedback items. One per org per cluster run."""

    __tablename__ = "themes"

    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    centroid: Mapped[list | None] = mapped_column(Vector(384), nullable=True)
    mention_count: Mapped[int] = mapped_column(default=0, nullable=False)
    unique_customers: Mapped[int] = mapped_column(default=0, nullable=False)
    segment_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    urgency_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sentiment_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    top_quotes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_current: Mapped[bool] = mapped_column(default=True, nullable=False)

    organization = relationship("Organization", backref="themes")
    feedback_items = relationship(
        "FeedbackItem",
        back_populates="theme",
        foreign_keys="FeedbackItem.theme_id",
    )
