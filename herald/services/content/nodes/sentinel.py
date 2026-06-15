import re
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import HeraldState
from ..clients.azure_foundry import get_scribe_llm
from ..prompts.prohibited_phrases import PROHIBITED_PHRASES, PROHIBITED_PATTERNS

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

COMPLIANCE_CRITIQUE_PROMPT = """
You are a banking compliance reviewer.

Review the following message content. Would a banking regulator flag any claim as:
- Misleading (false or unsubstantiated)
- Pressuring (urgency that could mislead)
- Non-compliant (violates banking advertising standards)
- Discriminatory or sensitive (inappropriate for the customer's situation)

Respond ONLY with valid JSON:
{
  "verdict": "PASS" or "FAIL",
  "reason": "string (if FAIL: specific violation. If PASS: 'No compliance issues detected.')",
  "fix_hint": "string (if FAIL: specific change needed. If PASS: null)"
}
"""


async def sentinel_node(state: HeraldState) -> dict:
    customer_id = state["customer_id"]
    channel = state["channel"]
    content = state["generated_content"]
    retry_count = state.get("retry_count", 0)

    logger.info(
        f"SENTINEL: Checking {channel} content for {customer_id} "
        f"(attempt {retry_count + 1}/{MAX_RETRIES + 1})"
    )

    content_str = _content_to_string(content, channel)

    pass1_result = _regex_check(content_str)
    if not pass1_result["passed"]:
        logger.warning(f"SENTINEL: Regex FAIL for {customer_id} — {pass1_result['violation']}")
        if retry_count < MAX_RETRIES:
            return await _retry_scribe(state, pass1_result["violation"])
        else:
            return _human_review(state, f"Regex: {pass1_result['violation']}")

    pass2_result = await _llm_check(content_str, state["brief"])
    if pass2_result["verdict"] == "FAIL":
        logger.warning(f"SENTINEL: LLM FAIL for {customer_id} — {pass2_result['reason']}")
        if retry_count < MAX_RETRIES:
            return await _retry_scribe(state, pass2_result["fix_hint"])
        else:
            return _human_review(state, f"LLM: {pass2_result['reason']}")

    logger.info(f"SENTINEL: PASS for {customer_id}")
    return {
        "compliance_status": "passed",
        "compliance_notes": "No compliance issues detected.",
        "human_review_required": False,
    }


def _content_to_string(content: dict, channel: str) -> str:
    if channel == "email":
        return (
            f"{content.get('subject_line', '')} "
            f"{content.get('body_html', '')} "
            f"{content.get('cta_text', '')}"
        )
    elif channel == "sms":
        return content.get("message", "")
    elif channel == "app":
        return (
            f"{content.get('title', '')} "
            f"{content.get('card_body', '')} "
            f"{content.get('cta_label', '')}"
        )
    elif channel in ("call", "rm_visit"):
        return json.dumps(content)
    return str(content)


def _regex_check(content_str: str) -> dict:
    content_lower = content_str.lower()

    for phrase in PROHIBITED_PHRASES:
        if phrase.lower() in content_lower:
            return {"passed": False, "violation": f"Prohibited phrase detected: '{phrase}'"}

    for pattern, description in PROHIBITED_PATTERNS:
        if re.search(pattern, content_str, re.IGNORECASE):
            return {"passed": False, "violation": f"Prohibited pattern: {description}"}

    return {"passed": True, "violation": None}


async def _llm_check(content_str: str, brief: dict) -> dict:
    llm = get_scribe_llm()

    stress_active = "cfsi_stress" in [
        s["signal_type"] for s in brief.get("active_signals", [])
    ]

    context = f"""
Content to review:
{content_str}

Customer context:
- Segment: {brief.get('segment')}
- Active tone modifiers: {', '.join(brief.get('tone_modifiers', []))}
- Primary life event: {brief.get('primary_event') or 'None'}
- Financial stress signal active: {'yes' if stress_active else 'no'}
"""

    messages = [
        SystemMessage(content=COMPLIANCE_CRITIQUE_PROMPT),
        HumanMessage(content=context),
    ]

    response = await llm.ainvoke(messages)
    try:
        return json.loads(response.content)
    except Exception:
        return {"verdict": "PASS", "reason": "Parse error — defaulting to PASS", "fix_hint": None}


async def _retry_scribe(state: HeraldState, fix_hint: str) -> dict:
    from .scribe import scribe_node

    logger.info(f"SENTINEL: Retrying SCRIBE for {state['customer_id']} with hint: {fix_hint}")

    updated_brief = {
        **state["brief"],
        "compliance_fix_hint": fix_hint,
        "tone_instructions": (
            state["brief"].get("tone_instructions", "")
            + f"\n\nIMPORTANT FIX REQUIRED: {fix_hint}"
        ),
    }
    updated_state = {
        **state,
        "brief": updated_brief,
        "retry_count": state.get("retry_count", 0) + 1,
    }

    scribe_result = await scribe_node(updated_state)
    sentinel_input = {**updated_state, **scribe_result}
    return await sentinel_node(sentinel_input)


def _human_review(state: HeraldState, reason: str) -> dict:
    logger.warning(f"SENTINEL: Routing {state['customer_id']} to human review — {reason}")
    return {
        "compliance_status": "human_review",
        "compliance_notes": reason,
        "human_review_required": True,
    }
