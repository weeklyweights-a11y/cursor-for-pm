from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FeedbackItem(Base, TimestampMixin):
    """Feedback item from CSV, manual, or Slack. Deduplicated by (org_id, source_id)."""

    __tablename__ = "feedback_items"
    __table_args__ = (UniqueConstraint("org_id", "source_id", name="uq_feedback_items_org_source"),)

    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # csv | manual | slack
    source_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # when feedback was given
    author_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    batch_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Extraction (Phase 3 / Layer 2)
    pain_point: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_feature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_existing_feature: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feature_gap: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(50), nullable=True)  # low, medium, high, critical
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)  # positive, neutral, negative
    verbatim_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")  # pending, completed, failed
    raw_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Enrichment (Phase 4)
    customer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    segment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    match_method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # exact, llm_fuzzy, manual
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unmatched", index=True)  # unmatched, pm_review, matched
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Phase 5: embedding and clustering
    embedding: Mapped[list | None] = mapped_column(Vector(384), nullable=True)
    theme_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("themes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clustered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", backref="feedback_items")
    theme = relationship("Theme", back_populates="feedback_items", foreign_keys=[theme_id])
    batch = relationship("Batch", backref="feedback_items")
    customer = relationship("Customer", back_populates="feedback_items", foreign_keys=[customer_id])
