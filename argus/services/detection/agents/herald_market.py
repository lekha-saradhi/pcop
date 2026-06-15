"""Herald Agent 2A-9: Market / Competitive Signals — Rate Change Index (RCI).

Pure statistical, deterministic — no LLM calls in ARGUS Layer 2.
LLM context-enrichment happens in Layer 4 after ARGUS flags the rate delta.

RCI = max competitor savings rate - PCOP savings rate.
Fires at PORTFOLIO level; individual applicability resolved by Layer 4.
"""

from __future__ import annotations

import logging
from typing import Any

from services.detection.agents.base_agent import BaseHeraldAgent, SignalResult

logger = logging.getLogger(__name__)

# Thresholds in basis points (bps)
_LOW_BPS = 50
_MEDIUM_BPS = 100
_HIGH_BPS = 150


class HeraldMarketAgent(BaseHeraldAgent):
    """Market competitive rate signal agent: Rate Change Index."""

    signal_type = "rci_market"
    method_used = "rate_change_index"

    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate market rate signal.

        data keys:
            pcop_savings_rate (float): Current PCOP savings rate in %.
            competitor_rates (dict[str, float]): {bank_name: savings_rate} mapping.
        """
        pcop_rate: float = data.get("pcop_savings_rate", 0.0)
        competitor_rates: dict[str, float] = data.get("competitor_rates", {})

        if not competitor_rates:
            return SignalResult(
                signal_type=self.signal_type,
                detected=False,
                confidence=0.0,
                p_value=1.0,
                evidence=[],
                method_used=self.method_used,
                statistic=0.0,
                threshold=_LOW_BPS / 100.0,
                direction="none",
                baseline_mean=pcop_rate,
                baseline_std=0.0,
            )

        best_competitor = max(competitor_rates, key=lambda k: competitor_rates[k])
        best_rate = competitor_rates[best_competitor]
        rci_pct = best_rate - pcop_rate
        rci_bps = rci_pct * 100.0

        if rci_bps > _HIGH_BPS:
            severity = "HIGH"
            confidence = 0.95
        elif rci_bps > _MEDIUM_BPS:
            severity = "MEDIUM"
            confidence = 0.75
        elif rci_bps > _LOW_BPS:
            severity = "LOW"
            confidence = 0.50
        else:
            severity = "NONE"
            confidence = 0.0

        detected = rci_bps > _LOW_BPS
        p_value = 1.0 - confidence

        evidence: list[str] = []
        if detected:
            evidence.append(
                f"RCI={rci_bps:.0f} bps: {best_competitor} offers {best_rate:.2f}%"
                f" vs PCOP {pcop_rate:.2f}% — severity {severity}"
            )

        return SignalResult(
            signal_type=self.signal_type,
            detected=detected,
            confidence=confidence,
            p_value=p_value,
            evidence=evidence,
            method_used=self.method_used,
            statistic=rci_bps,
            threshold=float(_LOW_BPS),
            direction="increase" if detected else "none",
            baseline_mean=pcop_rate,
            baseline_std=0.0,
        )
