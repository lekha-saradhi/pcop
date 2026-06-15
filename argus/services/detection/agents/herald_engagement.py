"""Herald Agent 2A-5: Digital Engagement — Personalised-λ EWMA + STL.

Lambda fitted from customer's AR(1) autocorrelation structure so that
monthly-pattern customers aren't penalised for weekly inactivity.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import numpy as np

from services.detection.agents.base_agent import BaseHeraldAgent, SignalResult
from services.detection.methods.ewma import (
    EWMAState,
    estimate_lambda_from_ar1,
    ewma_alarm,
    ewma_init,
    ewma_p_value,
    ewma_update,
)

logger = logging.getLogger(__name__)

_STL_PERIOD = 7
_L_SIGMA = 3.0


def _seasonal_adjust(values: np.ndarray, period: int = _STL_PERIOD) -> np.ndarray:
    """Remove day-of-week seasonal component."""
    if len(values) < period * 2:
        return values
    out = values.copy().astype(float)
    for dow in range(period):
        idx = np.arange(dow, len(values), period)
        out[idx] -= out[idx].mean()
    return out


def compute_engagement_score(login: bool, session_minutes: float) -> float:
    """Composite engagement score: 0.6 * login_flag + 0.4 * session_ratio."""
    return 0.6 * float(login) + 0.4 * min(session_minutes / 30.0, 1.0)


class HeraldEngagementAgent(BaseHeraldAgent):
    """Digital engagement agent: personalised-λ EWMA on STL residuals."""

    signal_type = "ewma_engagement"
    method_used = "personalised_ewma_stl"

    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate digital engagement signal.

        data keys:
            engagement_history (list[float]): 90+ day engagement score history.
            ewma_state (EWMAState): Persisted EWMA state.
            tempo_mu (float): Current TEMPO baseline mean.
            tempo_sigma (float): Current TEMPO baseline std.
        """
        history: list[float] = data["engagement_history"]
        ewma_state: EWMAState = data["ewma_state"]
        mu: float = data.get("tempo_mu", 0.5)
        sigma: float = max(data.get("tempo_sigma", 0.2), 1e-6)

        arr = np.array(history, dtype=float)
        residuals = _seasonal_adjust(arr)

        for r in residuals:
            ewma_state = ewma_update(ewma_state, r)

        alarm = ewma_alarm(ewma_state)
        p = ewma_p_value(ewma_state, mu, sigma)

        evidence: list[str] = []
        if alarm:
            evidence.append(
                f"Digital engagement EWMA {ewma_state.z:.3f} outside"
                f" control limits [{ewma_state.lcl:.3f}, {ewma_state.ucl:.3f}]"
            )

        direction = "decrease" if ewma_state.z < ewma_state.lcl else "increase"

        return SignalResult(
            signal_type=self.signal_type,
            detected=alarm,
            confidence=1.0 - p,
            p_value=p,
            evidence=evidence,
            method_used=self.method_used,
            statistic=ewma_state.z,
            threshold=ewma_state.ucl,
            direction=direction if alarm else "none",
            baseline_mean=mu,
            baseline_std=sigma,
        )
