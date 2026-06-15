"""Two-sided CUSUM control chart."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class CUSUMState:
    s_pos: float = 0.0
    s_neg: float = 0.0


def cusum_update(state: CUSUMState, x: float, mu: float, sigma: float, k_sigma: float = 0.5) -> CUSUMState:
    """Update CUSUM statistics with a new observation.

    k_sigma: allowance as fraction of sigma (0.5 detects 1-sigma shifts optimally).
    """
    k = k_sigma * sigma
    state.s_pos = max(0.0, state.s_pos + (x - mu) - k)
    state.s_neg = max(0.0, state.s_neg - (x - mu) - k)
    return state


def cusum_alarm(state: CUSUMState, h_sigma: float, sigma: float) -> bool:
    """True when CUSUM statistic exceeds h_sigma * sigma."""
    h = h_sigma * sigma
    return max(state.s_pos, state.s_neg) > h


def cusum_p_value(state: CUSUMState, h_sigma: float, sigma: float, k_sigma: float = 0.5) -> float:
    """Approximate p-value: exp(-2 * stat * k) using optimal stopping approximation."""
    stat = max(state.s_pos, state.s_neg)
    if stat <= 0.0:
        return 1.0
    h = h_sigma * sigma
    k = k_sigma * sigma
    # Approximate: P(S > s) ~ exp(-2*s*k/sigma^2) → normalized to [0,1]
    exponent = 2.0 * stat * k / (sigma ** 2)
    return float(math.exp(-exponent))


def cusum_reset(state: CUSUMState) -> CUSUMState:
    state.s_pos = 0.0
    state.s_neg = 0.0
    return state
