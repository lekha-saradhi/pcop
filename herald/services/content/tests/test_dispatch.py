import pytest
from unittest.mock import AsyncMock, patch
from ..nodes.dispatch import dispatch_node
from .conftest import make_state


EMAIL_CONTENT = {
    "subject_line": "Hello Priya",
    "body_html": "<p>Your offer</p>[LEGAL_FOOTER][UNSUBSCRIBE_LINK]",
    "cta_text": "See offer",
}

SMS_CONTENT = {
    "message": "[BankName]: Priya, your offer is ready.",
}

APP_CONTENT = {
    "title": "Your offer is ready",
    "card_body": "0.5% extra on savings",
    "cta_label": "See offer",
}


@pytest.mark.asyncio
async def test_dispatch_email_demo_mode(monkeypatch):
    monkeypatch.setenv("HERALD_DEMO_MODE", "true")
    state = make_state(
        channel="email",
        generated_content=EMAIL_CONTENT,
        compliance_status="passed",
    )

    with patch("services.content.nodes.dispatch.get_customer_contact",
               new_callable=AsyncMock,
               return_value={"email": "priya@example.com", "phone_mobile": "+910000"}):
        result = await dispatch_node(state)

    assert result["dispatched"] is True
    assert result["dispatch_provider_id"] is not None


@pytest.mark.asyncio
async def test_dispatch_sms_demo_mode(monkeypatch):
    monkeypatch.setenv("HERALD_DEMO_MODE", "true")
    state = make_state(
        channel="sms",
        generated_content=SMS_CONTENT,
        compliance_status="passed",
    )

    with patch("services.content.nodes.dispatch.get_customer_contact",
               new_callable=AsyncMock,
               return_value={"email": "", "phone_mobile": "+910000000000"}):
        result = await dispatch_node(state)

    assert result["dispatched"] is True


@pytest.mark.asyncio
async def test_dispatch_skips_human_review_required():
    state = make_state(
        generated_content=EMAIL_CONTENT,
        human_review_required=True,
    )
    result = await dispatch_node(state)
    assert result["dispatched"] is False


@pytest.mark.asyncio
async def test_dispatch_unknown_channel_returns_false():
    state = make_state(channel="fax", generated_content={"message": "hello"})
    state["channel"] = "fax"
    result = await dispatch_node(state)
    assert result["dispatched"] is False


@pytest.mark.asyncio
async def test_dispatch_app_demo_mode(monkeypatch):
    monkeypatch.setenv("HERALD_DEMO_MODE", "true")
    state = make_state(
        channel="app",
        generated_content=APP_CONTENT,
        compliance_status="passed",
    )

    with patch("services.content.nodes.dispatch.get_push_token",
               new_callable=AsyncMock,
               return_value="fcm-token-abc123"):
        result = await dispatch_node(state)

    assert result["dispatched"] is True
