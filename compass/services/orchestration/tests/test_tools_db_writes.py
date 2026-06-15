import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ..tools.db_writes import _score_to_tier


def _mock_session(fetchrow_result=None, execute_result=None):
    session = AsyncMock()
    session.fetchrow = AsyncMock(return_value=fetchrow_result)
    session.execute = AsyncMock(return_value=execute_result)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm, session


class TestScoreToTier:
    def test_critical(self):
        assert _score_to_tier(0.90) == "critical"

    def test_high(self):
        assert _score_to_tier(0.70) == "high"

    def test_medium(self):
        assert _score_to_tier(0.50) == "medium"

    def test_watch(self):
        assert _score_to_tier(0.25) == "watch"

    def test_low(self):
        assert _score_to_tier(0.10) == "low"

    def test_boundary_critical(self):
        assert _score_to_tier(0.85) == "critical"

    def test_boundary_high(self):
        assert _score_to_tier(0.65) == "high"


@pytest.mark.asyncio
async def test_write_life_event_rejects_invalid_event_type():
    from ..tools.db_writes import write_life_event_tool

    result = await write_life_event_tool.ainvoke({
        "customer_id": "C-001",
        "event_type": "invalid_event",
        "confidence": 0.8,
        "evidence": [],
        "source": "rule_verify",
        "risk_adjustment": 0.05,
    })
    assert result["success"] is False
    assert "Invalid event_type" in result["error"]


@pytest.mark.asyncio
async def test_write_life_event_rejects_out_of_range_confidence():
    from ..tools.db_writes import write_life_event_tool

    result = await write_life_event_tool.ainvoke({
        "customer_id": "C-001",
        "event_type": "relocation",
        "confidence": 1.5,
        "evidence": [],
        "source": "rule_verify",
        "risk_adjustment": 0.05,
    })
    assert result["success"] is False


@pytest.mark.asyncio
async def test_write_action_plan_rejects_invalid_channel():
    from ..tools.db_writes import write_action_plan_tool

    result = await write_action_plan_tool.ainvoke({
        "customer_id": "C-001",
        "channel": "carrier_pigeon",
        "offer_code": "TEST",
        "timing": "2024-11-01T09:00:00",
        "owner_id": "system",
        "priority": 3,
        "rationale": "test",
    })
    assert result["success"] is False
    assert "Invalid channel" in result["error"]


@pytest.mark.asyncio
async def test_adjust_risk_score_clamps_adjustment():
    from ..tools.db_writes import adjust_risk_score_tool

    row = MagicMock()
    row.__getitem__ = lambda self, key: 0.7 if key == "final_score" else "high"

    cm, session = _mock_session(fetchrow_result=row)
    session.fetchrow = AsyncMock(return_value=row)

    with patch("services.orchestration.tools.db_writes.get_db_session", return_value=cm):
        result = await adjust_risk_score_tool.ainvoke({
            "customer_id": "C-001",
            "adjustment": 0.99,
            "reason": "test over-adjustment",
        })

    # adjustment should be clamped to 0.30
    assert result["new_score"] == pytest.approx(0.7 + 0.30)
