"""create themes and scoring_configs; add theme_id to feedback_items (Phase 5)

Revision ID: 008
Revises: 007
Create Date: Phase 5

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "themes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_customers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("segment_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("urgency_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("sentiment_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("top_quotes", postgresql.JSONB(), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.execute("ALTER TABLE themes ADD COLUMN centroid vector(384)")
    op.create_index("ix_themes_org_id", "themes", ["org_id"])
    op.create_index("ix_themes_org_id_is_current", "themes", ["org_id", "is_current"])
    op.create_index("ix_themes_priority_score", "themes", ["priority_score"])

    op.create_table(
        "scoring_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goals", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("target_segments", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("weight_volume", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("weight_reach", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("weight_urgency", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("weight_sentiment", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("weight_strategic_fit", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_scoring_configs_org_id", "scoring_configs", ["org_id"], unique=True)

    op.add_column(
        "feedback_items",
        sa.Column("theme_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_feedback_items_theme_id_themes",
        "feedback_items",
        "themes",
        ["theme_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_feedback_items_theme_id", "feedback_items", ["theme_id"])
    op.create_index("ix_feedback_items_org_id_theme_id", "feedback_items", ["org_id", "theme_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_items_org_id_theme_id", table_name="feedback_items")
    op.drop_index("ix_feedback_items_theme_id", table_name="feedback_items")
    op.drop_constraint("fk_feedback_items_theme_id_themes", "feedback_items", type_="foreignkey")
    op.drop_column("feedback_items", "theme_id")
    op.drop_index("ix_scoring_configs_org_id", table_name="scoring_configs")
    op.drop_table("scoring_configs")
    op.drop_index("ix_themes_priority_score", table_name="themes")
    op.drop_index("ix_themes_org_id_is_current", table_name="themes")
    op.drop_index("ix_themes_org_id", table_name="themes")
    op.drop_table("themes")
