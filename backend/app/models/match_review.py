from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MatchReviewQueue(Base, TimestampMixin):
    """PM review queue for uncertain domain→customer matches."""

    __tablename__ = "match_review_queue"
    __table_args__ = (Index("ix_match_review_queue_org_id_status", "org_id", "status"),)

    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feedback_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("feedback_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    source_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_customer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    candidate_customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)  # pending, confirmed, rejected, skipped
    resolved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", backref="match_review_queue")
    feedback_item = relationship("FeedbackItem", backref="match_review_entries")
    candidate_customer = relationship("Customer", backref="match_review_entries")
