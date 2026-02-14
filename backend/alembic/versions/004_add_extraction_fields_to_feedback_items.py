"""add extraction fields to feedback_items

Revision ID: 004
Revises: 003
Create Date: 2026-02-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("feedback_items", sa.Column("pain_point", sa.Text(), nullable=True))
    op.add_column("feedback_items", sa.Column("topic", sa.String(length=255), nullable=True))
    op.add_column("feedback_items", sa.Column("related_feature", sa.String(length=255), nullable=True))
    op.add_column("feedback_items", sa.Column("is_existing_feature", sa.Boolean(), nullable=True))
    op.add_column("feedback_items", sa.Column("feature_gap", sa.Text(), nullable=True))
    op.add_column("feedback_items", sa.Column("urgency", sa.String(length=50), nullable=True))
    op.add_column("feedback_items", sa.Column("sentiment", sa.String(length=50), nullable=True))
    op.add_column("feedback_items", sa.Column("verbatim_quote", sa.Text(), nullable=True))
    op.add_column("feedback_items", sa.Column("extraction_confidence", sa.Float(), nullable=True))
    op.add_column(
        "feedback_items",
        sa.Column("extraction_status", sa.String(length=50), nullable=False, server_default="pending"),
    )
    op.add_column("feedback_items", sa.Column("raw_llm_response", sa.Text(), nullable=True))
    op.add_column("feedback_items", sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_feedback_items_org_id_extraction_status",
        "feedback_items",
        ["org_id", "extraction_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_items_org_id_extraction_status", table_name="feedback_items")
    op.drop_column("feedback_items", "extracted_at")
    op.drop_column("feedback_items", "raw_llm_response")
    op.drop_column("feedback_items", "extraction_status")
    op.drop_column("feedback_items", "extraction_confidence")
    op.drop_column("feedback_items", "verbatim_quote")
    op.drop_column("feedback_items", "sentiment")
    op.drop_column("feedback_items", "urgency")
    op.drop_column("feedback_items", "feature_gap")
    op.drop_column("feedback_items", "is_existing_feature")
    op.drop_column("feedback_items", "related_feature")
    op.drop_column("feedback_items", "topic")
    op.drop_column("feedback_items", "pain_point")
