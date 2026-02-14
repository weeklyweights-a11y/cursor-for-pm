"""add enrichment fields to feedback_items

Revision ID: 006
Revises: 005
Create Date: 2026-02-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "feedback_items",
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("feedback_items", sa.Column("customer_domain", sa.String(length=255), nullable=True))
    op.add_column("feedback_items", sa.Column("customer_name", sa.String(length=255), nullable=True))
    op.add_column("feedback_items", sa.Column("segment", sa.String(length=50), nullable=True))
    op.add_column("feedback_items", sa.Column("match_method", sa.String(length=50), nullable=True))
    op.add_column("feedback_items", sa.Column("match_confidence", sa.Float(), nullable=True))
    op.add_column(
        "feedback_items",
        sa.Column("match_status", sa.String(length=50), nullable=False, server_default="unmatched"),
    )
    op.add_column("feedback_items", sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_feedback_items_customer_id_customers",
        "feedback_items",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_feedback_items_customer_id", "feedback_items", ["customer_id"])
    op.create_index("ix_feedback_items_match_status", "feedback_items", ["match_status"])
    op.create_index("ix_feedback_items_org_id_customer_id", "feedback_items", ["org_id", "customer_id"])
    op.create_index("ix_feedback_items_org_id_match_status", "feedback_items", ["org_id", "match_status"])


def downgrade() -> None:
    op.drop_index("ix_feedback_items_org_id_match_status", table_name="feedback_items")
    op.drop_index("ix_feedback_items_org_id_customer_id", table_name="feedback_items")
    op.drop_index("ix_feedback_items_match_status", table_name="feedback_items")
    op.drop_index("ix_feedback_items_customer_id", table_name="feedback_items")
    op.drop_constraint("fk_feedback_items_customer_id_customers", "feedback_items", type_="foreignkey")
    op.drop_column("feedback_items", "enriched_at")
    op.drop_column("feedback_items", "match_status")
    op.drop_column("feedback_items", "match_confidence")
    op.drop_column("feedback_items", "match_method")
    op.drop_column("feedback_items", "segment")
    op.drop_column("feedback_items", "customer_name")
    op.drop_column("feedback_items", "customer_domain")
    op.drop_column("feedback_items", "customer_id")
