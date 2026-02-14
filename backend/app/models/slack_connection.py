from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SlackConnection(Base, TimestampMixin):
    """Slack OAuth connection per organization. access_token stored encrypted."""

    __tablename__ = "slack_connections"
    __table_args__ = (UniqueConstraint("org_id", name="uq_slack_connections_org_id"),)

    org_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(String(64), nullable=False)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)  # encrypted
    bot_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    incoming_channels: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)  # channel IDs to ingest from
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    organization = relationship("Organization", backref="slack_connection")
