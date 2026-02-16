"""create briefs (Phase 7)

Revision ID: 010
Revises: 009
Create Date: Phase 7

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="generating"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("sections", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("solution_evaluation", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_briefs_org_id", "briefs", ["org_id"])
    op.create_index("ix_briefs_theme_id", "briefs", ["theme_id"])
    op.create_index("ix_briefs_org_id_theme_id", "briefs", ["org_id", "theme_id"])
    op.create_index("ix_briefs_org_id_is_current", "briefs", ["org_id", "is_current"])


def downgrade() -> None:
    op.drop_index("ix_briefs_org_id_is_current", table_name="briefs")
    op.drop_index("ix_briefs_org_id_theme_id", table_name="briefs")
    op.drop_index("ix_briefs_theme_id", table_name="briefs")
    op.drop_index("ix_briefs_org_id", table_name="briefs")
    op.drop_table("briefs")
