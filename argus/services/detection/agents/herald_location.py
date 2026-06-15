"""Herald Agent 2A-7: Location / Relocation.

Amount-weighted city frequency + international signal. Prevents conference-
trip false alarms (low-value retail) while reliably detecting genuine
relocations (high-value rent/grocery/utility transactions).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from services.detection.agents.base_agent import BaseHeraldAgent, SignalResult

logger = logging.getLogger(__name__)

_CITY_SCORE_THRESHOLD = 0.60   # fraction of spend in new city
_DAYS_SUSTAINED = 14           # minimum days in new city
_INTL_FRACTION_THRESHOLD = 0.40  # fraction of transactions international
_MCC_REMITTANCE = 6099

# MCC 6099 (remittance) alongside new domestic city boosts confidence
_REMITTANCE_BOOST = 0.15


class HeraldLocationAgent(BaseHeraldAgent):
    """Location/relocation agent: amount-weighted city frequency."""

    signal_type = "location_rule"
    method_used = "amount_weighted_location"

    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate location / relocation signal.

        data keys:
            city_transactions (list[dict]): Each dict has 'city', 'amount', 'is_new_city', 'date'.
            home_city (str): Customer's registered home city.
            intl_fraction (float): Fraction of transactions international in 30 days.
            has_remittance_mcc (bool): True if MCC 6099 present alongside new city.
        """
        txns: list[dict] = data.get("city_transactions", [])
        intl_fraction: float = data.get("intl_fraction", 0.0)
        has_remittance: bool = data.get("has_remittance_mcc", False)

        # Amount-weighted new-city score
        total_amount = sum(t["amount"] for t in txns) or 1.0
        new_city_amount = sum(t["amount"] for t in txns if t.get("is_new_city", False))
        city_score = new_city_amount / total_amount

        # Days sustained in new city
        new_city_dates: set = {t["date"] for t in txns if t.get("is_new_city", False)}
        if new_city_dates:
            span = (max(new_city_dates) - min(new_city_dates)).days + 1
        else:
            span = 0

        domestic_detected = city_score >= _CITY_SCORE_THRESHOLD and span >= _DAYS_SUSTAINED
        intl_detected = intl_fraction >= _INTL_FRACTION_THRESHOLD

        detected = domestic_detected or intl_detected
        confidence = 0.0

        evidence: list[str] = []
        if domestic_detected:
            confidence = min(city_score, 0.90)
            if has_remittance:
                confidence = min(confidence + _REMITTANCE_BOOST, 1.0)
                evidence.append("Remittance MCC 6099 corroborates domestic relocation")
            evidence.append(
                f"New-city amount share {city_score * 100:.0f}% (>{_CITY_SCORE_THRESHOLD * 100:.0f}%)"
                f" sustained {span} days"
            )
        if intl_detected:
            confidence = max(confidence, 0.90)
            evidence.append(
                f"International transaction dominance: {intl_fraction * 100:.0f}% of spend"
            )

        p_value = 1.0 - confidence if detected else 1.0

        return SignalResult(
            signal_type=self.signal_type,
            detected=detected,
            confidence=confidence,
            p_value=p_value,
            evidence=evidence,
            method_used=self.method_used,
            statistic=city_score,
            threshold=_CITY_SCORE_THRESHOLD,
            direction="increase",
            baseline_mean=0.0,
            baseline_std=0.0,
        )
