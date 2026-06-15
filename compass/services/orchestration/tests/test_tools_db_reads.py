import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_session(fetchrow_result=None, fetch_result=None):
    session = AsyncMock()
    session.fetchrow = AsyncMock(return_value=fetchrow_result)
    session.fetch = AsyncMock(return_value=fetch_result or [])

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm, session


@pytest.mark.asyncio
async def test_get_churn_score_raw_returns_defaults_on_none():
    from ..tools.db_reads import get_churn_score_raw

    cm, _ = _mock_session(fetchrow_result=None)
    with patch("services.orchestration.tools.db_reads.get_db_session", return_value=cm):
        result = await get_churn_score_raw("C-00000001")

    assert result["final_score"] == 0.0
    assert result["risk_tier"] == "low"


@pytest.mark.asyncio
async def test_get_consent_flags_raw_returns_empty_on_none():
    from ..tools.db_reads import get_consent_flags_raw

    cm, _ = _mock_session(fetchrow_result=None)
    with patch("services.orchestration.tools.db_reads.get_db_session", return_value=cm):
        result = await get_consent_flags_raw("C-00000001")

    assert result == {}


@pytest.mark.asyncio
async def test_get_offer_eligibility_returns_hnw_offers():
    from ..tools.db_reads import get_offer_eligibility_tool

    row = {"segment": "HNW", "annual_income_band": "10L+"}
    cm, _ = _mock_session(fetchrow_result=row)
    with patch("services.orchestration.tools.db_reads.get_db_session", return_value=cm):
        result = await get_offer_eligibility_tool.ainvoke({"customer_id": "C-00000001"})

    assert result["segment"] == "HNW"
    assert any(o["offer_code"] == "HNW_FEE_WAIVER_12M" for o in result["offers"])


@pytest.mark.asyncio
async def test_get_offer_eligibility_returns_standard_on_unknown_segment():
    from ..tools.db_reads import get_offer_eligibility_tool

    row = {"segment": "Unknown", "annual_income_band": "1L-5L"}
    cm, _ = _mock_session(fetchrow_result=row)
    with patch("services.orchestration.tools.db_reads.get_db_session", return_value=cm):
        result = await get_offer_eligibility_tool.ainvoke({"customer_id": "C-00000001"})

    assert result["offers"][0]["offer_code"] == "RETENTION_STANDARD"
