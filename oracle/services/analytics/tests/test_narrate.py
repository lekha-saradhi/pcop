import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


DEMO_METRICS = [
    {"metric_name": "argus_alarm_count", "current_value": 847, "prior_value": 612, "delta_pct": 38.4, "severity": "high", "segment": "mass_affluent", "channel": "all", "affected_customers": 847},
    {"metric_name": "dr_uplift_email", "current_value": 0.082, "prior_value": 0.065, "delta_pct": 26.2, "severity": "info", "segment": "all", "channel": "email", "affected_customers": None},
    {"metric_name": "sentinel_failure_rate", "current_value": 0.031, "prior_value": 0.018, "delta_pct": 72.2, "severity": "high", "segment": "all", "channel": "sms", "affected_customers": 143},
]

DEMO_CARDS = [
    {
        "severity": "high",
        "title": "ARGUS alarm volume surged +38% in Mass Affluent segment",
        "what": "ARGUS alarm count rose from 612 to 847 in 7 days",
        "why": "Likely driven by TEMPO transaction frequency signal breaching 2σ limits",
        "where": "Mass Affluent segment, all regions",
        "recommend": "Increase COMPASS dispatch capacity and review WARDEN FDR threshold",
        "metric_name": "argus_alarm_count",
        "metric_delta": "+38.4%",
        "affected_customers": 847,
    },
    {
        "severity": "high",
        "title": "HERALD SENTINEL failure rate on SMS spiked +72%",
        "what": "SMS compliance failure rate rose from 1.8% to 3.1%",
        "why": "Possible new prohibited phrase pattern in sms_v2 template",
        "where": "SMS channel, all segments",
        "recommend": "Audit SMS prompt version and review PROHIBITED_PHRASES list",
        "metric_name": "sentinel_failure_rate",
        "metric_delta": "+72.2%",
        "affected_customers": 143,
    },
]


@pytest.mark.asyncio
async def test_narrate_writes_insight_cards():
    """run_nightly_narration writes cards to DB."""
    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps({"cards": DEMO_CARDS})

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

    mock_producer = MagicMock()
    mock_producer.produce = MagicMock()
    mock_producer.flush = MagicMock()

    with patch("services.analytics.cycles.narrate.get_top_metric_changes",
               new_callable=AsyncMock, return_value=DEMO_METRICS), \
         patch("services.analytics.cycles.narrate.get_narrate_llm", return_value=mock_llm), \
         patch("services.analytics.cycles.narrate.write_insight_cards",
               new_callable=AsyncMock) as mock_write, \
         patch("services.analytics.cycles.narrate.get_kafka_producer",
               return_value=mock_producer):

        from services.analytics.cycles.narrate import run_nightly_narration
        cards = await run_nightly_narration()

    assert len(cards) == 2
    mock_write.assert_called_once()
    call_cards = mock_write.call_args[0][0]
    assert len(call_cards) == 2


@pytest.mark.asyncio
async def test_narrate_publishes_to_kafka():
    """run_nightly_narration publishes cards to pcop.insights.v1."""
    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps({"cards": DEMO_CARDS})

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

    mock_producer = MagicMock()

    with patch("services.analytics.cycles.narrate.get_top_metric_changes",
               new_callable=AsyncMock, return_value=DEMO_METRICS), \
         patch("services.analytics.cycles.narrate.get_narrate_llm", return_value=mock_llm), \
         patch("services.analytics.cycles.narrate.write_insight_cards", new_callable=AsyncMock), \
         patch("services.analytics.cycles.narrate.get_kafka_producer",
               return_value=mock_producer):

        from services.analytics.cycles.narrate import run_nightly_narration
        await run_nightly_narration()

    mock_producer.produce.assert_called_once()
    call_kwargs = mock_producer.produce.call_args.kwargs
    assert call_kwargs["topic"] == "pcop.insights.v1"


@pytest.mark.asyncio
async def test_narrate_handles_llm_parse_failure():
    """run_nightly_narration returns empty list on LLM parse failure."""
    mock_llm_response = MagicMock()
    mock_llm_response.content = "not valid json"

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

    with patch("services.analytics.cycles.narrate.get_top_metric_changes",
               new_callable=AsyncMock, return_value=DEMO_METRICS), \
         patch("services.analytics.cycles.narrate.get_narrate_llm", return_value=mock_llm), \
         patch("services.analytics.cycles.narrate.write_insight_cards", new_callable=AsyncMock), \
         patch("services.analytics.cycles.narrate.get_kafka_producer", return_value=MagicMock()):

        from services.analytics.cycles.narrate import run_nightly_narration
        cards = await run_nightly_narration()

    assert cards == []


@pytest.mark.asyncio
async def test_narrate_strips_markdown_fences():
    """LLM responses wrapped in ```json blocks are parsed correctly."""
    mock_llm_response = MagicMock()
    mock_llm_response.content = "```json\n" + json.dumps({"cards": DEMO_CARDS}) + "\n```"

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

    with patch("services.analytics.cycles.narrate.get_top_metric_changes",
               new_callable=AsyncMock, return_value=DEMO_METRICS), \
         patch("services.analytics.cycles.narrate.get_narrate_llm", return_value=mock_llm), \
         patch("services.analytics.cycles.narrate.write_insight_cards", new_callable=AsyncMock), \
         patch("services.analytics.cycles.narrate.get_kafka_producer", return_value=MagicMock()):

        from services.analytics.cycles.narrate import run_nightly_narration
        cards = await run_nightly_narration()

    assert len(cards) == 2
