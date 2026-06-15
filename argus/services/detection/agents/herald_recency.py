"""Herald Agent 2A-2: Transaction Recency — Survival-Adjusted EWMA.

Correctly handles monthly, weekly, and daily transactors via a
customer-specific exponential inter-arrival distribution.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from services.detection.agents.base_agent import BaseHeraldAgent, SignalResult
from services.detection.methods.sa_ewma import (
    SAEWMAState,
    sa_ewma_alarm,
    sa_ewma_p_value,
    sa_ewma_update,
    survival_percentile,
)

logger = logging.getLogger(__name__)


class HeraldRecencyAgent(BaseHeraldAgent):
    """Transaction recency agent: SA-EWMA on log-survival."""

    signal_type = "sa_ewma_recency"
    method_used = "sa_ewma"

    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate transaction recency signal.

        data keys:
            days_since_last_txn (float): Current gap since last transaction.
            sa_state (SAEWMAState): Persisted SA-EWMA state.
        """
        days: float = data["days_since_last_txn"]
        state: SAEWMAState = data["sa_state"]

        state = sa_ewma_update(state, days)
        alarm = sa_ewma_alarm(state)
        p = sa_ewma_p_value(state)
        pct = survival_percentile(state, days)

        evidence: list[str] = []
        if alarm:
            evidence.append(
                f"Days since last transaction {days:.0f} days, exceeds"
                f" {pct * 100:.0f}th percentile of customer's historical inter-arrival"
            )

        return SignalResult(
            signal_type=self.signal_type,
            detected=alarm,
            confidence=1.0 - p,
            p_value=p,
            evidence=evidence,
            method_used=self.method_used,
            statistic=state.z,
            threshold=state.mu_z + 3.0 * state.sigma_z,
            direction="increase" if alarm else "none",
            baseline_mean=state.mu_z,
            baseline_std=state.sigma_z,
        )
