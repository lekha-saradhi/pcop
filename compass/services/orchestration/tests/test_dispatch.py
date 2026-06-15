import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ..nodes.dispatch import dispatch_node


def _base_state(suppressed=False, channel="email"):
    return {
        "customer_id": "C-00000001",
        "as_of_date": "2024-11-01",
        "alarm_severity": "HIGH",
        "alarm_timestamp": "2024-11-01T06:00:00Z",
        "signal_results": [],
        "risk_tier": "high",
        "final_score": 0.75,
        "action_score": 0.45,
        "confirmed_events": [],
        "llm_inferred_events": [],
        "final_events": [{"event_type": "relocation", "confidence": 0.85,
                          "evidence": [], "source": "rule_verify",
                          "risk_adjustment": 0.10}],
        "risk_adjustment": 0.10,
        "action_plan": {
            "channel": channel,
            "offer_code": "MA_RATE_UPGRADE",
            "timing": "2024-11-02T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Test",
            "suppressed": suppressed,
        },
        "gate_decision": "approved" if not suppressed else "suppressed",
        "gate_reason": None,
        "dispatch_timestamp": None,
        "outreach_id": None,
    }


@pytest.mark.asyncio
async def test_dispatch_writes_outreach_log():
    state = _base_state()

    mock_producer = MagicMock()

    with patch("services.orchestration.nodes.dispatch.write_outreach_log_tool") as mock_tool, \
         patch("services.orchestration.nodes.dispatch.get_kafka_producer",
               return_value=mock_producer):

        mock_tool.ainvoke = AsyncMock(return_value={"success": True, "outreach_id": 42})
        result = await dispatch_node(state)

    assert result["outreach_id"] == 42
    assert result["dispatch_timestamp"] is not None
    mock_producer.produce.assert_called_once()
    mock_producer.flush.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_suppressed_skips_kafka():
    state = _base_state(suppressed=True)

    mock_producer = MagicMock()

    with patch("services.orchestration.nodes.dispatch.write_outreach_log_tool") as mock_tool, \
         patch("services.orchestration.nodes.dispatch.get_kafka_producer",
               return_value=mock_producer):

        mock_tool.ainvoke = AsyncMock(return_value={"success": True, "outreach_id": 43})
        result = await dispatch_node(state)

    assert result["outreach_id"] == 43
    mock_producer.produce.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_monitor_plan_skips_kafka():
    state = _base_state(channel=None)

    mock_producer = MagicMock()

    with patch("services.orchestration.nodes.dispatch.write_outreach_log_tool") as mock_tool, \
         patch("services.orchestration.nodes.dispatch.get_kafka_producer",
               return_value=mock_producer):

        mock_tool.ainvoke = AsyncMock(return_value={"success": True, "outreach_id": 44})
        await dispatch_node(state)

    mock_producer.produce.assert_not_called()
