"""Rename transformer_score to tare_score in churn_scores.

Revision ID: 001
Revises: 000
Create Date: 2026-05-12
"""

from alembic import op

revision = "001"
down_revision = "000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("churn_scores", "transformer_score", new_column_name="tare_score")


def downgrade() -> None:
    op.alter_column("churn_scores", "tare_score", new_column_name="transformer_score")
