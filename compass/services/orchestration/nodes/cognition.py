import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from ..state import CompassState
from ..clients.azure_foundry import get_langchain_cognition_llm
from ..prompts.cognition_system import COGNITION_SYSTEM_PROMPT
from ..tools.db_reads import (
    get_signal_results_tool,
    get_crm_notes_tool,
    get_transactions_tool,
    get_kyc_updates_tool,
    get_account_events_tool,
    get_enrichment_tool,
)
from ..tools.db_writes import write_life_event_tool, adjust_risk_score_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


async def cognition_node(state: CompassState) -> dict:
    customer_id = state["customer_id"]
    logger.info(f"COGNITION: Starting inference for customer {customer_id}")

    llm = get_langchain_cognition_llm()

    read_tools = [
        get_signal_results_tool,
        get_crm_notes_tool,
        get_transactions_tool,
        get_kyc_updates_tool,
        get_account_events_tool,
        get_enrichment_tool,
    ]
    write_tools = [write_life_event_tool, adjust_risk_score_tool]
    all_tools = read_tools + write_tools

    llm_with_tools = llm.bind_tools(all_tools)

    signal_summary = _format_signal_summary(state["signal_results"])
    human_message = HumanMessage(content=f"""
Customer ID: {customer_id}
As-of date: {state['as_of_date']}
Risk tier: {state.get('risk_tier', 'unknown')}
Churn score: {(state.get('final_score') or 0.0):.3f}

## ARGUS signals detected

{signal_summary}

## Your task

Analyse these signals and determine which life events are occurring.
Use the available tools to gather evidence.
Confirm events by calling write_life_event for each one with confidence >= 0.60.
""")

    messages = [
        SystemMessage(content=COGNITION_SYSTEM_PROMPT),
        human_message,
    ]

    inferred_events = []
    tool_call_count = 0

    for round_num in range(MAX_TOOL_ROUNDS):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            logger.info(
                f"COGNITION: Agent completed after {round_num + 1} rounds, "
                f"{tool_call_count} tool calls, "
                f"{len(inferred_events)} events inferred"
            )
            break

        for tool_call in response.tool_calls:
            tool_call_count += 1
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            logger.debug(f"COGNITION: Tool call {tool_call_count} - {tool_name}({tool_args})")

            tool_result = await _execute_tool(tool_name, tool_args, customer_id, all_tools)

            if tool_name == "write_life_event_tool" and tool_result.get("success"):
                inferred_events.append(tool_result["event"])

            messages.append(ToolMessage(
                content=json.dumps(tool_result, default=str),
                tool_call_id=tool_call["id"],
            ))
    else:
        logger.warning(
            f"COGNITION: Reached MAX_TOOL_ROUNDS={MAX_TOOL_ROUNDS} "
            f"for customer {customer_id}"
        )

    return {"llm_inferred_events": inferred_events}


def _format_signal_summary(signal_results: list) -> str:
    detected = [s for s in signal_results if s.get("detected")]
    if not detected:
        return "No signals detected."

    lines = []
    for s in detected:
        lines.append(
            f"- {s['signal_type']}: confidence={s['confidence']:.2f}, "
            f"direction={s.get('direction', 'n/a')}, "
            f"onset={s.get('onset_estimate', 'unknown')}\n"
            f"  Evidence: {'; '.join(s.get('evidence', [])[:2])}"
        )
    return "\n".join(lines)


async def _execute_tool(
    tool_name: str, tool_args: dict, customer_id: str, all_tools: list
) -> dict:
    tool_args["customer_id"] = customer_id

    tool_map = {t.name: t for t in all_tools}
    if tool_name not in tool_map:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        result = await tool_map[tool_name].ainvoke(tool_args)
        return result
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"error": str(e), "tool": tool_name}


def _should_use_full_cognition(state: CompassState) -> bool:
    signals = state.get("signal_results", [])
    ambiguous = [
        s for s in signals if 0.40 <= s.get("confidence", 0) < 0.80 and s["detected"]
    ]
    tier = state.get("risk_tier", "watch")
    severity = state.get("alarm_severity", "LOW")

    if not ambiguous:
        return False
    if tier in ["watch", "low"] and severity not in ["CRITICAL", "HIGH"]:
        return False
    return True
