import pytest
from unittest.mock import AsyncMock, patch
from ..tone import derive_tone_modifiers, derive_content_strategy
from ..nodes.brief import brief_node
from .conftest import make_state


# --- derive_tone_modifiers ---

def test_tone_complaint_sentiment():
    signals = [{"signal_type": "beta_cusum_sentiment", "detected": True}]
    result = derive_tone_modifiers(signals)
    assert "empathetic" in result


def test_tone_bereavement():
    signals = [{"signal_type": "lifecycle_mcc_bereavement", "detected": True}]
    result = derive_tone_modifiers(signals)
    assert "sensitive" in result
    assert "non_promotional" in result


def test_tone_marriage():
    signals = [{"signal_type": "lifecycle_mcc_marriage", "detected": True}]
    result = derive_tone_modifiers(signals)
    assert "celebratory" in result


def test_tone_stress_suppresses_promotional():
    signals = [{"signal_type": "cfsi_stress", "detected": True}]
    result = derive_tone_modifiers(signals)
    assert "supportive" in result
    assert "non_promotional" in result


def test_tone_nexus_urgent():
    signals = [{"signal_type": "nexus_correlation", "detected": True}]
    result = derive_tone_modifiers(signals)
    assert "urgent" in result


def test_tone_engagement_only():
    signals = [{"signal_type": "ewma_engagement", "detected": True}]
    result = derive_tone_modifiers(signals)
    assert "warm_reengagement" in result


def test_tone_defaults_professional():
    result = derive_tone_modifiers([])
    assert result == ["professional"]


def test_tone_undetected_signals_ignored():
    signals = [{"signal_type": "beta_cusum_sentiment", "detected": False}]
    result = derive_tone_modifiers(signals)
    assert "empathetic" not in result


# --- derive_content_strategy ---

def test_strategy_full_retention():
    result = derive_content_strategy(treatability=0.7, final_score=0.80, risk_tier="critical")
    assert result == "full_retention"


def test_strategy_graceful_retention():
    result = derive_content_strategy(treatability=0.3, final_score=0.80, risk_tier="high")
    assert result == "graceful_retention"


def test_strategy_proactive_medium():
    result = derive_content_strategy(treatability=0.6, final_score=0.50, risk_tier="medium")
    assert result == "proactive"


def test_strategy_proactive_watch():
    result = derive_content_strategy(treatability=0.2, final_score=0.30, risk_tier="watch")
    assert result == "proactive"


def test_strategy_monitor():
    result = derive_content_strategy(treatability=0.2, final_score=0.30, risk_tier="medium")
    assert result == "monitor"


# --- brief_node ---

def _mock_db_reads():
    return patch.multiple(
        "services.content.nodes.brief",
        get_customer_profile=AsyncMock(return_value={
            "customer_id": "C-00000001",
            "full_name": "Priya Sharma",
            "segment": "Mass Affluent",
            "tenure_years": 4.5,
            "preferred_channel": "email",
        }),
        get_churn_score_with_reasons=AsyncMock(return_value={
            "final_score": 0.78,
            "risk_tier": "high",
            "treatability_score": 0.65,
            "action_score": 0.45,
            "reason_codes_v2": [
                {"category": "engagement_drop", "description": "Login -65%", "importance": 0.89, "source": "both"},
            ],
        }),
        get_signal_results=AsyncMock(return_value=[]),
        get_prior_outreach=AsyncMock(return_value=[]),
        get_account_summary=AsyncMock(return_value={"accounts": []}),
        get_best_prompt_version=AsyncMock(return_value={
            "version_id": "v1",
            "system_prompt": "",
            "few_shot_examples": [],
            "tone_instructions": "",
            "offer_instructions": "",
        }),
        get_offer_details=AsyncMock(return_value={
            "description": "Rate upgrade",
            "value": "0.5% additional p.a.",
        }),
    )


@pytest.mark.asyncio
async def test_brief_node_populates_all_fields():
    state = make_state()

    with _mock_db_reads():
        result = await brief_node(state)

    brief = result["brief"]
    assert brief["customer_id"] == "C-00000001"
    assert brief["full_name"] == "Priya Sharma"
    assert brief["first_name"] == "Priya"
    assert brief["segment"] == "Mass Affluent"
    assert brief["content_strategy"] in ("full_retention", "graceful_retention", "proactive", "monitor")
    assert isinstance(brief["tone_modifiers"], list)
    assert len(brief["tone_modifiers"]) >= 1


@pytest.mark.asyncio
async def test_brief_node_reason_codes_populated():
    state = make_state()

    with _mock_db_reads():
        result = await brief_node(state)

    assert len(result["brief"]["reason_codes"]) == 1
    assert result["brief"]["reason_codes"][0]["category"] == "engagement_drop"


@pytest.mark.asyncio
async def test_brief_node_primary_event_from_confirmed():
    import copy
    state = make_state()
    state["action_plan_event"]["final_events"] = [
        {"event_type": "job_change", "confidence": 0.91, "evidence": [], "source": "llm_cognition"},
        {"event_type": "relocation", "confidence": 0.88, "evidence": [], "source": "rule_verify"},
    ]

    with _mock_db_reads():
        result = await brief_node(state)

    assert result["brief"]["primary_event"] == "job_change"
