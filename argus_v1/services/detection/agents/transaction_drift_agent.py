"""
Transaction Drift Agent.

Consumes:    pcop.transactions.v1
Method:      Daily aggregation -> STL(period=7) -> CUSUM on residuals.

This is run as a daily batch over each customer's last 60-day txn count
series. STL removes day-of-week / month seasonality so the CUSUM does
not false-alarm on weekends or paydays.

Falls back to plain CUSUM when statsmodels is not available.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import CanonicalEvent, SignalResult
from ..methods.cusum import Cusum, CusumState

try:
    from ..methods.stl_cusum import StlCusum
    import pandas as pd
    _HAS_STL = True
except Exception:  # pragma: no cover
    _HAS_STL = False


class TransactionDriftAgent(BaseAgent):
    signal_type = "transaction_freq"
    method_used = "stl_cusum"

    WINDOW_DAYS = 60
    STL_PERIOD = 7

    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        # We expect a "daily_aggregator" pseudo-event with payload.daily_count_series
        # for the customer's trailing window, OR raw transaction events that we will
        # bucket internally. Here we handle the aggregator-event case as primary.
        payload = event.payload
        if event.event_type != "daily_aggregator":
            # For raw txns, we just accumulate counts in Redis; emit nothing.
            self._accumulate_raw_txn(event)
            return None

        customer_id = event.customer_id
        series: list[dict] = payload.get("daily_count_series", [])
        if len(series) < self.STL_PERIOD * 2:
            return None

        baseline = self.baselines.get(customer_id, "transaction_frequency_daily")
        if baseline is None:
            return None

        state_dict = self.state_store.get("cusum", customer_id, "txn_freq") or {}
        state = CusumState(s_plus=state_dict.get("s_plus", 0.0),
                           s_minus=state_dict.get("s_minus", 0.0))

        if _HAS_STL:
            idx = pd.to_datetime([row["date"] for row in series])
            counts = pd.Series([row["count"] for row in series], index=idx).asfreq("D").fillna(0)
            stl = StlCusum(mu_0=0.0, sigma=baseline.sigma,
                           period=self.STL_PERIOD, k_sigma=0.5, H_sigma=4.0)
            stl_res = stl.step(counts, state)
            residual = stl_res.residual
            cresult = stl_res.cusum
        else:
            latest = float(series[-1]["count"])
            cusum = Cusum(mu_0=baseline.mu_0, sigma=baseline.sigma, k_sigma=0.5, H_sigma=4.0)
            cresult = cusum.update(latest, state)
            residual = latest - baseline.mu_0

        ts = event.event_timestamp
        self.state_store.set("cusum", customer_id, "txn_freq", {
            "s_plus": cresult.s_plus,
            "s_minus": cresult.s_minus,
            "last_update": ts.isoformat(),
        })

        if not cresult.alarm:
            return None

        direction = "decline" if cresult.direction == "down" else "increase"
        evidence = [
            f"Sustained transaction {direction} detected by STL+CUSUM",
            f"Latest residual = {residual:+.2f}; CUSUM stat "
            f"{max(cresult.s_plus, cresult.s_minus):.2f} vs threshold {cresult.threshold:.2f}",
        ]
        raw = {
            "window_days": len(series),
            "baseline_daily_count": baseline.mu_0,
            "baseline_sigma": baseline.sigma,
            "latest_residual": round(residual, 4),
            "direction": cresult.direction,
        }
        return self._make_result(
            customer_id=customer_id, detected=True, confidence=cresult.confidence,
            evidence=evidence, raw_data=raw,
            cusum_value=round(max(cresult.s_plus, cresult.s_minus), 4),
            alarm_threshold=round(cresult.threshold, 4),
            evaluated_at=ts,
        )

    # --- helper for raw event accumulation (write-through bucket) ---
    def _accumulate_raw_txn(self, event: CanonicalEvent) -> None:
        ts = event.event_timestamp
        key_day = ts.date().isoformat()
        state = self.state_store.get("agg", event.customer_id, "txn_freq") or {}
        daily = state.get("daily", {})
        daily[key_day] = daily.get(key_day, 0) + 1
        # keep last WINDOW_DAYS keys
        if len(daily) > self.WINDOW_DAYS:
            cutoff = (ts.date() - timedelta(days=self.WINDOW_DAYS)).isoformat()
            daily = {d: c for d, c in daily.items() if d >= cutoff}
        state["daily"] = daily
        self.state_store.set("agg", event.customer_id, "txn_freq", state)
