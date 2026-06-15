"""005_herald_layer5

Revision ID: 005_herald_layer5
Revises: 004_compass_layer4
Create Date: 2024-11-15 00:00:00

Adds:
  - content_store new columns: ab_variant_content, content_strategy, tone_modifiers, reason_codes_used
  - human_review_queue table (compliance failures awaiting human decision)
  - New Kafka topic: pcop.dispatched.v1 (documented here, created separately)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005_herald_layer5"
down_revision = "004_compass_layer4"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE content_store
            ADD COLUMN IF NOT EXISTS ab_variant_content TEXT,
            ADD COLUMN IF NOT EXISTS content_strategy VARCHAR(30),
            ADD COLUMN IF NOT EXISTS tone_modifiers TEXT[],
            ADD COLUMN IF NOT EXISTS reason_codes_used JSONB
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS human_review_queue (
            review_id        BIGSERIAL PRIMARY KEY,
            outreach_id      BIGINT REFERENCES outreach_log(outreach_id),
            customer_id      VARCHAR(20) NOT NULL,
            channel          VARCHAR(20),
            content_store_id BIGINT,
            compliance_notes TEXT,
            priority         INTEGER DEFAULT 3,
            status           VARCHAR(20) DEFAULT 'pending',
            reviewer_id      VARCHAR(50),
            reviewed_at      TIMESTAMPTZ,
            created_at       TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hrq_status
            ON human_review_queue(status, priority, created_at)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hrq_customer
            ON human_review_queue(customer_id)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prompt_versions (
            version_id       VARCHAR(50) PRIMARY KEY,
            channel          VARCHAR(20) NOT NULL,
            segment          VARCHAR(30) NOT NULL,
            risk_tier        VARCHAR(20) NOT NULL,
            system_prompt    TEXT,
            few_shot_examples JSONB DEFAULT '[]',
            tone_instructions TEXT,
            offer_instructions TEXT,
            is_active        BOOLEAN DEFAULT TRUE,
            created_at       TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prompt_performance (
            version_id       VARCHAR(50) PRIMARY KEY REFERENCES prompt_versions(version_id),
            conversion_rate  NUMERIC(5,4) DEFAULT 0.0,
            bandit_alpha     NUMERIC(10,4) DEFAULT 1.0,
            bandit_beta      NUMERIC(10,4) DEFAULT 1.0,
            updated_at       TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS device_tokens (
            token_id         BIGSERIAL PRIMARY KEY,
            customer_id      VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
            push_token       TEXT NOT NULL,
            platform         VARCHAR(10),
            is_active        BOOLEAN DEFAULT TRUE,
            updated_at       TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_tokens_customer
            ON device_tokens(customer_id, is_active)
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS device_tokens")
    op.execute("DROP TABLE IF EXISTS prompt_performance")
    op.execute("DROP TABLE IF EXISTS prompt_versions")
    op.execute("DROP INDEX IF EXISTS idx_hrq_customer")
    op.execute("DROP INDEX IF EXISTS idx_hrq_status")
    op.execute("DROP TABLE IF EXISTS human_review_queue")
    op.execute("ALTER TABLE content_store DROP COLUMN IF EXISTS ab_variant_content")
    op.execute("ALTER TABLE content_store DROP COLUMN IF EXISTS content_strategy")
    op.execute("ALTER TABLE content_store DROP COLUMN IF EXISTS tone_modifiers")
    op.execute("ALTER TABLE content_store DROP COLUMN IF EXISTS reason_codes_used")
