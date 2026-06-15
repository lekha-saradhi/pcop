from typing import TypedDict, Optional


class SignalResult(TypedDict):
    signal_type: str
    detected: bool
    confidence: float
    evidence: list[str]
    cusum_value: Optional[float]
    alarm_threshold: Optional[float]
    onset_estimate: Optional[str]
    direction: Optional[str]
    expires_at: Optional[str]


class LifeEvent(TypedDict):
    event_type: str
    confidence: float
    evidence: list[str]
    source: str
    risk_adjustment: float


class ActionPlan(TypedDict):
    channel: Optional[str]
    offer_code: Optional[str]
    timing: Optional[str]
    owner_id: str
    priority: int
    rationale: str
    suppressed: bool


class CompassState(TypedDict):
    # Populated by Kafka consumer before graph invocation
    customer_id: str
    as_of_date: str
    alarm_severity: str
    alarm_timestamp: str
    signal_results: list[SignalResult]

    # Populated by INTAKE node
    risk_tier: Optional[str]
    final_score: Optional[float]
    action_score: Optional[float]

    # Populated by COGNITION or VERIFY
    confirmed_events: list[LifeEvent]
    llm_inferred_events: list[LifeEvent]

    # Populated by MERGE
    final_events: list[LifeEvent]
    risk_adjustment: float

    # Populated by COMPASS NBA
    action_plan: Optional[ActionPlan]

    # Populated by GATE
    gate_decision: Optional[str]
    gate_reason: Optional[str]

    # Populated by DISPATCH
    dispatch_timestamp: Optional[str]
    outreach_id: Optional[int]
