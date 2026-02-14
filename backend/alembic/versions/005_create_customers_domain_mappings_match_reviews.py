"""create customers, domain_mappings, match_review_queue

Revision ID: 005
Revises: 004
Create Date: 2026-02-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("segment", sa.String(length=50), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "domain", name="uq_customers_org_domain"),
    )
    op.create_index("ix_customers_org_id", "customers", ["org_id"])
    op.create_index("ix_customers_domain", "customers", ["domain"])

    op.create_table(
        "domain_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("source_company_name", sa.String(length=255), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("match_method", sa.String(length=50), nullable=False),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "source_domain", name="uq_domain_mappings_org_source"),
    )
    op.create_index("ix_domain_mappings_org_id", "domain_mappings", ["org_id"])
    op.create_index("ix_domain_mappings_source_domain", "domain_mappings", ["source_domain"])

    op.create_table(
        "match_review_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feedback_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("source_company_name", sa.String(length=255), nullable=True),
        sa.Column("candidate_customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("candidate_customer_name", sa.String(length=255), nullable=True),
        sa.Column("candidate_domain", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feedback_item_id"], ["feedback_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_review_queue_org_id", "match_review_queue", ["org_id"])
    op.create_index("ix_match_review_queue_feedback_item_id", "match_review_queue", ["feedback_item_id"])
    op.create_index("ix_match_review_queue_status", "match_review_queue", ["status"])
    op.create_index("ix_match_review_queue_org_id_status", "match_review_queue", ["org_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_match_review_queue_org_id_status", table_name="match_review_queue")
    op.drop_index("ix_match_review_queue_status", table_name="match_review_queue")
    op.drop_index("ix_match_review_queue_feedback_item_id", table_name="match_review_queue")
    op.drop_index("ix_match_review_queue_org_id", table_name="match_review_queue")
    op.drop_table("match_review_queue")
    op.drop_index("ix_domain_mappings_source_domain", table_name="domain_mappings")
    op.drop_index("ix_domain_mappings_org_id", table_name="domain_mappings")
    op.drop_table("domain_mappings")
    op.drop_index("ix_customers_domain", table_name="customers")
    op.drop_index("ix_customers_org_id", table_name="customers")
    op.drop_table("customers")
