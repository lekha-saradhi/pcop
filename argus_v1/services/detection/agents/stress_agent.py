"""
Stress / Overdraft Agent.

Consumes:    pcop.transactions.v1
Method:      CUSUM on monthly overdraft rate + SQL rule on high-risk MCCs.

High-risk MCC whitelist (from doc Appendix B):
    6141 - personal credit / payday lending
    5933 - pawnbrokers
    6051 - quasi-cash (often used for crypto / chit funds)
"""
from datetime import datetime
from typing import Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import CanonicalEvent, SignalResult
from ..methods.cusum import Cusum, CusumState


HIGH_RISK_MCCS = {"6141", "5933", "6051", "7995"}


class StressAgent(BaseAgent):
    signal_type = "stress"
    method_used = "cusum"

    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        if event.event_type != "transaction":
            return None

        payload = event.payload
        customer_id = event.customer_id
        ts = event.event_timestamp
        mcc = str(payload.get("mcc_code") or "")
        balance_after = payload.get("balance_after")
        direction = payload.get("direction")
        amount = float(payload.get("amount", 0))

        # Pull state: monthly bucket for overdraft rate
        state = self.state_store.get("stress", customer_id, "monthly") or {}
        month_key = ts.strftime("%Y-%m")
        if state.get("month") != month_key:
            # New month -> evaluate previous month and reset buckets
            prev_overdraft = state.get("overdraft_count", 0)
            prev_total = state.get("txn_count", 0)
            prev_mcc_hits = state.get("high_risk_mcc_hits", 0)
            prev_rate = prev_overdraft / prev_total if prev_total > 0 else 0.0

            # Carry the rate into CUSUM
            cusum_result = None
            baseline = self.baselines.get(customer_id, "overdraft_rate_monthly")
            if baseline and prev_total >= 5:
                cusum = Cusum(mu_0=baseline.mu_0, sigma=baseline.sigma,
                              k_sigma=0.5, H_sigma=3.0)
                cstate = CusumState(s_plus=state.get("cusum_s_plus", 0.0),
                                    s_minus=state.get("cusum_s_minus", 0.0))
                cusum_result = cusum.update(prev_rate, cstate)
                state["cusum_s_plus"] = cusum_result.s_plus
                state["cusum_s_minus"] = cusum_result.s_minus

            # Reset month buckets
            state["month"] = month_key
            state["overdraft_count"] = 0
            state["txn_count"] = 0
            state["high_risk_mcc_hits"] = 0
            state["last_overdraft_rate"] = prev_rate

            # Emit if overdraft CUSUM upside alarm OR repeated MCC hits
            mcc_alarm = prev_mcc_hits >= 2
            cusum_alarm = bool(cusum_result and cusum_result.alarm
                               and cusum_result.direction == "up")
            if cusum_alarm or mcc_alarm:
                evidence = []
                if cusum_alarm:
                    evidence.append(
                        f"Overdraft rate rose to {prev_rate*100:.1f}% in {state['month']} "
                        f"(baseline {baseline.mu_0*100:.1f}%)"
                    )
                if mcc_alarm:
                    evidence.append(
                        f"{prev_mcc_hits} high-risk MCC transactions detected last month "
                        f"(payday/pawnbroker/quasi-cash)"
                    )
                conf = 0.0
                if cusum_result:
                    conf = max(conf, cusum_result.confidence)
                if mcc_alarm:
                    conf = max(conf, min(0.55 + 0.10 * prev_mcc_hits, 0.90))
                raw = {
                    "month_evaluated": state["month"],
                    "overdraft_rate": round(prev_rate, 4),
                    "overdraft_count": prev_overdraft,
                    "txn_count": prev_total,
                    "high_risk_mcc_hits": prev_mcc_hits,
                }
                self.state_store.set("stress", customer_id, "monthly", state)
                return self._make_result(
                    customer_id=customer_id, detected=True, confidence=conf,
                    evidence=evidence, raw_data=raw,
                    cusum_value=round(state.get("cusum_s_plus", 0.0), 4) if cusum_result else None,
                    alarm_threshold=round(cusum_result.threshold, 4) if cusum_result else None,
                    evaluated_at=ts,
                )

        # Same month: update buckets
        state["month"] = month_key
        state["txn_count"] = state.get("txn_count", 0) + 1
        is_overdraft = (balance_after is not None and float(balance_after) < 0
                        and direction == "debit")
        if is_overdraft:
            state["overdraft_count"] = state.get("overdraft_count", 0) + 1
        if mcc in HIGH_RISK_MCCS and amount > 0:
            state["high_risk_mcc_hits"] = state.get("high_risk_mcc_hits", 0) + 1

        self.state_store.set("stress", customer_id, "monthly", state)
        return None
