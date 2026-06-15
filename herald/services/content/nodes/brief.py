import asyncio
import logging
from ..state import HeraldState, GenerationBrief
from ..db.reads import (
    get_customer_profile,
    get_churn_score_with_reasons,
    get_signal_results,
    get_offer_details,
    get_best_prompt_version,
    get_prior_outreach,
    get_account_summary,
)
from ..tone import derive_tone_modifiers, derive_content_strategy

logger = logging.getLogger(__name__)

CHANNEL_CONSTRAINTS = {
    "email": {
        "max_words": 250,
        "format": "subject_line + html_body",
        "required_elements": ["legal_footer", "unsubscribe_link", "personalised_greeting"],
        "prohibited": ["links_without_text", "all_caps_subject"],
        "ab_variant": True,
    },
    "sms": {
        "max_chars": 160,
        "format": "plain_text",
        "required_elements": ["stop_instruction"],
        "prohibited": ["links_unless_shortened", "special_characters"],
        "ab_variant": False,
    },
    "app": {
        "title_max_chars": 50,
        "body_max_chars": 120,
        "format": "push_title + card_body + cta_label",
        "required_elements": ["cta_button"],
        "ab_variant": False,
    },
    "call": {
        "format": "json_script",
        "required_elements": ["opening_30s", "three_talking_points", "two_objection_handlers", "close"],
        "duration_target_seconds": 180,
        "ab_variant": False,
    },
    "rm_visit": {
        "format": "briefing_document",
        "sections": [
            "customer_summary", "event_context", "signal_evidence",
            "pre_approved_offer", "conversation_agenda", "objection_guide",
        ],
        "max_words_per_section": 150,
        "ab_variant": False,
    },
}


async def brief_node(state: HeraldState) -> dict:
    event = state["action_plan_event"]
    customer_id = state["customer_id"]
    channel = state["channel"]
    action_plan = event.get("action_plan", {})

    logger.info(f"BRIEF: Assembling for {customer_id} channel={channel}")

    (
        customer,
        score_data,
        signals,
        prior_outreach,
        account_summary,
    ) = await asyncio.gather(
        get_customer_profile(customer_id),
        get_churn_score_with_reasons(customer_id),
        get_signal_results(customer_id),
        get_prior_outreach(customer_id, limit=2),
        get_account_summary(customer_id),
    )

    segment = customer.get("segment", "Mass Market")
    risk_tier = event.get("risk_tier") or score_data.get("risk_tier", "medium")

    prompt_data = await get_best_prompt_version(
        channel=channel,
        segment=segment,
        risk_tier=risk_tier,
    )

    offer_details = await get_offer_details(action_plan.get("offer_code"))

    treatability = score_data.get("treatability_score") or 0.5
    final_score = score_data.get("final_score") or 0.5
    content_strategy = derive_content_strategy(
        treatability=treatability,
        final_score=final_score,
        risk_tier=risk_tier,
    )

    tone_modifiers = derive_tone_modifiers(signals)

    confirmed_events = event.get("final_events", [])
    primary_event = (
        max(confirmed_events, key=lambda e: e.get("confidence") or 0)["event_type"]
        if confirmed_events else None
    )

    full_name = customer.get("full_name", "Valued Customer")
    first_name = full_name.split()[0] if full_name else "Customer"

    brief: GenerationBrief = {
        "customer_id": customer_id,
        "full_name": full_name,
        "first_name": first_name,
        "segment": segment,
        "tenure_years": customer.get("tenure_years", 0),
        "preferred_channel": customer.get("preferred_channel", channel),
        "channel": channel,
        "offer_code": action_plan.get("offer_code"),
        "offer_description": offer_details.get("description", ""),
        "offer_value": offer_details.get("value", ""),
        "action_rationale": action_plan.get("rationale", ""),
        "risk_tier": risk_tier,
        "final_score": final_score,
        "treatability_score": treatability,
        "content_strategy": content_strategy,
        "reason_codes": score_data.get("reason_codes_v2", []),
        "confirmed_events": confirmed_events,
        "primary_event": primary_event,
        "active_signals": signals,
        "tone_modifiers": tone_modifiers,
        "channel_constraints": CHANNEL_CONSTRAINTS.get(channel, {}),
        "system_prompt": prompt_data.get("system_prompt", ""),
        "few_shot_examples": prompt_data.get("few_shot_examples", []),
        "tone_instructions": prompt_data.get("tone_instructions", ""),
        "offer_instructions": prompt_data.get("offer_instructions", ""),
        "prompt_version_id": prompt_data.get("version_id", "default"),
        "prior_messages": prior_outreach,
    }

    logger.info(
        f"BRIEF: Assembled for {customer_id} — "
        f"strategy={content_strategy} tone={tone_modifiers} "
        f"primary_event={primary_event} prompt_version={prompt_data.get('version_id')}"
    )

    return {"brief": brief}
