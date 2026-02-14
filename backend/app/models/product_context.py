from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ProductContext(Base, TimestampMixin):
    """Product context per organization for extraction prompts. One per org."""

    __tablename__ = "product_contexts"

    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_description: Mapped[str] = mapped_column(Text, nullable=False)
    existing_features: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    target_users: Mapped[str | None] = mapped_column(String(500), nullable=True)
    known_limitations: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    additional_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization = relationship("Organization", backref="product_context")
