import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from ..state import CompassState
from ..clients.azure_foundry import get_langchain_compass_llm
from ..prompts.compass_system import COMPASS_SYSTEM_PROMPT
from ..tools.db_reads import (
    get_offer_eligibility_tool,
    get_channel_history_tool,
    get_rm_availability_tool,
    get_consent_flags_tool,
    get_life_events_tool,
)
from ..tools.db_writes import write_action_plan_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3


async def compass_nba_node(state: CompassState) -> dict:
    customer_id = state["customer_id"]
    logger.info(f"COMPASS: Starting NBA selection for customer {customer_id}")

    if (
        state.get("risk_tier") in ["watch", "low"]
        and not state.get("final_events")
        and state.get("alarm_severity") not in ["CRITICAL", "HIGH"]
    ):
        logger.info(f"COMPASS: Generating monitor plan for {customer_id} (low risk, no events)")
        return {
            "action_plan": {
                "channel": None,
                "offer_code": None,
                "timing": None,
                "owner_id": "system",
                "priority": 5,
                "rationale": "Customer at watch/low tier with no confirmed life events. Monitor only.",
                "suppressed": False,
            }
        }

    llm = get_langchain_compass_llm()

    tools = [
        get_offer_eligibility_tool,
        get_channel_history_tool,
        get_rm_availability_tool,
        get_consent_flags_tool,
        get_life_events_tool,
        write_action_plan_tool,
    ]

    llm_with_tools = llm.bind_tools(tools)

    events_summary = _format_events_summary(state.get("final_events", []))

    human_message = HumanMessage(content=f"""
Customer ID: {customer_id}
As-of date: {state['as_of_date']}
Risk tier: {state.get('risk_tier', 'unknown')}
Churn score: {(state.get('final_score') or 0.0):.3f}
Action score: {(state.get('action_score') or 0.0):.3f}
Risk adjustment applied: {(state.get('risk_adjustment') or 0.0):+.2f}

## Confirmed life events

{events_summary}

## Your task

1. Call get_offer_eligibility to see what offers this customer can receive
2. Call get_channel_history to check recent outreach
3. Call get_consent_flags to check opt-outs
4. If considering rm_visit or call: call get_rm_availability
5. Select the best channel and offer, then call write_action_plan
""")

    messages = [
        SystemMessage(content=COMPASS_SYSTEM_PROMPT),
        human_message,
    ]

    action_plan = None
    tool_call_count = 0

    for round_num in range(MAX_TOOL_ROUNDS):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tool_call in response.tool_calls:
            tool_call_count += 1
            tool_name = tool_call["name"]
            tool_args = {**tool_call["args"], "customer_id": customer_id}

            tool_map = {t.name: t for t in tools}
            try:
                result = await tool_map[tool_name].ainvoke(tool_args)
            except Exception as e:
                result = {"error": str(e)}

            if tool_name == "write_action_plan_tool" and result.get("success"):
                action_plan = result["action_plan"]
                logger.info(
                    f"COMPASS: Action plan written for {customer_id}: "
                    f"channel={action_plan.get('channel')} "
                    f"offer={action_plan.get('offer_code')}"
                )

            messages.append(ToolMessage(
                content=json.dumps(result, default=str),
                tool_call_id=tool_call["id"],
            ))

    if action_plan is None:
        logger.warning(
            f"COMPASS: No action plan written for {customer_id} "
            f"after {tool_call_count} tool calls. Using fallback."
        )
        action_plan = _fallback_action_plan(state)

    return {"action_plan": action_plan}


def _format_events_summary(events: list) -> str:
    if not events:
        return "No life events confirmed."
    lines = []
    for e in events:
        lines.append(
            f"- {e['event_type']} (confidence={e['confidence']:.2f}, "
            f"source={e['source']})"
        )
    return "\n".join(lines)


def _fallback_action_plan(state: CompassState) -> dict:
    tier_defaults = {
        "critical": {"channel": "call", "priority": 1},
        "high": {"channel": "email", "priority": 2},
        "medium": {"channel": "email", "priority": 3},
        "watch": {"channel": None, "priority": 5},
        "low": {"channel": None, "priority": 5},
    }
    tier = state.get("risk_tier", "watch")
    defaults = tier_defaults.get(tier, {"channel": None, "priority": 5})

    return {
        "channel": defaults["channel"],
        "offer_code": "RETENTION_STANDARD",
        "timing": state["as_of_date"],
        "owner_id": "system",
        "priority": defaults["priority"],
        "rationale": f"Fallback plan for {tier} tier customer.",
        "suppressed": False,
    }
