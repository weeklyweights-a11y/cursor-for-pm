"""create specs (Phase 8)

Revision ID: 011
Revises: 010
Create Date: Phase 8

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "specs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brief_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="generating"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("target_audience", sa.String(20), nullable=False),
        sa.Column("sections", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brief_id"], ["briefs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_specs_org_id", "specs", ["org_id"])
    op.create_index("ix_specs_brief_id", "specs", ["brief_id"])
    op.create_index("ix_specs_theme_id", "specs", ["theme_id"])
    op.create_index("ix_specs_org_id_brief_id", "specs", ["org_id", "brief_id"])
    op.create_index("ix_specs_org_id_theme_id", "specs", ["org_id", "theme_id"])
    op.create_index("ix_specs_org_id_is_current", "specs", ["org_id", "is_current"])


def downgrade() -> None:
    op.drop_index("ix_specs_org_id_is_current", table_name="specs")
    op.drop_index("ix_specs_org_id_theme_id", table_name="specs")
    op.drop_index("ix_specs_org_id_brief_id", table_name="specs")
    op.drop_index("ix_specs_theme_id", table_name="specs")
    op.drop_index("ix_specs_brief_id", table_name="specs")
    op.drop_index("ix_specs_org_id", table_name="specs")
    op.drop_table("specs")
