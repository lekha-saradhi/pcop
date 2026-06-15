"""
Feature Usage Agent (Page-Hinkley).

Consumes:    pcop.app_events.v1   (feature_view / transfer / investment_tab ...)
Method:      Page-Hinkley test on per-feature daily counts.

We maintain ONE Page-Hinkley state per (customer, feature). When a feature
is abandoned (Page-Hinkley T_t > lambda on the negative side), the agent
emits an alarm.
"""
from typing import Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import CanonicalEvent, SignalResult
from ..methods.page_hinkley import PageHinkley, PageHinkleyState


TRACKED_FEATURES = {"investment_tab", "transfer", "credit_card", "loans", "support_chat"}


class FeatureUsageAgent(BaseAgent):
    signal_type = "feature_usage"
    method_used = "page_hinkley"

    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        if event.event_type != "app_event":
            return None
        feature = event.payload.get("feature_name")
        if feature not in TRACKED_FEATURES:
            return None
        if event.payload.get("event_type") != "feature_view":
            return None

        customer_id = event.customer_id
        ts = event.event_timestamp
        day_key = ts.date().isoformat()

        # Bucket by day in state
        state = self.state_store.get("ph", customer_id, f"feature:{feature}") or {}
        daily_counts: dict[str, int] = state.get("daily_counts", {})
        daily_counts[day_key] = daily_counts.get(day_key, 0) + 1

        # Only evaluate when day changes
        last_day = state.get("last_day_evaluated")
        if last_day == day_key:
            state["daily_counts"] = daily_counts
            self.state_store.set("ph", customer_id, f"feature:{feature}", state)
            return None

        # Day rolled: feed previous day's count to Page-Hinkley
        result_emit: Optional[SignalResult] = None
        if last_day and last_day in daily_counts:
            previous_count = float(daily_counts[last_day])
            # NEGATIVE Page-Hinkley: we want to detect ABANDONMENT (drop).
            # So we feed (-x) so a sustained drop becomes an increase in M_t.
            x_input = -previous_count
            ph = PageHinkley(delta=0.01, threshold=50.0)
            ph_state = PageHinkleyState(
                n=state.get("n", 0),
                running_mean=state.get("running_mean", 0.0),
                M_t=state.get("M_t", 0.0),
                M_min=state.get("M_min", 0.0),
            )
            ph_result = ph.update(x_input, ph_state)
            state.update({"n": ph_state.n, "running_mean": ph_state.running_mean,
                          "M_t": ph_state.M_t, "M_min": ph_state.M_min})

            if ph_result.alarm:
                evidence = [
                    f"Feature '{feature}' abandoned: Page-Hinkley T_t = {ph_result.T_t:.2f} "
                    f"> threshold {ph_result.threshold:.2f}",
                    f"Running mean daily count = {ph_result.running_mean:.2f}, "
                    f"latest = {previous_count:.0f}",
                ]
                raw = {
                    "feature": feature,
                    "T_t": round(ph_result.T_t, 4),
                    "threshold": ph_result.threshold,
                    "running_mean": round(ph_result.running_mean, 4),
                    "latest_count": previous_count,
                }
                result_emit = self._make_result(
                    customer_id=customer_id, detected=True, confidence=ph_result.confidence,
                    evidence=evidence, raw_data=raw,
                    cusum_value=round(ph_result.T_t, 4),
                    alarm_threshold=ph_result.threshold,
                    evaluated_at=ts,
                )

        state["last_day_evaluated"] = day_key
        state["daily_counts"] = daily_counts
        self.state_store.set("ph", customer_id, f"feature:{feature}", state)
        return result_emit
