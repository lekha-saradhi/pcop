import logging
from ..state import CompassState, LifeEvent

logger = logging.getLogger(__name__)


async def merge_node(state: CompassState) -> dict:
    customer_id = state["customer_id"]
    confirmed = state.get("confirmed_events", [])
    inferred = state.get("llm_inferred_events", [])

    event_map: dict[str, LifeEvent] = {}

    for event in confirmed + inferred:
        event_type = event["event_type"]
        if event_type not in event_map:
            event_map[event_type] = event
        else:
            if event["confidence"] > event_map[event_type]["confidence"]:
                event_map[event_type] = event

    final_events = list(event_map.values())

    raw_adjustment = sum(e.get("risk_adjustment", 0.0) for e in final_events)
    total_adjustment = max(-0.30, min(0.30, raw_adjustment))

    logger.info(
        f"MERGE: customer={customer_id} "
        f"events={[e['event_type'] for e in final_events]} "
        f"adjustment={total_adjustment:+.2f}"
    )

    return {
        "final_events": final_events,
        "risk_adjustment": total_adjustment,
    }
