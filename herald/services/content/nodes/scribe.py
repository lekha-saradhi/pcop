import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import HeraldState
from ..prompts.channel_prompts import CHANNEL_PROMPTS
from ..clients.azure_foundry import get_scribe_llm

logger = logging.getLogger(__name__)


def _build_human_message(brief: dict) -> str:
    reason_codes_text = "\n".join([
        f"  - {rc['category']}: {rc['description']} "
        f"(importance: {rc['importance']:.2f}, source: {rc['source']})"
        for rc in brief.get("reason_codes", [])
    ])

    signals_text = "\n".join([
        f"  - {s['signal_type']}: confidence={s.get('confidence', 0):.2f}, "
        f"onset={s.get('onset_estimate', 'unknown')}\n"
        f"    Evidence: {'; '.join(s.get('evidence', [])[:2])}"
        for s in brief.get("active_signals", [])
        if s.get("detected")
    ])

    events_text = "\n".join([
        f"  - {e['event_type']} (confidence={e.get('confidence', 0):.2f}, "
        f"source={e.get('source', 'unknown')})\n"
        f"    Evidence: {'; '.join(e.get('evidence', [])[:2])}"
        for e in brief.get("confirmed_events", [])
    ]) or "  None confirmed"

    few_shot_text = ""
    for i, ex in enumerate(brief.get("few_shot_examples", [])[:3], 1):
        few_shot_text += f"\nExample {i} (conversion_rate={ex.get('conversion_rate', 'unknown')}):\n"
        if isinstance(ex.get("output"), dict):
            few_shot_text += json.dumps(ex["output"], indent=2)
        else:
            few_shot_text += str(ex.get("output", ""))

    prior_text = ""
    for msg in brief.get("prior_messages", []):
        dispatched_at = str(msg.get("dispatched_at", ""))[:10]
        content_preview = str(msg.get("subject_line") or msg.get("message", ""))[:100]
        prior_text += f"\n  [{msg.get('channel')} sent {dispatched_at}]: {content_preview}"
    if not prior_text:
        prior_text = "\n  None"

    return f"""
## Customer profile

Name: {brief['full_name']} ({brief['first_name']})
Segment: {brief['segment']}
Tenure: {brief['tenure_years']:.1f} years
Preferred channel: {brief['preferred_channel']}

## Risk and scoring (CHRONOS)

Risk tier: {brief['risk_tier']}
Churn score: {brief['final_score']:.3f}
Treatability score: {brief['treatability_score']:.3f}
Content strategy: {brief['content_strategy']}

## CHRONOS reason codes (PRISM)

{reason_codes_text or '  None available'}

## Confirmed life events (COMPASS)

{events_text}

Primary event: {brief.get('primary_event') or 'None'}

## ARGUS active signals

{signals_text or '  None active'}

## Tone modifiers

{', '.join(brief.get('tone_modifiers', ['professional']))}

## Offer details

Offer code: {brief.get('offer_code')}
Description: {brief.get('offer_description')}
Value: {brief.get('offer_value')}

## Tone and offer instructions

{brief.get('tone_instructions', '')}
{brief.get('offer_instructions', '')}

## Prior messages (DO NOT REPEAT)
{prior_text}

## Top-performing examples for this segment×channel×tier

{few_shot_text or '  No examples available yet'}

## Channel constraints

{json.dumps(brief.get('channel_constraints', {}), indent=2)}

## Your task

Generate content for channel: {brief['channel']}
Follow the output schema in your system prompt exactly.
"""


async def scribe_node(state: HeraldState) -> dict:
    brief = state["brief"]
    channel = state["channel"]

    logger.info(
        f"SCRIBE: Generating {channel} content for {state['customer_id']} "
        f"strategy={brief.get('content_strategy')} tone={brief.get('tone_modifiers')}"
    )

    llm = get_scribe_llm()
    system_prompt = CHANNEL_PROMPTS.get(channel, CHANNEL_PROMPTS["email"])

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=_build_human_message(brief)),
    ]

    response = await llm.ainvoke(messages)
    raw_content = response.content

    try:
        content = json.loads(raw_content)
    except json.JSONDecodeError:
        cleaned = raw_content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        content = json.loads(cleaned.strip())

    ab_variant = content.pop("ab_variant", None)

    logger.info(
        f"SCRIBE: Generated {channel} content for {state['customer_id']} "
        f"ab_variant={'yes' if ab_variant else 'no'}"
    )

    return {
        "generated_content": content,
        "ab_variant": ab_variant,
    }
