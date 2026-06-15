import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _base_state():
    return {
        "customer_id": "C-00000001",
        "as_of_date": "2024-11-01",
        "alarm_severity": "HIGH",
        "alarm_timestamp": "2024-11-01T06:00:00Z",
        "signal_results": [
            {"signal_type": "cusum_salary", "detected": True, "confidence": 0.72,
             "evidence": ["Employer ref changed"], "direction": "increase",
             "onset_estimate": "2024-09-01"},
        ],
        "risk_tier": "high",
        "final_score": 0.75,
        "action_score": 0.45,
        "confirmed_events": [],
        "llm_inferred_events": [],
        "final_events": [],
        "risk_adjustment": 0.0,
        "action_plan": None,
        "gate_decision": None,
        "gate_reason": None,
        "dispatch_timestamp": None,
        "outreach_id": None,
    }


@pytest.mark.asyncio
async def test_cognition_returns_empty_on_no_tool_calls():
    """LLM that returns no tool calls should produce empty inferred_events."""
    from ..nodes.cognition import cognition_node

    mock_response = MagicMock()
    mock_response.tool_calls = []

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("services.orchestration.nodes.cognition.get_langchain_cognition_llm",
               return_value=mock_llm):
        result = await cognition_node(_base_state())

    assert result["llm_inferred_events"] == []


@pytest.mark.asyncio
async def test_cognition_captures_write_life_event_results():
    """When LLM calls write_life_event_tool, the event is captured."""
    from ..nodes.cognition import cognition_node

    write_call = MagicMock()
    write_call.name = "write_life_event_tool"
    write_call.args = {
        "event_type": "salary_change",
        "confidence": 0.78,
        "evidence": ["employer ref changed"],
        "source": "llm_cognition",
        "risk_adjustment": 0.05,
    }
    write_call.id = "call-001"

    response_with_tools = MagicMock()
    response_with_tools.tool_calls = [write_call]

    response_done = MagicMock()
    response_done.tool_calls = []

    captured_event = {
        "event_type": "salary_change",
        "confidence": 0.78,
        "evidence": ["employer ref changed"],
        "source": "llm_cognition",
        "risk_adjustment": 0.05,
    }

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(side_effect=[response_with_tools, response_done])

    with patch("services.orchestration.nodes.cognition.get_langchain_cognition_llm",
               return_value=mock_llm), \
         patch("services.orchestration.nodes.cognition._execute_tool",
               new_callable=AsyncMock,
               return_value={"success": True, "event": captured_event}):

        result = await cognition_node(_base_state())

    assert len(result["llm_inferred_events"]) == 1
    assert result["llm_inferred_events"][0]["event_type"] == "salary_change"
