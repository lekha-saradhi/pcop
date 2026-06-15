"""006_verdict_oracle

Revision ID: 006_verdict_oracle
Revises: 005_herald_layer5
Create Date: 2024-11-15 00:00:00

Adds:
  - interaction_events table (COLLECT node writes)
  - outcomes table extensions (OBSERVE node)
  - uplift_results table extensions (ATTRIBUTE DR columns)
  - holdout_registry table (HOLDOUT node)
  - model_calibration_signals table (ATTRIBUTE → Layer 7 RETRAIN)
  - channel_policy table (Layer 7 ROUTE)
  - insight_cards table (Layer 7 NARRATE)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006_verdict_oracle"
down_revision = "005_herald_layer5"
branch_labels = None
depends_on = None


def upgrade():
    # Interaction events (COLLECT)
    op.execute("""
        CREATE TABLE IF NOT EXISTS interaction_events (
            id               BIGSERIAL PRIMARY KEY,
            event_id         VARCHAR(64) UNIQUE NOT NULL,
            outreach_id      BIGINT REFERENCES outreach_log(outreach_id),
            customer_id      VARCHAR(20) NOT NULL,
            channel          VARCHAR(20),
            event_type       VARCHAR(30),
            event_timestamp  TIMESTAMPTZ,
            duration_seconds INTEGER,
            outcome          VARCHAR(50),
            link_url         TEXT,
            variant          VARCHAR(2),
            content_store_id BIGINT,
            prompt_version_id VARCHAR(50),
            content_strategy VARCHAR(30),
            ab_variant       TEXT,
            life_events_at_send TEXT[],
            risk_tier_at_send VARCHAR(20),
            final_score_at_send NUMERIC(5,4),
            treatability_score_at_send NUMERIC(5,4),
            created_at       TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ie_outreach
            ON interaction_events(outreach_id, event_type)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ie_customer_channel
            ON interaction_events(customer_id, channel, event_timestamp)
    """)

    # Outcomes table (OBSERVE)
    op.execute("""
        CREATE TABLE IF NOT EXISTS outcomes (
            outcome_id       BIGSERIAL PRIMARY KEY,
            outreach_id      BIGINT REFERENCES outreach_log(outreach_id),
            customer_id      VARCHAR(20) NOT NULL,
            holdout_group    BOOLEAN DEFAULT FALSE,
            observation_window INTEGER NOT NULL,
            outcome_label    VARCHAR(20),
            txn_volume_change NUMERIC(8,2),
            engagement_change NUMERIC(8,4),
            balance_change   NUMERIC(14,2),
            products_closed  INTEGER DEFAULT 0,
            churn_score_at_measure NUMERIC(5,4),
            score_reduction  NUMERIC(5,4),
            signals_cleared  BOOLEAN,
            signals_still_active TEXT[],
            tempo_baseline_recovered BOOLEAN,
            content_strategy VARCHAR(30),
            prompt_version_id VARCHAR(50),
            treatability_score_at_send NUMERIC(5,4),
            active_signal_count INTEGER,
            measured_at      TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(outreach_id, observation_window)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_outcomes_customer
            ON outcomes(customer_id, observation_window)
    """)

    # Uplift results (ATTRIBUTE) — create or extend
    op.execute("""
        CREATE TABLE IF NOT EXISTS uplift_results (
            result_id        BIGSERIAL PRIMARY KEY,
            campaign_id      VARCHAR(50),
            channel          VARCHAR(20),
            segment          VARCHAR(30),
            risk_tier        VARCHAR(20),
            observation_window INTEGER,
            treatment_n      INTEGER,
            holdout_n        INTEGER,
            treatment_retention_rate NUMERIC(5,4),
            holdout_retention_rate   NUMERIC(5,4),
            naive_uplift     NUMERIC(6,4),
            dr_uplift        NUMERIC(6,4),
            dr_uplift_se     NUMERIC(6,4),
            overestimation_bias NUMERIC(6,4),
            ate_high_treatability NUMERIC(6,4),
            ate_low_treatability  NUMERIC(6,4),
            psm_adjusted     BOOLEAN DEFAULT FALSE,
            estimator        VARCHAR(30) DEFAULT 'DR-Learner',
            content_strategy VARCHAR(30),
            prompt_version_id VARCHAR(50),
            calculated_at    TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Holdout registry (HOLDOUT)
    op.execute("""
        CREATE TABLE IF NOT EXISTS holdout_registry (
            registry_id      BIGSERIAL PRIMARY KEY,
            customer_id      VARCHAR(20) NOT NULL,
            campaign_id      VARCHAR(50) NOT NULL,
            risk_tier_at_entry VARCHAR(20),
            risk_score_at_entry NUMERIC(5,4),
            entered_holdout_at TIMESTAMPTZ DEFAULT NOW(),
            exited_holdout_at  TIMESTAMPTZ,
            exit_reason        VARCHAR(30),
            UNIQUE(customer_id, campaign_id)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_holdout_active
            ON holdout_registry(exited_holdout_at, customer_id)
            WHERE exited_holdout_at IS NULL
    """)

    # Model calibration signals (ATTRIBUTE → Layer 7 RETRAIN)
    op.execute("""
        CREATE TABLE IF NOT EXISTS model_calibration_signals (
            signal_id       BIGSERIAL PRIMARY KEY,
            model_name      VARCHAR(50),
            channel         VARCHAR(20),
            segment         VARCHAR(30),
            calibration_ok  BOOLEAN,
            ate_high        NUMERIC(6,4),
            ate_low         NUMERIC(6,4),
            n_samples       INTEGER,
            measured_at     TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Channel policy table (Layer 7 ROUTE)
    op.execute("""
        CREATE TABLE IF NOT EXISTS channel_policy (
            policy_id          BIGSERIAL PRIMARY KEY,
            segment            VARCHAR(30) NOT NULL,
            life_event_type    VARCHAR(50),
            risk_tier          VARCHAR(20) NOT NULL,
            content_strategy   VARCHAR(30),
            primary_signal_type VARCHAR(50),
            channel            VARCHAR(20) NOT NULL,
            bandit_alpha       NUMERIC(10,4) DEFAULT 1.0,
            bandit_beta        NUMERIC(10,4) DEFAULT 1.0,
            updated_at         TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(segment, risk_tier, channel, content_strategy, primary_signal_type)
        )
    """)

    # Insight cards (Layer 7 NARRATE)
    op.execute("""
        CREATE TABLE IF NOT EXISTS insight_cards (
            card_id         BIGSERIAL PRIMARY KEY,
            generated_date  DATE NOT NULL,
            severity        VARCHAR(20),
            title           TEXT,
            what            TEXT,
            why             TEXT,
            where_affected  TEXT,
            recommend       TEXT,
            metric_name     VARCHAR(100),
            metric_delta    VARCHAR(50),
            affected_customers INTEGER,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_insight_cards_date
            ON insight_cards(generated_date DESC, severity)
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_insight_cards_date")
    op.execute("DROP TABLE IF EXISTS insight_cards")
    op.execute("DROP TABLE IF EXISTS channel_policy")
    op.execute("DROP TABLE IF EXISTS model_calibration_signals")
    op.execute("DROP INDEX IF EXISTS idx_holdout_active")
    op.execute("DROP TABLE IF EXISTS holdout_registry")
    op.execute("DROP TABLE IF EXISTS uplift_results")
    op.execute("DROP INDEX IF EXISTS idx_outcomes_customer")
    op.execute("DROP TABLE IF EXISTS outcomes")
    op.execute("DROP INDEX IF EXISTS idx_ie_customer_channel")
    op.execute("DROP INDEX IF EXISTS idx_ie_outreach")
    op.execute("DROP TABLE IF EXISTS interaction_events")
