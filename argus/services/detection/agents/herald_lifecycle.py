"""Herald Agent 2A-8: Lifecycle Events — MCC temporal cluster scoring.

Cluster of 3+ related MCCs in a 30-day window provides high-confidence
lifecycle event detection vs. single-MCC whitelist approaches.
"""

from __future__ import annotations

import logging
from typing import Any

from services.detection.agents.base_agent import BaseHeraldAgent, SignalResult
from services.detection.methods.mcc_cluster import LifecycleEvent, MCCClusterResult, score_mcc_cluster

logger = logging.getLogger(__name__)


class HeraldLifecycleAgent(BaseHeraldAgent):
    """Lifecycle event agent: MCC cluster scoring."""

    signal_type = "lifecycle_mcc"
    method_used = "mcc_cluster"

    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate lifecycle event signal.

        data keys:
            mccs_30d (set[int] | list[int]): MCC codes seen in last 30 days.
        """
        mccs: set[int] = set(data.get("mccs_30d", []))

        result: MCCClusterResult = score_mcc_cluster(mccs)

        p_value = 1.0 - result.confidence if result.detected else 1.0

        return SignalResult(
            signal_type=self.signal_type,
            detected=result.detected,
            confidence=result.confidence,
            p_value=p_value,
            evidence=result.evidence,
            method_used=self.method_used,
            statistic=result.score,
            threshold=0.70,
            direction="increase",
            baseline_mean=0.0,
            baseline_std=0.0,
        )
