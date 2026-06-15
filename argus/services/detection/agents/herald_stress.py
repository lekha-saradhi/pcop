"""Herald Agent 2A-6: Financial Stress — CUSUM on Composite Financial Stress Index.

Sensitive to early financial stress that doesn't yet show in overdraft alone,
e.g. ATM cash + payday MCC spend before the first overdraft event.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from services.detection.agents.base_agent import BaseHeraldAgent, SignalResult
from services.detection.baseline.tempo import TEMPOState, tempo_update
from services.detection.methods.cfsi import CFSIComponents, cfsi_evidence, compute_cfsi
from services.detection.methods.cusum import CUSUMState, cusum_alarm, cusum_p_value, cusum_update

logger = logging.getLogger(__name__)

_CUSUM_K = 0.5   # 0.5σ allowance
_CUSUM_H = 4.0   # 4σ threshold


class HeraldStressAgent(BaseHeraldAgent):
    """Financial stress agent: CUSUM on CFSI composite index."""

    signal_type = "cfsi_stress"
    method_used = "cfsi_cusum"

    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate financial stress signal.

        data keys:
            components (CFSIComponents): Five stress component values.
            cusum_state (CUSUMState): Persisted CUSUM state.
            tempo_state (TEMPOState): TEMPO baseline (for CFSI baseline mean/std).
            today (date): Evaluation date.
        """
        components: CFSIComponents = data["components"]
        cusum: CUSUMState = data["cusum_state"]
        tempo: TEMPOState = data["tempo_state"]
        today: date = data.get("today", date.today())

        cfsi = compute_cfsi(components)
        mu = tempo.mu
        sigma = max(tempo.sigma, 0.01)

        cusum = cusum_update(cusum, cfsi, mu, sigma, k_sigma=_CUSUM_K)
        tempo = tempo_update(tempo, cfsi, today)

        alarm = cusum_alarm(cusum, h_sigma=_CUSUM_H, sigma=sigma)
        p = cusum_p_value(cusum, _CUSUM_H, sigma, _CUSUM_K)

        evidence = cfsi_evidence(components, cfsi) if alarm else []

        return SignalResult(
            signal_type=self.signal_type,
            detected=alarm,
            confidence=1.0 - p,
            p_value=p,
            evidence=evidence,
            method_used=self.method_used,
            statistic=max(cusum.s_pos, cusum.s_neg),
            threshold=_CUSUM_H * sigma,
            direction="increase",
            baseline_mean=mu,
            baseline_std=sigma,
        )
