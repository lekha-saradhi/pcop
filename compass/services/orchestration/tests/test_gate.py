import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from ..nodes.gate import gate_node
from ..state import CompassState


@pytest.fixture
def base_state() -> CompassState:
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
        "final_events": [],
        "risk_adjustment": 0.0,
        "action_plan": {
            "channel": "email",
            "offer_code": "MA_RATE_UPGRADE",
            "timing": "2024-11-02T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Test plan",
            "suppressed": False,
        },
        "gate_decision": None,
        "gate_reason": None,
        "dispatch_timestamp": None,
        "outreach_id": None,
    }


@pytest.mark.asyncio
async def test_gate_approves_clean_customer(base_state):
    with patch("services.orchestration.nodes.gate.get_consent_flags_raw",
               new_callable=AsyncMock,
               return_value={"email_opt_in": True, "sms_opt_in": True,
                             "push_opt_in": True, "call_opt_in": True}), \
         patch("services.orchestration.nodes.gate.get_channel_history_raw",
               new_callable=AsyncMock,
               return_value=[]):

        result = await gate_node(base_state)
        assert result["gate_decision"] == "approved"
        assert result["action_plan"]["suppressed"] is False


@pytest.mark.asyncio
async def test_gate_suppresses_email_optout(base_state):
    with patch("services.orchestration.nodes.gate.get_consent_flags_raw",
               new_callable=AsyncMock,
               return_value={"email_opt_in": False, "sms_opt_in": True,
                             "push_opt_in": True, "call_opt_in": True}), \
         patch("services.orchestration.nodes.gate.get_channel_history_raw",
               new_callable=AsyncMock,
               return_value=[]):

        result = await gate_node(base_state)
        assert result["gate_decision"] == "suppressed"
        assert "opted_out" in result["gate_reason"]


@pytest.mark.asyncio
async def test_gate_rescue_override_bypasses_cooldown(base_state):
    base_state["final_score"] = 0.95

    recent_email = {
        "channel": "email",
        "dispatched_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
    }

    with patch("services.orchestration.nodes.gate.get_consent_flags_raw",
               new_callable=AsyncMock,
               return_value={"email_opt_in": True}), \
         patch("services.orchestration.nodes.gate.get_channel_history_raw",
               new_callable=AsyncMock,
               return_value=[recent_email]):

        result = await gate_node(base_state)
        assert result["gate_decision"] == "approved"
        assert result["gate_reason"] == "rescue_override"


@pytest.mark.asyncio
async def test_gate_suppresses_cooldown(base_state):
    recent_email = {
        "channel": "email",
        "dispatched_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
    }

    with patch("services.orchestration.nodes.gate.get_consent_flags_raw",
               new_callable=AsyncMock,
               return_value={"email_opt_in": True}), \
         patch("services.orchestration.nodes.gate.get_channel_history_raw",
               new_callable=AsyncMock,
               return_value=[recent_email]):

        result = await gate_node(base_state)
        assert result["gate_decision"] == "suppressed"
        assert "cooldown" in result["gate_reason"]


@pytest.mark.asyncio
async def test_gate_suppresses_fatigue(base_state):
    recent_touches = [
        {
            "channel": "email",
            "dispatched_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
        }
        for i in range(4)
    ]

    with patch("services.orchestration.nodes.gate.get_consent_flags_raw",
               new_callable=AsyncMock,
               return_value={"email_opt_in": True}), \
         patch("services.orchestration.nodes.gate.get_channel_history_raw",
               new_callable=AsyncMock,
               return_value=recent_touches):

        result = await gate_node(base_state)
        assert result["gate_decision"] == "suppressed"
        assert "fatigue" in result["gate_reason"]


@pytest.mark.asyncio
async def test_gate_monitor_plan_always_passes(base_state):
    base_state["action_plan"]["channel"] = None
    result = await gate_node(base_state)
    assert result["gate_decision"] == "approved"
