"""Adaptive Shiryaev-Roberts (SR) procedure for changepoint detection.

SR is minimax-optimal for detecting changes of unknown magnitude — ideal
for gradual churn where the shift size is uncertain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class SRState:
    r_pos: float = 0.0   # statistic for upward shift
    r_neg: float = 0.0   # statistic for downward shift


def sr_update(state: SRState, x: float, mu: float, sigma: float, delta_sigma: float = 0.5) -> SRState:
    """Update SR statistics with a new observation (Gaussian model).

    delta_sigma: detection target as fraction of sigma (0.5 = half-sigma shift).
    """
    delta = delta_sigma * sigma
    sigma2 = sigma ** 2

    # Log-likelihood ratio for upward shift mu + delta vs mu
    log_lr_pos = delta * (x - mu) / sigma2 - delta ** 2 / (2.0 * sigma2)
    # Log-likelihood ratio for downward shift mu - delta vs mu
    log_lr_neg = -delta * (x - mu) / sigma2 - delta ** 2 / (2.0 * sigma2)

    state.r_pos = (state.r_pos + 1.0) * math.exp(log_lr_pos)
    state.r_neg = (state.r_neg + 1.0) * math.exp(log_lr_neg)
    return state


def sr_alarm(state: SRState, threshold: float = 100.0) -> bool:
    """True when SR statistic exceeds the control limit.

    Default threshold ≈ ARL0 500 for 0.5-sigma Gaussian shift.
    """
    return max(state.r_pos, state.r_neg) > threshold


def sr_p_value(state: SRState) -> float:
    """Approximate p-value using Wald approximation: P(R > r | H0) ≈ 1/(1+r)."""
    r = max(state.r_pos, state.r_neg)
    return 1.0 / (1.0 + r)


def sr_reset(state: SRState) -> SRState:
    state.r_pos = 0.0
    state.r_neg = 0.0
    return state
