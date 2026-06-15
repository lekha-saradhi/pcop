import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from ..graph.builder import build_herald_graph


@pytest.fixture
def graph():
    return build_herald_graph()


def _build_state(customer_id, channel, alarm_severity, final_events, offer_code="MA_RATE_UPGRADE"):
    return {
        "action_plan_event": {
            "customer_id": customer_id,
            "outreach_id": int(customer_id.replace("C-", "")),
            "as_of_date": "2024-11-01",
            "risk_tier": "high",
            "final_score": 0.78,
            "action_score": 0.45,
            "final_events": final_events,
            "action_plan": {
                "channel": channel,
                "offer_code": offer_code,
                "timing": "2024-11-02T09:00:00",
                "owner_id": "system",
                "priority": 2,
                "rationale": "Integration test",
            },
            "dispatch_timestamp": "2024-11-01T06:00:00Z",
        },
        "customer_id": customer_id,
        "channel": channel,
        "brief": None,
        "generated_content": None,
        "ab_variant": None,
        "compliance_status": None,
        "compliance_notes": None,
        "retry_count": 0,
        "dispatched": False,
        "dispatch_provider_id": None,
        "content_store_id": None,
        "human_review_required": False,
    }


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
            "reason_codes_v2": [],
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
        get_offer_details=AsyncMock(return_value={"description": "Rate upgrade", "value": "0.5% p.a."}),
    )


def _mock_scribe_email():
    content = {
        "subject_line": "Priya, your personalised offer",
        "preheader": "A message from your bank",
        "greeting": "Dear Priya",
        "body_html": "<p>We have an offer for you.</p>[LEGAL_FOOTER][UNSUBSCRIBE_LINK]",
        "cta_text": "See offer",
        "ab_variant": {
            "subject_line": "Alternative subject",
            "body_html": "<p>Alternative body</p>[LEGAL_FOOTER][UNSUBSCRIBE_LINK]",
        },
    }
    mock_response = MagicMock()
    mock_response.content = json.dumps(content)
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


def _mock_db_writes():
    return patch.multiple(
        "services.content.nodes.chronicle",
        write_content_store=AsyncMock(return_value=100),
        update_outreach_log_status=AsyncMock(return_value=None),
        write_human_review_queue=AsyncMock(return_value=None),
    )


@pytest.mark.asyncio
async def test_integration_email_full_pipeline(graph, monkeypatch):
    monkeypatch.setenv("HERALD_DEMO_MODE", "true")
    state = _build_state(
        "C-00000001", "email", "HIGH",
        [{"event_type": "job_change", "confidence": 0.91, "evidence": ["Employer changed"], "source": "rule_verify"}],
    )

    mock_llm = _mock_scribe_email()
    mock_producer = MagicMock()
    mock_producer.produce = MagicMock()
    mock_producer.flush = MagicMock()

    compliance_pass = MagicMock()
    compliance_pass.content = json.dumps({"verdict": "PASS", "reason": "OK", "fix_hint": None})
    mock_llm.ainvoke = AsyncMock(side_effect=[
        MagicMock(content=json.dumps({
            "subject_line": "Priya, your personalised offer",
            "preheader": "A message from your bank",
            "greeting": "Dear Priya",
            "body_html": "<p>Offer here</p>[LEGAL_FOOTER][UNSUBSCRIBE_LINK]",
            "cta_text": "See offer",
            "ab_variant": {"subject_line": "Alt", "body_html": "<p>Alt</p>[LEGAL_FOOTER]"},
        })),
        MagicMock(content=json.dumps({"verdict": "PASS", "reason": "OK", "fix_hint": None})),
    ])

    with _mock_db_reads(), \
         _mock_db_writes(), \
         patch("services.content.nodes.scribe.get_scribe_llm", return_value=mock_llm), \
         patch("services.content.nodes.sentinel.get_scribe_llm", return_value=mock_llm), \
         patch("services.content.nodes.dispatch.get_customer_contact",
               new_callable=AsyncMock,
               return_value={"email": "priya@example.com", "phone_mobile": ""}), \
         patch("services.content.nodes.chronicle.get_kafka_producer", return_value=mock_producer):

        result = await graph.ainvoke(state)

    assert result["compliance_status"] == "passed"
    assert result["dispatched"] is True
    assert result["content_store_id"] == 100


@pytest.mark.asyncio
async def test_integration_monitor_plan_skipped():
    """HeraldConsumer skips monitor plans before graph invocation."""
    from ..kafka.consumer import HeraldConsumer

    consumer = HeraldConsumer(demo_mode=True)

    monitor_event = {
        "customer_id": "C-00000005",
        "outreach_id": 5,
        "risk_tier": "watch",
        "final_score": 0.25,
        "final_events": [],
        "action_plan": {"channel": None, "offer_code": None, "priority": 5, "rationale": "monitor"},
    }

    graph_called = False
    original_ainvoke = consumer.graph.ainvoke

    async def mock_ainvoke(state):
        nonlocal graph_called
        graph_called = True
        return {}

    consumer.graph.ainvoke = mock_ainvoke
    await consumer._process(monitor_event)
    assert graph_called is False
