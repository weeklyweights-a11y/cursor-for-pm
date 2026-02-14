"""create product_contexts

Revision ID: 003
Revises: 002
Create Date: 2026-02-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("product_description", sa.Text(), nullable=False),
        sa.Column("existing_features", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("target_users", sa.String(length=500), nullable=True),
        sa.Column("known_limitations", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("additional_context", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", name="uq_product_contexts_org_id"),
    )
    op.create_index("ix_product_contexts_org_id", "product_contexts", ["org_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_product_contexts_org_id", table_name="product_contexts")
    op.drop_table("product_contexts")
