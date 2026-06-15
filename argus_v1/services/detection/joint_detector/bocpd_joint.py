"""
BOCPD Joint Detector.

This is NOT a per-event Kafka consumer. It is invoked periodically (e.g.
every 2 hours by the scheduler) for each customer where >= 2 individual
CUSUM statistics are between 50% and 100% of their alarm thresholds.

Input:
    SignalResults for all per-signal agents in the lookback window.
Output:
    A `bocpd_joint` SignalResult if the joint changepoint probability
    crosses the alarm threshold.

Joint statistic fed to BOCPD: weighted average of CUSUM ratios across
all currently-active sub-threshold signals.
"""
from datetime import datetime, timezone
from typing import Iterable, Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import SignalResult
from ..methods.bocpd import Bocpd, BocpdState


class BocpdJointDetector(BaseAgent):
    signal_type = "bocpd_joint"
    method_used = "bocpd"

    LOWER_RATIO = 0.50
    UPPER_RATIO = 1.00
    HAZARD = 1.0 / 200.0
    ALARM_PROB = 0.60

    SUB_SIGNAL_TYPES = {
        "salary", "complaint_sentiment", "engagement",
        "transaction_freq", "stress", "feature_usage",
    }

    # In-control prior history used to pre-warm BOCPD on first evaluation
    # so the run-length posterior has had time to stabilise. Each value
    # represents a "no co-active signals" joint score.
    PREWARM_HISTORY = [0.18, 0.22, 0.19, 0.21, 0.17, 0.23, 0.20,
                       0.18, 0.21, 0.19, 0.22, 0.20, 0.18, 0.21,
                       0.19, 0.20, 0.22, 0.18, 0.21, 0.19]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Diffuse prior is fine; pre-warm history gives the run-length
        # posterior something to compare new observations against.
        self.bocpd = Bocpd(hazard=self.HAZARD, alarm_prob=self.ALARM_PROB,
                           prior_mu=0.20, prior_kappa=1.0,
                           prior_alpha=2.0, prior_beta=0.02)

    def _maybe_prewarm(self, customer_id: str, state_dict) -> "BocpdState":
        from ..methods.bocpd import BocpdState
        if state_dict:
            return BocpdState(**state_dict)
        # First evaluation: replay synthetic in-control history so the
        # run-length posterior is calibrated when the real value arrives.
        state = self.bocpd.init_state()
        for x in self.PREWARM_HISTORY:
            self.bocpd.update(x, state)
        return state

    def process_event(self, event):
        # Not driven by events; use evaluate_customer() instead.
        return None

    def evaluate_customer(self, customer_id: str,
                          recent_signal_results: Iterable[SignalResult],
                          now: Optional[datetime] = None) -> Optional[SignalResult]:
        ts = now or datetime.now(timezone.utc)

        # Pick the most-recent sub-threshold ratio for each tracked signal type
        ratios: dict[str, float] = {}
        for r in recent_signal_results:
            if r.signal_type not in self.SUB_SIGNAL_TYPES:
                continue
            if r.cusum_value is None or r.alarm_threshold in (None, 0):
                continue
            ratio = r.cusum_value / r.alarm_threshold
            if self.LOWER_RATIO <= ratio <= self.UPPER_RATIO:
                # Keep latest only (assumes input list is in chronological order)
                ratios[r.signal_type] = ratio

        if len(ratios) < 2:
            return None  # Need at least 2 co-active signals

        joint_score = sum(ratios.values()) / len(ratios)

        # Load/update BOCPD state (pre-warm if first call)
        state_dict = self.state_store.get("bocpd", customer_id, "joint")
        state = self._maybe_prewarm(customer_id, state_dict)

        result = self.bocpd.update(joint_score, state)

        # Persist (cap stored hypotheses to a reasonable depth)
        self.state_store.set("bocpd", customer_id, "joint", {
            "run_length_probs": state.run_length_probs[:50],
            "mu": state.mu[:50],
            "kappa": state.kappa[:50],
            "alpha": state.alpha[:50],
            "beta": state.beta[:50],
            "t": state.t,
        })

        if not result.alarm:
            return None

        signals_involved = sorted(ratios.keys())
        evidence = [
            f"Joint changepoint probability P(r_t=0) = {result.changepoint_probability:.2f} "
            f"> threshold {self.ALARM_PROB:.2f}",
            f"{len(ratios)} signals co-active at 50-100% of individual thresholds",
            "Coordinated regime shift detected across signal space",
        ]
        raw = {
            "changepoint_probability": round(result.changepoint_probability, 4),
            "signals_involved": signals_involved,
            "individual_cusum_ratios": {k: round(v, 4) for k, v in ratios.items()},
            "hazard_lambda": self.HAZARD,
            "run_length_mode": result.most_likely_run_length,
            "joint_score": round(joint_score, 4),
        }
        return self._make_result(
            customer_id=customer_id, detected=True,
            confidence=result.changepoint_probability,
            evidence=evidence, raw_data=raw,
            cusum_value=None, alarm_threshold=self.ALARM_PROB,
            evaluated_at=ts,
        )
