"""Composite Financial Stress Index (CFSI) construction and CUSUM detection.

CFSI aggregates 5 normalised stress components; CUSUM on the index is more
sensitive to early financial stress than monitoring overdraft rate alone.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from services.detection.methods.cusum import CUSUMState, cusum_alarm, cusum_p_value, cusum_update


# MCC codes flagged as high-risk (money transfers, payday lending, etc.)
HIGH_RISK_MCC: frozenset[int] = frozenset({6141, 6099, 6051, 6012, 7299})

WEIGHTS = {
    "overdraft_freq": 0.30,
    "high_risk_mcc":  0.25,
    "balance_min":    0.20,
    "late_payment":   0.15,
    "atm_ratio":      0.10,
}


@dataclass
class CFSIComponents:
    overdraft_freq: float      # normalised overdraft events (0–1)
    high_risk_mcc_ratio: float # high-risk MCC spend / total spend (0–1)
    balance_min_ratio: float   # monthly min / monthly avg balance (0–1)
    late_payment: float        # 1 if any EMI > 3 days late, else 0
    atm_ratio: float           # ATM cash withdrawal / total transactions (0–1)


def compute_cfsi(components: CFSIComponents) -> float:
    """Return CFSI ∈ [0,1]; higher = more financial stress."""
    stress_balance = 1.0 - min(1.0, max(0.0, components.balance_min_ratio))
    cfsi = (
        WEIGHTS["overdraft_freq"]  * components.overdraft_freq
        + WEIGHTS["high_risk_mcc"] * components.high_risk_mcc_ratio
        + WEIGHTS["balance_min"]   * stress_balance
        + WEIGHTS["late_payment"]  * components.late_payment
        + WEIGHTS["atm_ratio"]     * components.atm_ratio
    )
    return float(np.clip(cfsi, 0.0, 1.0))


def cfsi_evidence(components: CFSIComponents, cfsi: float) -> list[str]:
    """Return human-readable evidence strings for the CFSI alarm."""
    items = []
    if components.overdraft_freq > 0.4:
        items.append(f"Overdraft frequency elevated (c1={components.overdraft_freq:.2f})")
    if components.high_risk_mcc_ratio > 0.3:
        items.append(f"High-risk MCC spend ratio above baseline (c2={components.high_risk_mcc_ratio:.2f})")
    if components.balance_min_ratio < 0.2:
        items.append(f"Balance minimum critically low (c3={components.balance_min_ratio:.2f})")
    if components.late_payment > 0:
        items.append("Late EMI payment detected (c4=1.0)")
    if components.atm_ratio > 0.4:
        items.append(f"ATM cash withdrawal ratio elevated (c5={components.atm_ratio:.2f})")
    if not items:
        items.append(f"CFSI={cfsi:.3f} elevated above baseline")
    return items
