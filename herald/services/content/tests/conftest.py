import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_brief(
    customer_id="C-00000001",
    channel="email",
    segment="Mass Affluent",
    risk_tier="high",
    final_score=0.78,
    treatability_score=0.65,
    content_strategy="full_retention",
    tone_modifiers=None,
    confirmed_events=None,
    active_signals=None,
    reason_codes=None,
    offer_code="MA_RATE_UPGRADE",
):
    return {
        "customer_id": customer_id,
        "full_name": "Priya Sharma",
        "first_name": "Priya",
        "segment": segment,
        "tenure_years": 4.5,
        "preferred_channel": channel,
        "channel": channel,
        "offer_code": offer_code,
        "offer_description": "Preferential savings rate upgrade",
        "offer_value": "0.5% additional p.a.",
        "action_rationale": "Job change + relocation detected",
        "risk_tier": risk_tier,
        "final_score": final_score,
        "treatability_score": treatability_score,
        "content_strategy": content_strategy,
        "reason_codes": reason_codes or [],
        "confirmed_events": confirmed_events or [],
        "primary_event": (confirmed_events or [{"event_type": None}])[0].get("event_type"),
        "active_signals": active_signals or [],
        "tone_modifiers": tone_modifiers or ["professional"],
        "channel_constraints": {},
        "system_prompt": "",
        "few_shot_examples": [],
        "tone_instructions": "",
        "offer_instructions": "",
        "prompt_version_id": "default",
        "prior_messages": [],
    }


def make_state(
    customer_id="C-00000001",
    channel="email",
    brief=None,
    generated_content=None,
    compliance_status=None,
    human_review_required=False,
    dispatched=False,
    retry_count=0,
    action_plan_event=None,
):
    if action_plan_event is None:
        action_plan_event = {
            "customer_id": customer_id,
            "outreach_id": 999,
            "risk_tier": "high",
            "final_score": 0.78,
            "final_events": [],
            "action_plan": {
                "channel": channel,
                "offer_code": "MA_RATE_UPGRADE",
                "timing": "2024-11-02T09:00:00",
                "owner_id": "system",
                "priority": 2,
                "rationale": "Test rationale",
            },
        }
    return {
        "action_plan_event": action_plan_event,
        "customer_id": customer_id,
        "channel": channel,
        "brief": brief or make_brief(customer_id=customer_id, channel=channel),
        "generated_content": generated_content,
        "ab_variant": None,
        "compliance_status": compliance_status,
        "compliance_notes": None,
        "retry_count": retry_count,
        "dispatched": dispatched,
        "dispatch_provider_id": None,
        "content_store_id": None,
        "human_review_required": human_review_required,
    }
