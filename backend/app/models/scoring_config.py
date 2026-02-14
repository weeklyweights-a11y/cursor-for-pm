from uuid import UUID

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ScoringConfig(Base, TimestampMixin):
    """Per-org scoring weights and goals for theme prioritization."""

    __tablename__ = "scoring_configs"

    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    goals: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    target_segments: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    weight_volume: Mapped[float] = mapped_column(Float, default=0.25, nullable=False)
    weight_reach: Mapped[float] = mapped_column(Float, default=0.20, nullable=False)
    weight_urgency: Mapped[float] = mapped_column(Float, default=0.25, nullable=False)
    weight_sentiment: Mapped[float] = mapped_column(Float, default=0.15, nullable=False)
    weight_strategic_fit: Mapped[float] = mapped_column(Float, default=0.15, nullable=False)

    organization = relationship("Organization", backref="scoring_config")
