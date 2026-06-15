from typing import TypedDict, Optional


class GenerationBrief(TypedDict):
    # Customer identity (from customers table)
    customer_id: str
    full_name: str
    first_name: str
    segment: str
    tenure_years: float
    preferred_channel: str

    # Action context (from COMPASS pcop.action_plans.v1)
    channel: str
    offer_code: Optional[str]
    offer_description: str
    offer_value: str
    action_rationale: str

    # Risk context (from CHRONOS churn_scores)
    risk_tier: str
    final_score: float
    treatability_score: float
    content_strategy: str
    reason_codes: list

    # Life events (from COMPASS final_events)
    confirmed_events: list
    primary_event: Optional[str]

    # Signal context (from ARGUS signal_results)
    active_signals: list
    tone_modifiers: list

    # Channel constraints
    channel_constraints: dict

    # Prompt bank (from prompt_versions + prompt_performance)
    system_prompt: str
    few_shot_examples: list
    tone_instructions: str
    offer_instructions: str
    prompt_version_id: str

    # Prior outreach (from outreach_log + content_store)
    prior_messages: list


class HeraldState(TypedDict):
    action_plan_event: dict
    customer_id: str
    channel: str
    brief: Optional[GenerationBrief]
    generated_content: Optional[dict]
    ab_variant: Optional[dict]
    compliance_status: Optional[str]
    compliance_notes: Optional[str]
    retry_count: int
    dispatched: bool
    dispatch_provider_id: Optional[str]
    content_store_id: Optional[int]
    human_review_required: bool
