"""EWMA (Exponentially Weighted Moving Average) control chart.

Supports personalised lambda fitted from individual AR(1) autocorrelation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class EWMAState:
    z: float           # current EWMA value
    lam: float         # smoothing parameter lambda
    ucl: float         # upper control limit
    lcl: float         # lower control limit


def ewma_init(mu: float, sigma: float, lam: float = 0.2, L: float = 3.0) -> EWMAState:
    """Initialise EWMA state.

    lam: smoothing parameter (0.05–0.40 for personalised use).
    L: control limit multiplier (3 = standard 3-sigma).
    """
    half_width = L * sigma * math.sqrt(lam / (2.0 - lam))
    return EWMAState(z=mu, lam=lam, ucl=mu + half_width, lcl=mu - half_width)


def ewma_update(state: EWMAState, x: float) -> EWMAState:
    state.z = state.lam * x + (1.0 - state.lam) * state.z
    return state


def ewma_alarm(state: EWMAState) -> bool:
    return state.z > state.ucl or state.z < state.lcl


def ewma_p_value(state: EWMAState, mu: float, sigma: float) -> float:
    """Two-sided p-value based on current EWMA position relative to mean."""
    effective_sigma = sigma * math.sqrt(state.lam / (2.0 - state.lam))
    z_score = abs(state.z - mu) / (effective_sigma + 1e-12)
    return float(2.0 * stats.norm.sf(z_score))


def estimate_lambda_from_ar1(history: np.ndarray, clamp_min: float = 0.05, clamp_max: float = 0.40) -> float:
    """Estimate personalised lambda by fitting AR(1) to customer history.

    lambda = 1 - phi, where phi is the AR(1) coefficient.
    """
    if len(history) < 10:
        return 0.2
    y = history[1:]
    x = history[:-1]
    x_centered = x - x.mean()
    y_centered = y - y.mean()
    denom = float(np.dot(x_centered, x_centered))
    if denom < 1e-12:
        return 0.2
    phi = float(np.dot(x_centered, y_centered) / denom)
    lam = 1.0 - phi
    return float(np.clip(lam, clamp_min, clamp_max))
