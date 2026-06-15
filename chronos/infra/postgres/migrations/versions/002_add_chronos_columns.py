"""Add CHRONOS scoring columns to churn_scores.

Revision ID: 002
Revises: 001
Create Date: 2026-05-12
"""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("churn_scores", sa.Column("treatability_score", sa.Numeric(5, 4), nullable=True))
    op.add_column("churn_scores", sa.Column("action_score", sa.Numeric(5, 4), nullable=True))
    op.add_column("churn_scores", sa.Column("scoring_pass", sa.String(10), nullable=True))
    op.add_column("churn_scores", sa.Column("reason_codes_v2", sa.JSON(), nullable=True))
    op.add_column("churn_scores", sa.Column("anomaly_flag", sa.Boolean(), server_default="FALSE", nullable=False))


def downgrade() -> None:
    op.drop_column("churn_scores", "anomaly_flag")
    op.drop_column("churn_scores", "reason_codes_v2")
    op.drop_column("churn_scores", "scoring_pass")
    op.drop_column("churn_scores", "action_score")
    op.drop_column("churn_scores", "treatability_score")
