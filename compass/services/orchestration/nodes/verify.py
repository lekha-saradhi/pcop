import logging
from ..state import CompassState, LifeEvent
from ..tools.db_writes import write_life_event_tool

logger = logging.getLogger(__name__)

SIGNAL_TO_EVENT_MAP = {
    "sr_transaction": None,
    "sa_ewma_recency": None,
    "cusum_salary": "salary_change",
    "beta_cusum_sentiment": None,
    "ewma_engagement": None,
    "cfsi_stress": "financial_stress",
    "location_rule": "relocation",
    "lifecycle_mcc_marriage": "marriage",
    "lifecycle_mcc_baby": "new_baby",
    "lifecycle_mcc_home": "home_purchase",
    "lifecycle_mcc_bereavement": "bereavement",
    "lifecycle_mcc_retirement": "retirement",
    "nexus_correlation": None,
    "oracle_multivariate": None,
}

EVENT_RISK_ADJUSTMENT = {
    "salary_change": +0.05,
    "financial_stress": +0.20,
    "relocation": +0.10,
    "marriage": -0.05,
    "new_baby": -0.05,
    "home_purchase": +0.08,
    "bereavement": +0.15,
    "retirement": +0.05,
    "churn_intent": +0.25,
}


async def verify_node(state: CompassState) -> dict:
    customer_id = state["customer_id"]
    signal_results = state.get("signal_results", [])
    already_inferred = {e["event_type"] for e in state.get("llm_inferred_events", [])}

    confirmed_events: list[LifeEvent] = []

    for signal in signal_results:
        if not signal.get("detected"):
            continue
        if (signal.get("confidence") or 0) < 0.80:
            continue

        signal_type = signal["signal_type"]
        event_type = SIGNAL_TO_EVENT_MAP.get(signal_type)

        if event_type is None:
            continue

        if event_type in already_inferred:
            logger.debug(
                f"VERIFY: Skipping {event_type} for {customer_id} "
                f"— already inferred by COGNITION"
            )
            continue

        event: LifeEvent = {
            "event_type": event_type,
            "confidence": signal["confidence"],
            "evidence": signal.get("evidence", []),
            "source": "rule_verify",
            "risk_adjustment": EVENT_RISK_ADJUSTMENT.get(event_type, 0.0),
        }

        result = await write_life_event_tool.ainvoke({
            "customer_id": customer_id,
            "event_type": event_type,
            "confidence": event["confidence"],
            "evidence": event["evidence"],
            "source": "rule_verify",
            "risk_adjustment": event["risk_adjustment"],
        })

        if result.get("success"):
            confirmed_events.append(event)
            logger.info(
                f"VERIFY: Confirmed {event_type} for {customer_id} "
                f"(confidence={signal['confidence']:.2f})"
            )

    return {"confirmed_events": confirmed_events}
