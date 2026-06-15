import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from ..nodes.sentinel import sentinel_node, _regex_check, _content_to_string
from ..prompts.prohibited_phrases import PROHIBITED_PHRASES
from .conftest import make_state


EMAIL_CLEAN = {
    "subject_line": "A note for you, Priya",
    "preheader": "We'd like to help",
    "greeting": "Dear Priya",
    "body_html": "<p>We noticed your banking activity changed recently.</p>",
    "cta_text": "See your offer",
}

EMAIL_DIRTY = {
    "subject_line": "Guaranteed rate offer for you!",
    "body_html": "<p>This is your last chance to get our guaranteed rate.</p>",
    "cta_text": "Act now",
}


# --- _regex_check ---

def test_regex_clean_passes():
    result = _regex_check("Hello Priya, your account has a new offer waiting.")
    assert result["passed"] is True


def test_regex_prohibited_phrase_fails():
    for phrase in PROHIBITED_PHRASES[:5]:
        content = f"This content contains {phrase} as a phrase."
        result = _regex_check(content)
        assert result["passed"] is False, f"Expected fail for phrase: {phrase}"


def test_regex_rate_guarantee_pattern_fails():
    result = _regex_check("Your rate is 8.5% guaranteed forever.")
    assert result["passed"] is False


def test_regex_all_caps_fails():
    result = _regex_check("SPECIAL OFFER AVAILABLE NOW FOR YOU")
    assert result["passed"] is False


def test_regex_savings_claim_fails():
    result = _regex_check("You can save up to 40% on your fees.")
    assert result["passed"] is False


# --- sentinel_node ---

def _mock_llm_pass():
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "verdict": "PASS",
        "reason": "No compliance issues detected.",
        "fix_hint": None,
    })
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


def _mock_llm_fail(reason="Misleading claim", fix="Remove the claim"):
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "verdict": "FAIL",
        "reason": reason,
        "fix_hint": fix,
    })
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


@pytest.mark.asyncio
async def test_sentinel_clean_content_passes():
    state = make_state(generated_content=EMAIL_CLEAN)

    with patch("services.content.nodes.sentinel.get_scribe_llm", return_value=_mock_llm_pass()):
        result = await sentinel_node(state)

    assert result["compliance_status"] == "passed"
    assert result["human_review_required"] is False


@pytest.mark.asyncio
async def test_sentinel_prohibited_phrase_triggers_human_review_after_retries():
    state = make_state(generated_content=EMAIL_DIRTY, retry_count=2)

    result = await sentinel_node(state)

    assert result["compliance_status"] == "human_review"
    assert result["human_review_required"] is True
    assert "Regex" in result["compliance_notes"]


@pytest.mark.asyncio
async def test_sentinel_llm_fail_triggers_human_review_after_retries():
    state = make_state(generated_content=EMAIL_CLEAN, retry_count=2)

    with patch("services.content.nodes.sentinel.get_scribe_llm", return_value=_mock_llm_fail()):
        result = await sentinel_node(state)

    assert result["compliance_status"] == "human_review"
    assert result["human_review_required"] is True
    assert "LLM" in result["compliance_notes"]


@pytest.mark.asyncio
async def test_sentinel_llm_parse_error_defaults_pass():
    state = make_state(generated_content=EMAIL_CLEAN)

    bad_response = MagicMock()
    bad_response.content = "NOT JSON AT ALL"
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=bad_response)

    with patch("services.content.nodes.sentinel.get_scribe_llm", return_value=mock_llm):
        result = await sentinel_node(state)

    assert result["compliance_status"] == "passed"
