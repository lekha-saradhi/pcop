"""Add expires_at column to signal_results.

Revision ID: 003
Revises: 002
Create Date: 2026-05-12
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "signal_results",
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_signal_results_expires_at", "signal_results", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_signal_results_expires_at", "signal_results")
    op.drop_column("signal_results", "expires_at")
