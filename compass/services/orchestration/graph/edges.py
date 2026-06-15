from ..state import CompassState


def route_after_intake(state: CompassState) -> str:
    signals = state.get("signal_results", [])

    if not signals:
        return "verify"

    ambiguous = [s for s in signals if (s.get("confidence") or 0) < 0.80 and s.get("detected")]
    high_conf = [s for s in signals if (s.get("confidence") or 0) >= 0.80 and s.get("detected")]

    if ambiguous:
        return "cognition"
    elif high_conf:
        return "verify"
    else:
        return "verify"


def route_after_gate(state: CompassState) -> str:
    action_plan = state.get("action_plan", {})

    if action_plan and action_plan.get("suppressed", False):
        return "suppressed"
    return "dispatch"
