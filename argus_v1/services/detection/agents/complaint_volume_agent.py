"""
Complaint Volume Agent.

Consumes:    pcop.complaints.v1   (monthly count aggregator events)
Method:      SPRT (Poisson) -- optimal for detecting Poisson rate shifts.
             H0: rate = baseline_lambda_0
             H1: rate = 2 * baseline_lambda_0  (doc default)
             alpha = 0.01, beta = 0.10
"""
from typing import Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import CanonicalEvent, SignalResult
from ..methods.sprt import SprtPoisson, SprtState


class ComplaintVolumeAgent(BaseAgent):
    signal_type = "complaint_volume"
    method_used = "sprt"

    EVENT_TYPE = "complaint_count_window"

    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        if event.event_type != self.EVENT_TYPE:
            return None

        payload = event.payload
        observed = float(payload["complaint_count"])
        lambda_0 = float(payload.get("baseline_lambda_0")
                         or (self.baselines.get(event.customer_id, "complaint_count_monthly")
                             or _Default()).lambda_0
                         or 0.3)
        lambda_1 = 2.0 * lambda_0

        sprt = SprtPoisson(lambda_0=lambda_0, lambda_1=lambda_1, alpha=0.01, beta=0.10)
        state_dict = self.state_store.get("sprt", event.customer_id, "complaints") or {}
        state = SprtState(lambda_t=state_dict.get("lambda_t", 0.0))
        result = sprt.update(observed, state, reset_on_decision=False)

        self.state_store.set("sprt", event.customer_id, "complaints", {
            "lambda_t": result.lambda_t,
            "decision": result.decision,
            "last_update": event.event_timestamp.isoformat(),
        })

        if not result.alarm:
            return None

        evidence = [
            f"Monthly complaint count = {int(observed)} vs baseline λ₀={lambda_0}",
            "SPRT log-likelihood ratio crossed upper bound B",
            f"H1 (λ₁={lambda_1:.2f}={2}×λ₀) accepted",
        ]
        raw = {
            "observed_count": observed,
            "baseline_lambda_0": lambda_0,
            "alternative_lambda_1": lambda_1,
            "lambda_t": round(result.lambda_t, 4),
            "upper_bound_B": round(result.upper_bound, 4),
            "lower_bound_A": round(result.lower_bound, 4),
            "alpha": 0.01,
            "beta": 0.10,
        }
        return self._make_result(
            customer_id=event.customer_id,
            detected=True,
            confidence=result.confidence,
            evidence=evidence, raw_data=raw,
            cusum_value=round(result.lambda_t, 4),
            alarm_threshold=round(result.upper_bound, 4),
            evaluated_at=event.event_timestamp,
        )


class _Default:
    lambda_0 = 0.3
