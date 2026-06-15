"""Herald Agent 2A-4: Complaint Sentiment + Volume.

Two sub-signals:
  1. Sentiment drift: Beta-CUSUM on logit-transformed LLM sentiment score.
  2. Volume surge: SPRT on Poisson complaint count.

Combined confidence = 1 - (1-c1)(1-c2) (union bound).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from services.detection.agents.base_agent import BaseHeraldAgent, SignalResult
from services.detection.methods.beta_cusum import (
    BetaCUSUMState,
    beta_cusum_alarm,
    beta_cusum_p_value,
    beta_cusum_update,
)
from services.detection.methods.sprt import SPRTState, sprt_alarm, sprt_p_value, sprt_update

logger = logging.getLogger(__name__)


class HeraldSentimentAgent(BaseHeraldAgent):
    """Complaint sentiment + volume agent."""

    signal_type = "beta_cusum_sentiment"
    method_used = "beta_cusum_sprt"

    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate complaint sentiment and volume signals.

        data keys:
            sentiment_score (float): LLM output ∈ [-1, +1].
            complaint_count (int): Complaint count in current period.
            beta_cusum_state (BetaCUSUMState): Persisted Beta-CUSUM state.
            sprt_state (SPRTState): Persisted SPRT state.
            lambda0 (float): Baseline Poisson complaint rate.
            lambda1 (float): Alternative (surge) Poisson complaint rate.
        """
        sentiment: float = data["sentiment_score"]
        count: int = data.get("complaint_count", 0)
        beta_state: BetaCUSUMState = data["beta_cusum_state"]
        sprt_state: SPRTState = data["sprt_state"]
        lambda0: float = data.get("lambda0", 0.5)
        lambda1: float = data.get("lambda1", 2.0)

        beta_state = beta_cusum_update(beta_state, sentiment)
        sprt_state = sprt_update(sprt_state, count, lambda0, lambda1)

        sent_detected = beta_cusum_alarm(beta_state)
        vol_detected = sprt_alarm(sprt_state)

        p_sent = beta_cusum_p_value(beta_state)
        p_vol = sprt_p_value(sprt_state)

        # Union bound: P(at least one) = 1 - (1-c1)(1-c2)
        detected = sent_detected or vol_detected
        c1, c2 = 1.0 - p_sent, 1.0 - p_vol
        confidence = 1.0 - (1.0 - c1) * (1.0 - c2)
        p_combined = 1.0 - confidence

        evidence: list[str] = []
        if sent_detected:
            evidence.append(
                f"Complaint sentiment trend negative (Beta-CUSUM stat"
                f" {max(beta_state.s_pos, beta_state.s_neg):.2f})"
            )
        if vol_detected:
            evidence.append(
                f"Complaint volume surge detected (SPRT log-LR"
                f" {sprt_state.log_lr:.2f}, n={sprt_state.n})"
            )

        return SignalResult(
            signal_type=self.signal_type,
            detected=detected,
            confidence=confidence,
            p_value=p_combined,
            evidence=evidence,
            method_used=self.method_used,
            statistic=max(beta_state.s_pos, beta_state.s_neg),
            threshold=4.0 * beta_state.sigma_y,
            direction="decrease" if beta_state.s_pos > beta_state.s_neg else "increase",
            baseline_mean=0.0,
            baseline_std=beta_state.sigma_y,
        )
