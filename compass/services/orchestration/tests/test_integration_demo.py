import pytest
from unittest.mock import AsyncMock, patch
from ..graph.builder import build_demo_graph
from ..state import CompassState


@pytest.fixture
def graph():
    return build_demo_graph()


def _build_state(customer_id, severity, signals) -> CompassState:
    return {
        "customer_id": customer_id,
        "as_of_date": "2024-11-01",
        "alarm_severity": severity,
        "alarm_timestamp": "2024-11-01T06:00:00Z",
        "signal_results": signals,
        "risk_tier": None, "final_score": None, "action_score": None,
        "confirmed_events": [], "llm_inferred_events": [],
        "final_events": [], "risk_adjustment": 0.0,
        "action_plan": None, "gate_decision": None, "gate_reason": None,
        "dispatch_timestamp": None, "outreach_id": None,
    }


def _mock_all_db():
    """Mocks all DB calls so integration tests need no real database."""
    return patch.multiple(
        "services.orchestration.tools.db_reads",
        get_churn_score_raw=AsyncMock(return_value={
            "final_score": 0.87, "risk_tier": "critical", "action_score": 0.52,
        }),
        get_consent_flags_raw=AsyncMock(return_value={
            "email_opt_in": True, "sms_opt_in": True,
            "push_opt_in": True, "call_opt_in": True,
        }),
        get_channel_history_raw=AsyncMock(return_value=[]),
    )


def _mock_llm_tools():
    """Mocks LLM clients so tests don't hit NVIDIA API."""
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.tool_calls = []
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


def _mock_write_tools():
    return patch.multiple(
        "services.orchestration.tools.db_writes",
        write_life_event_tool=AsyncMock(return_value={"success": True}),
        write_action_plan_tool=AsyncMock(return_value={
            "success": True,
            "action_plan": {
                "channel": "email", "offer_code": "HNW_FEE_WAIVER_12M",
                "timing": "2024-11-02T09:00:00", "owner_id": "system",
                "priority": 2, "rationale": "Test", "suppressed": False,
            },
        }),
        write_outreach_log_tool=AsyncMock(return_value={"success": True, "outreach_id": 1}),
    )


@pytest.mark.asyncio
async def test_c00000001_relocation_confirmed(graph):
    """
    C-00000001: location_rule >= 0.80 → relocation confirmed by VERIFY.
    """
    state = _build_state("C-00000001", "CRITICAL", [
        {"signal_type": "location_rule", "detected": True, "confidence": 0.91,
         "evidence": ["Bangalore 68% dominance"], "direction": None,
         "onset_estimate": "2024-10-01"},
    ])

    mock_llm = _mock_llm_tools()

    with _mock_all_db(), \
         _mock_write_tools(), \
         patch("services.orchestration.nodes.verify.write_life_event_tool") as mock_verify_write, \
         patch("services.orchestration.nodes.dispatch.write_outreach_log_tool") as mock_dispatch_write, \
         patch("services.orchestration.nodes.dispatch.get_kafka_producer") as mock_kafka, \
         patch("services.orchestration.nodes.intake.get_churn_score_raw",
               new_callable=AsyncMock,
               return_value={"final_score": 0.87, "risk_tier": "critical",
                             "action_score": 0.52}), \
         patch("services.orchestration.clients.azure_foundry.get_langchain_compass_llm",
               return_value=mock_llm), \
         patch("services.orchestration.nodes.gate.get_consent_flags_raw",
               new_callable=AsyncMock,
               return_value={"email_opt_in": True, "sms_opt_in": True,
                             "push_opt_in": True, "call_opt_in": True}), \
         patch("services.orchestration.nodes.gate.get_channel_history_raw",
               new_callable=AsyncMock, return_value=[]):

        mock_verify_write.ainvoke = AsyncMock(return_value={"success": True})
        mock_dispatch_write.ainvoke = AsyncMock(
            return_value={"success": True, "outreach_id": 10}
        )
        mock_kafka.return_value = mock_kafka
        mock_kafka.produce = lambda **kwargs: None
        mock_kafka.flush = lambda: None

        result = await graph.ainvoke(state)

    confirmed_types = [e["event_type"] for e in result.get("confirmed_events", [])]
    assert "relocation" in confirmed_types or "relocation" in [
        e["event_type"] for e in result.get("final_events", [])
    ]


@pytest.mark.asyncio
async def test_c00000006_bereavement_confirmed(graph):
    """
    C-00000006: lifecycle_mcc_bereavement >= 0.80 → bereavement confirmed by VERIFY.
    """
    state = _build_state("C-00000006", "CRITICAL", [
        {"signal_type": "lifecycle_mcc_bereavement", "detected": True, "confidence": 0.95,
         "evidence": ["MCC 7261 (funeral)", "MCC 8111 (legal)"], "direction": None,
         "onset_estimate": "2024-10-25"},
    ])

    mock_llm = _mock_llm_tools()

    with _mock_all_db(), \
         patch("services.orchestration.nodes.verify.write_life_event_tool") as mock_vw, \
         patch("services.orchestration.nodes.dispatch.write_outreach_log_tool") as mock_dw, \
         patch("services.orchestration.nodes.dispatch.get_kafka_producer") as mock_kafka, \
         patch("services.orchestration.nodes.intake.get_churn_score_raw",
               new_callable=AsyncMock,
               return_value={"final_score": 0.87, "risk_tier": "critical",
                             "action_score": 0.52}), \
         patch("services.orchestration.clients.azure_foundry.get_langchain_compass_llm",
               return_value=mock_llm), \
         patch("services.orchestration.nodes.gate.get_consent_flags_raw",
               new_callable=AsyncMock,
               return_value={"email_opt_in": True, "sms_opt_in": True,
                             "push_opt_in": True, "call_opt_in": True}), \
         patch("services.orchestration.nodes.gate.get_channel_history_raw",
               new_callable=AsyncMock, return_value=[]):

        mock_vw.ainvoke = AsyncMock(return_value={"success": True})
        mock_dw.ainvoke = AsyncMock(return_value={"success": True, "outreach_id": 20})
        mock_kafka.return_value = mock_kafka
        mock_kafka.produce = lambda **kwargs: None
        mock_kafka.flush = lambda: None

        result = await graph.ainvoke(state)

    event_types = [e["event_type"] for e in result.get("final_events", [])]
    assert "bereavement" in event_types
