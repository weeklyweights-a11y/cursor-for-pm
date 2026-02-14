from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DomainMapping(Base, TimestampMixin):
    """Saved mapping from source_domain to customer (or negative). One per (org_id, source_domain)."""

    __tablename__ = "domain_mappings"
    __table_args__ = (UniqueConstraint("org_id", "source_domain", name="uq_domain_mappings_org_source"),)

    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_method: Mapped[str] = mapped_column(String(50), nullable=False)  # exact, llm_fuzzy, manual
    confirmed_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    organization = relationship("Organization", backref="domain_mappings")
    customer = relationship("Customer", backref="domain_mappings")
