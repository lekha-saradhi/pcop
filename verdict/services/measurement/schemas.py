from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InteractionEvent(BaseModel):
    """
    Canonical interaction event schema.
    Published to pcop.interactions.v1 by all channel webhooks.
    """
    event_id: str
    outreach_id: int
    customer_id: str
    channel: str
    event_type: str
    event_timestamp: datetime

    # Channel-specific fields (nullable for irrelevant channels)
    duration_seconds: Optional[int] = None     # Call answered
    outcome: Optional[str] = None              # RM visit outcome
    link_url: Optional[str] = None             # Which link was clicked
    variant: Optional[str] = None             # A or B (email A/B)

    # Attribution fields (populated by COLLECT)
    content_store_id: Optional[int] = None
    prompt_version_id: Optional[str] = None
    content_strategy: Optional[str] = None
    ab_variant: Optional[str] = None
    life_events_at_send: Optional[list[str]] = None
    risk_tier_at_send: Optional[str] = None
    final_score_at_send: Optional[float] = None
    treatability_score_at_send: Optional[float] = None


class OutcomeRecord(BaseModel):
    """
    Measured behavioural outcome for one customer at one observation window.
    Written by OBSERVE to the outcomes table.
    """
    customer_id: str
    outreach_id: int
    holdout_group: bool
    observation_window: int                    # 1, 7, or 30 days
    outcome_label: str                         # retained | churned | partial | unresponsive
    txn_volume_change: float                   # % change vs pre-alarm TEMPO baseline
    engagement_change: float
    balance_change: float
    products_closed: int
    churn_score_at_measure: Optional[float]
    score_reduction: float                     # Positive = score fell = good
    signals_cleared: bool
    active_signal_count: int
    measured_at: str


class UpliftResult(BaseModel):
    """
    DR-Learner uplift estimate for one (campaign × channel × segment × tier) slice.
    Written by ATTRIBUTE to the uplift_results table.
    """
    campaign_id: str
    channel: str
    segment: str
    risk_tier: str
    observation_window: int
    treatment_n: int
    holdout_n: int
    treatment_retention_rate: float
    holdout_retention_rate: float
    naive_uplift: float
    dr_uplift: float
    dr_uplift_se: float
    overestimation_bias: float
    ate_high_treatability: Optional[float]
    ate_low_treatability: Optional[float]
    estimator: str = "DR-Learner"
    content_strategy: Optional[str] = None
    prompt_version_id: Optional[str] = None
    calculated_at: str
