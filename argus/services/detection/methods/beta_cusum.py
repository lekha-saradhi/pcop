"""Beta-CUSUM for bounded continuous signals (complaint sentiment).

Applies logit transform to map sentiment ∈ [-1,+1] → R, then
runs standard two-sided CUSUM on the transformed values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy import stats


@dataclass
class BetaCUSUMState:
    s_pos: float = 0.0
    s_neg: float = 0.0
    sigma_y: float = 1.0   # std of logit-transformed baseline signal


def _logit_transform(sentiment_score: float, eps: float = 1e-6) -> float:
    """Map sentiment ∈ [-1,+1] to R via logit of (score+1)/2."""
    p = (sentiment_score + 1.0) / 2.0
    p = max(eps, min(1.0 - eps, p))
    return math.log(p / (1.0 - p))


def beta_cusum_update(
    state: BetaCUSUMState,
    sentiment_score: float,
    mu0_y: float = 0.0,
    k_sigma: float = 0.25,
) -> BetaCUSUMState:
    """Update Beta-CUSUM with a new sentiment observation.

    mu0_y: baseline logit mean (0.0 = neutral, logit(0.5) = 0).
    k_sigma: allowance as fraction of sigma_y (0.25 detects 0.5-sigma sentiment shifts).
    """
    y = _logit_transform(sentiment_score)
    k = k_sigma * state.sigma_y
    state.s_pos = max(0.0, state.s_pos + (y - mu0_y) - k)
    state.s_neg = max(0.0, state.s_neg - (y - mu0_y) - k)
    return state


def beta_cusum_alarm(state: BetaCUSUMState, h_sigma: float = 4.0) -> bool:
    h = h_sigma * state.sigma_y
    return max(state.s_pos, state.s_neg) > h


def beta_cusum_p_value(state: BetaCUSUMState, k_sigma: float = 0.25) -> float:
    stat = max(state.s_pos, state.s_neg)
    if stat <= 0.0:
        return 1.0
    k = k_sigma * state.sigma_y
    exponent = 2.0 * stat * k / (state.sigma_y ** 2)
    return float(math.exp(-exponent))


def beta_cusum_reset(state: BetaCUSUMState) -> BetaCUSUMState:
    state.s_pos = 0.0
    state.s_neg = 0.0
    return state
