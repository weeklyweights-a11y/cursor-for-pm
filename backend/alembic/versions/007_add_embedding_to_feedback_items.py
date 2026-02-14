"""add embedding columns to feedback_items (Phase 5)

Revision ID: 007
Revises: 006
Create Date: Phase 5

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE feedback_items ADD COLUMN embedding vector(384)")
    op.add_column(
        "feedback_items",
        sa.Column("is_outlier", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "feedback_items",
        sa.Column("clustered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "CREATE INDEX ix_feedback_items_embedding_hnsw ON feedback_items "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_feedback_items_embedding_hnsw")
    op.drop_column("feedback_items", "clustered_at")
    op.drop_column("feedback_items", "is_outlier")
    op.execute("ALTER TABLE feedback_items DROP COLUMN IF EXISTS embedding")
