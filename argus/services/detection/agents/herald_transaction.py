"""Herald Agent 2A-1: Transaction Frequency — Adaptive SR + STL seasonal adjustment.

Uses Shiryaev-Roberts instead of CUSUM: SR is minimax-optimal for detecting
changes at unknown magnitude, which matches the gradual churn profile.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import numpy as np

from services.detection.agents.base_agent import BaseHeraldAgent, SignalResult
from services.detection.baseline.tempo import TEMPOState, tempo_update
from services.detection.methods.adaptive_sr import SRState, sr_alarm, sr_p_value, sr_update

logger = logging.getLogger(__name__)

_SR_THRESHOLD = 100.0   # calibrated for ARL0 ≈ 500 at 0.5σ shift
_STL_PERIOD = 7         # 7-day seasonal period


def _seasonal_adjust(values: np.ndarray) -> np.ndarray:
    """Remove 7-day seasonal component via period-mean subtraction."""
    if len(values) < _STL_PERIOD * 2:
        return values
    residuals = values.copy().astype(float)
    for dow in range(_STL_PERIOD):
        idx = np.arange(dow, len(values), _STL_PERIOD)
        residuals[idx] -= residuals[idx].mean()
    return residuals


class HeraldTransactionAgent(BaseHeraldAgent):
    """Transaction frequency agent: Adaptive SR on STL residuals."""

    signal_type = "sr_transaction"
    method_used = "adaptive_sr"

    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate transaction frequency signal.

        data keys:
            history (list[float]): Daily transaction counts (≥14 days).
            tempo_state (TEMPOState): Current TEMPO baseline state.
            sr_state (SRState): Persisted SR state across calls.
            today (date): Evaluation date.
        """
        history: list[float] = data["history"]
        tempo: TEMPOState = data["tempo_state"]
        sr: SRState = data["sr_state"]
        today: date = data.get("today", date.today())

        arr = np.array(history, dtype=float)
        residuals = _seasonal_adjust(arr)

        mu = tempo.mu
        sigma = max(tempo.sigma, 1e-6)

        for r in residuals:
            sr = sr_update(sr, r, mu, sigma)
            tempo = tempo_update(tempo, r, today)

        alarm = sr_alarm(sr, _SR_THRESHOLD)
        p = sr_p_value(sr)

        direction = "decrease" if sr.r_neg > sr.r_pos else "increase"
        stat = max(sr.r_pos, sr.r_neg)

        evidence: list[str] = []
        if alarm:
            pct = int((1.0 - p) * 100)
            evidence.append(
                f"Transaction frequency SR statistic {stat:.1f} > threshold {_SR_THRESHOLD};"
                f" {pct}th percentile anomaly"
            )

        return SignalResult(
            signal_type=self.signal_type,
            detected=alarm,
            confidence=1.0 - p,
            p_value=p,
            evidence=evidence,
            method_used=self.method_used,
            statistic=stat,
            threshold=_SR_THRESHOLD,
            direction=direction if alarm else "none",
            baseline_mean=mu,
            baseline_std=sigma,
        )
