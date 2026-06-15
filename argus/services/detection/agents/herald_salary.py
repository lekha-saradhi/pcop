"""Herald Agent 2A-3: Salary Credit — CUSUM on amount + SR on employer reference string.

Two sub-signals combined: amount shift via CUSUM, employer reference change
via normalised Levenshtein distance fed into SR.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from services.detection.agents.base_agent import BaseHeraldAgent, SignalResult
from services.detection.baseline.tempo import TEMPOState, tempo_update
from services.detection.methods.adaptive_sr import SRState, sr_alarm, sr_p_value, sr_update
from services.detection.methods.cusum import CUSUMState, cusum_alarm, cusum_p_value, cusum_update

logger = logging.getLogger(__name__)

_CUSUM_K = 0.10
_CUSUM_H = 0.30   # relative thresholds (spec: k=0.10, H=0.30 relative)
_EMPLOYER_DIST_THRESHOLD = 0.50
_EMPLOYER_SUSTAINED = 2   # consecutive credits with changed employer ref


def _levenshtein_norm(s1: str, s2: str) -> float:
    """Normalised Levenshtein distance ∈ [0, 1]."""
    s1, s2 = s1.upper().strip(), s2.upper().strip()
    if not s1 and not s2:
        return 0.0
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if s1[i - 1] == s2[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n] / max(m, n)


class HeraldSalaryAgent(BaseHeraldAgent):
    """Salary credit agent: CUSUM on amount + employer reference SR."""

    signal_type = "cusum_salary"
    method_used = "cusum_employer_sr"

    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate salary credit signal.

        data keys:
            salary_amount (float): Latest salary credit amount.
            employer_ref (str): Payment reference string.
            modal_employer_ref (str): Most common employer ref in last 6 months.
            cusum_state (CUSUMState): Persisted CUSUM state.
            sr_state (SRState): Persisted SR state for employer distance.
            tempo_state (TEMPOState): Current TEMPO baseline state.
            employer_dist_history (list[float]): Recent employer distances.
            today (date): Evaluation date.
        """
        amount: float = data["salary_amount"]
        employer_ref: str = data.get("employer_ref", "")
        modal_ref: str = data.get("modal_employer_ref", "")
        cusum: CUSUMState = data["cusum_state"]
        sr_emp: SRState = data["sr_state"]
        tempo: TEMPOState = data["tempo_state"]
        dist_history: list[float] = data.get("employer_dist_history", [])
        today: date = data.get("today", date.today())

        mu = tempo.mu
        sigma = max(tempo.sigma, 1.0)

        cusum = cusum_update(cusum, amount, mu, sigma, k_sigma=_CUSUM_K)
        tempo = tempo_update(tempo, amount, today)

        # Employer reference distance signal
        dist = _levenshtein_norm(employer_ref, modal_ref)
        sr_emp = sr_update(sr_emp, dist, mu=0.05, sigma=0.15)

        cusum_detected = cusum_alarm(cusum, h_sigma=_CUSUM_H, sigma=sigma)
        employer_detected = (
            dist > _EMPLOYER_DIST_THRESHOLD
            and sum(1 for d in dist_history[-_EMPLOYER_SUSTAINED:] if d > _EMPLOYER_DIST_THRESHOLD)
            >= _EMPLOYER_SUSTAINED - 1
        )

        detected = cusum_detected or employer_detected
        p_cusum = cusum_p_value(cusum, _CUSUM_H, sigma, _CUSUM_K)
        p_emp = sr_p_value(sr_emp)
        p_combined = min(p_cusum, p_emp)

        evidence: list[str] = []
        if cusum_detected:
            evidence.append(f"Salary amount CUSUM statistic elevated (shift from baseline ₹{mu:.0f})")
        if employer_detected:
            evidence.append(
                f"Employer reference changed (Levenshtein distance {dist:.2f} > 0.50,"
                f" sustained {_EMPLOYER_SUSTAINED} credits)"
            )

        direction = "decrease" if cusum.s_neg > cusum.s_pos else "increase"

        return SignalResult(
            signal_type=self.signal_type,
            detected=detected,
            confidence=1.0 - p_combined,
            p_value=p_combined,
            evidence=evidence,
            method_used=self.method_used,
            statistic=max(cusum.s_pos, cusum.s_neg),
            threshold=_CUSUM_H * sigma,
            direction=direction if detected else "none",
            baseline_mean=mu,
            baseline_std=sigma,
        )
