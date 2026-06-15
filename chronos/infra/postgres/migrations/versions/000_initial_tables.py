"""Create initial churn_scores and signal_results tables.

Revision ID: 000
Revises:
Create Date: 2026-05-19
"""
import sqlalchemy as sa
from alembic import op

revision = "000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "churn_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("final_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("risk_tier", sa.String(10), nullable=True),
        sa.Column("transformer_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("habitat_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("reason_codes", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("scored_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_cold_start", sa.Boolean(), server_default="FALSE", nullable=False),
    )
    op.create_index("ix_churn_scores_customer_id", "churn_scores", ["customer_id"])
    op.create_index("ix_churn_scores_scored_at", "churn_scores", ["scored_at"])

    op.create_table(
        "signal_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("score", sa.Numeric(5, 4), nullable=True),
        sa.Column("triggered_by", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Numeric(10, 2), nullable=True),
        sa.Column("attention_weights", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_signal_results_customer_id", "signal_results", ["customer_id"])
    op.create_index("ix_signal_results_created_at", "signal_results", ["created_at"])


def downgrade() -> None:
    op.drop_table("signal_results")
    op.drop_table("churn_scores")
