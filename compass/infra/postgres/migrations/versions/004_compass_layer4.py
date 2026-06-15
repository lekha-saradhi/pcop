"""004_compass_layer4

Revision ID: 004_compass_layer4
Revises: 003_chronos_layer3
Create Date: 2024-11-01 00:00:00

Adds:
  - action_plans table (written by COMPASS, read by DISPATCH)
  - life_events.risk_adjustment column (if missing)
  - life_events.source column (if missing)
  - outreach_log.life_events column (if missing)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_compass_layer4"
down_revision = "003_chronos_layer3"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS action_plans (
            plan_id         BIGSERIAL PRIMARY KEY,
            customer_id     VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
            channel         VARCHAR(20),
            offer_code      VARCHAR(50),
            timing          TIMESTAMPTZ,
            owner_id        VARCHAR(20),
            priority        INTEGER DEFAULT 3,
            rationale       TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_action_plans_customer
            ON action_plans(customer_id, created_at DESC)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_action_plans_channel
            ON action_plans(channel, created_at DESC)
    """)

    op.execute("""
        ALTER TABLE outreach_log
            ADD COLUMN IF NOT EXISTS life_events TEXT[]
    """)

    op.execute("""
        ALTER TABLE life_events
            ADD COLUMN IF NOT EXISTS risk_adjustment NUMERIC(5,3) DEFAULT 0.0
    """)

    op.execute("""
        ALTER TABLE life_events
            ADD COLUMN IF NOT EXISTS source VARCHAR(30) DEFAULT 'rule_verify'
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS action_plans")
    op.execute("ALTER TABLE outreach_log DROP COLUMN IF EXISTS life_events")
    op.execute("ALTER TABLE life_events DROP COLUMN IF EXISTS risk_adjustment")
    op.execute("ALTER TABLE life_events DROP COLUMN IF EXISTS source")
