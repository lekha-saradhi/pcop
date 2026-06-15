import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from ..nodes.scribe import scribe_node, _build_human_message
from .conftest import make_state, make_brief


def _mock_llm(content_dict: dict):
    mock_response = MagicMock()
    mock_response.content = json.dumps(content_dict)
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


EMAIL_CONTENT = {
    "subject_line": "Priya, a note from your relationship team",
    "preheader": "We noticed some changes and want to help",
    "greeting": "Dear Priya",
    "body_html": "<p>We noticed your engagement has changed recently...</p>[LEGAL_FOOTER][UNSUBSCRIBE_LINK]",
    "cta_text": "See your offer",
    "ab_variant": {
        "subject_line": "Your personalised rate upgrade — Priya",
        "body_html": "<p>As a valued Mass Affluent customer...</p>[LEGAL_FOOTER][UNSUBSCRIBE_LINK]",
    },
}

SMS_CONTENT = {
    "message": "[BankName]: Priya, your account upgrade is ready. Call us to activate your rate upgrade.",
}

APP_CONTENT = {
    "title": "Your rate upgrade is ready",
    "card_body": "As a valued customer, you qualify for 0.5% extra p.a. on your savings.",
    "cta_label": "See offer",
}

CALL_CONTENT = {
    "opening": {"duration_seconds": 30, "script": "Hello, am I speaking with Priya?"},
    "talking_points": [
        {"point": "Engagement", "script": "We noticed...", "objective": "Acknowledge"},
        {"point": "Offer", "script": "We'd like to...", "objective": "Present offer"},
        {"point": "Next steps", "script": "I can arrange...", "objective": "Commit"},
    ],
    "objection_handlers": [
        {"objection": "I'm happy with my current setup", "response": "Absolutely understood..."},
        {"objection": "I need to think about it", "response": "Of course..."},
    ],
    "close": {"script": "Thank you for your time, Priya. I'll send a summary email."},
}

RM_CONTENT = {
    "customer_summary": "Priya Sharma, Mass Affluent, 4.5 years tenure.",
    "event_context": "Job change detected October 2024.",
    "signal_evidence": "Login frequency -65% vs baseline; Last login 14d ago",
    "pre_approved_offer": "MA_RATE_UPGRADE: 0.5% additional p.a.",
    "conversation_agenda": ["Discuss recent changes", "Present rate upgrade", "Next steps"],
    "objection_guide": [
        {"objection": "I'm busy", "suggested_response": "Of course, I can schedule a call."},
    ],
    "sensitivity_notes": "No complaint signals active.",
}


@pytest.mark.asyncio
async def test_scribe_email_extracts_ab_variant():
    state = make_state(channel="email")
    mock_llm = _mock_llm(EMAIL_CONTENT)

    with patch("services.content.nodes.scribe.get_scribe_llm", return_value=mock_llm):
        result = await scribe_node(state)

    assert "subject_line" in result["generated_content"]
    assert "ab_variant" not in result["generated_content"]
    assert result["ab_variant"] is not None
    assert "subject_line" in result["ab_variant"]


@pytest.mark.asyncio
async def test_scribe_sms_no_ab_variant():
    state = make_state(channel="sms")
    mock_llm = _mock_llm(SMS_CONTENT)

    with patch("services.content.nodes.scribe.get_scribe_llm", return_value=mock_llm):
        result = await scribe_node(state)

    assert "message" in result["generated_content"]
    assert result["ab_variant"] is None


@pytest.mark.asyncio
async def test_scribe_app_returns_title_and_cta():
    state = make_state(channel="app")
    mock_llm = _mock_llm(APP_CONTENT)

    with patch("services.content.nodes.scribe.get_scribe_llm", return_value=mock_llm):
        result = await scribe_node(state)

    assert "title" in result["generated_content"]
    assert "card_body" in result["generated_content"]
    assert "cta_label" in result["generated_content"]


@pytest.mark.asyncio
async def test_scribe_call_script_structure():
    state = make_state(channel="call")
    mock_llm = _mock_llm(CALL_CONTENT)

    with patch("services.content.nodes.scribe.get_scribe_llm", return_value=mock_llm):
        result = await scribe_node(state)

    content = result["generated_content"]
    assert "opening" in content
    assert len(content["talking_points"]) == 3
    assert len(content["objection_handlers"]) == 2


@pytest.mark.asyncio
async def test_scribe_rm_visit_all_sections():
    state = make_state(channel="rm_visit")
    mock_llm = _mock_llm(RM_CONTENT)

    with patch("services.content.nodes.scribe.get_scribe_llm", return_value=mock_llm):
        result = await scribe_node(state)

    content = result["generated_content"]
    for section in ["customer_summary", "event_context", "signal_evidence",
                     "pre_approved_offer", "conversation_agenda", "objection_guide"]:
        assert section in content


@pytest.mark.asyncio
async def test_scribe_strips_markdown_code_blocks():
    state = make_state(channel="sms")
    raw = "```json\n" + json.dumps(SMS_CONTENT) + "\n```"

    mock_response = MagicMock()
    mock_response.content = raw
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("services.content.nodes.scribe.get_scribe_llm", return_value=mock_llm):
        result = await scribe_node(state)

    assert "message" in result["generated_content"]


def test_build_human_message_includes_reason_codes():
    brief = make_brief(reason_codes=[
        {"category": "engagement_drop", "description": "Login -65%", "importance": 0.89, "source": "both"},
    ])
    msg = _build_human_message(brief)
    assert "engagement_drop" in msg
    assert "Login -65%" in msg
