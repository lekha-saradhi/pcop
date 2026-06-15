import json
import logging
from datetime import date
from langchain_core.messages import SystemMessage, HumanMessage
from ..clients.azure_foundry import get_narrate_llm
from ..db.reads import get_top_metric_changes
from ..db.writes import write_insight_cards
from ..kafka.producer import get_kafka_producer
from ..prompts.narrate_system import NARRATE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def run_nightly_narration() -> list[dict]:
    """
    Nightly insight card generation — tailored to our platform.

    Reads 20 most significant metric deltas from ClickHouse analytical store.

    ARGUS metrics: alarm count by signal_type, WARDEN FDR rate, NEXUS events, onset_estimate distribution
    CHRONOS metrics: portfolio tier distribution, CAUSAL-NET calibration, TARE/HABITAT disagreement
    COMPASS metrics: gate suppression rate by reason, life event distribution
    HERALD metrics: SENTINEL compliance failure rate, human review queue depth, content strategy mix
    VERDICT metrics: DR uplift by channel × segment, naive vs DR bias, signal resolution at T+30
    ORACLE metrics: prompt promotion/retirement, channel policy changes, retraining events
    """
    metric_changes = await get_top_metric_changes(n=20, lookback_days=7)

    data_packet = _format_metric_changes(metric_changes)

    llm = get_narrate_llm()

    messages = [
        SystemMessage(content=NARRATE_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Date: {date.today().isoformat()}
Lookback: last 7 days vs prior 7 days

## Top {len(metric_changes)} metric changes

{data_packet}

Generate insight cards for the analyst dashboard.
"""),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content
        # Strip markdown fences if present
        if content.strip().startswith("```"):
            content = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(content)
        cards = result.get("cards", [])
    except Exception as e:
        logger.error(f"NARRATE: Failed to parse LLM response: {e}")
        cards = []

    await write_insight_cards(cards, generated_date=date.today().isoformat())

    if cards:
        try:
            producer = get_kafka_producer()
            producer.produce(
                topic="pcop.insights.v1",
                key=date.today().isoformat(),
                value=json.dumps({
                    "date": date.today().isoformat(),
                    "cards": cards,
                }).encode("utf-8"),
            )
            producer.flush()
        except Exception as e:
            logger.warning(f"NARRATE: Failed to publish cards to Kafka: {e}")

    logger.info(f"NARRATE: Generated {len(cards)} insight cards for {date.today()}")
    return cards


def _format_metric_changes(metric_changes: list[dict]) -> str:
    """Formats metric changes into a readable data packet for the LLM."""
    lines = []
    for m in metric_changes:
        lines.append(
            f"[{m.get('severity', 'info').upper()}] {m['metric_name']}: "
            f"{m.get('current_value')} vs {m.get('prior_value')} "
            f"(delta: {m.get('delta_pct', 0):+.1f}%) "
            f"segment={m.get('segment', 'all')} "
            f"channel={m.get('channel', 'all')} "
            f"n_customers={m.get('affected_customers', 'unknown')}"
        )
    return "\n".join(lines)
