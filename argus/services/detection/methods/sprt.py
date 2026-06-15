"""Sequential Probability Ratio Test (SPRT) for Poisson count data.

Used for complaint volume surge detection.
Reference: Wald (1947), sequential analysis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class SPRTState:
    log_lr: float = 0.0   # cumulative log-likelihood ratio
    n: int = 0            # observations processed


def sprt_update(state: SPRTState, count: int, lambda0: float, lambda1: float) -> SPRTState:
    """Update SPRT with a new Poisson count observation.

    count: observed count in this period.
    lambda0: null hypothesis rate (baseline).
    lambda1: alternative hypothesis rate (surge level, lambda1 > lambda0).
    """
    # Log LR for one Poisson observation: count*log(lambda1/lambda0) - (lambda1-lambda0)
    state.log_lr += count * math.log(lambda1 / lambda0) - (lambda1 - lambda0)
    state.n += 1
    return state


def sprt_decision(state: SPRTState, alpha: float = 0.05, beta: float = 0.10) -> str:
    """Return 'H1' (surge detected), 'H0' (no surge), or 'continue' (insufficient evidence)."""
    A = math.log(beta / (1.0 - alpha))     # lower boundary: accept H0
    B = math.log((1.0 - beta) / alpha)    # upper boundary: reject H0 (alarm H1)
    if state.log_lr >= B:
        return "H1"
    if state.log_lr <= A:
        return "H0"
    return "continue"


def sprt_alarm(state: SPRTState, alpha: float = 0.05, beta: float = 0.10) -> bool:
    return sprt_decision(state, alpha, beta) == "H1"


def sprt_p_value(state: SPRTState, alpha: float = 0.05, beta: float = 0.10) -> float:
    """Approximate p-value from log-likelihood ratio position relative to boundaries."""
    B = math.log((1.0 - beta) / alpha)
    if B <= 0.0:
        return 1.0
    # Linearly map log_lr from 0 (p=1) to B (p~alpha)
    fraction = max(0.0, min(1.0, state.log_lr / B))
    return float(1.0 - fraction * (1.0 - alpha))


def sprt_reset(state: SPRTState) -> SPRTState:
    state.log_lr = 0.0
    state.n = 0
    return state
