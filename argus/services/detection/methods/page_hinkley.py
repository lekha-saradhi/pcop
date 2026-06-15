"""Page-Hinkley change detection test (kept for reference).

Note: Page-Hinkley is one-sided. For two-sided detection (engagement can
spike OR collapse) use two separate instances or EWMA instead.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class PageHinkleyState:
    cumsum: float = 0.0
    min_cumsum: float = 0.0
    n: int = 0


def ph_update(state: PageHinkleyState, x: float, mu: float, delta: float = 0.005) -> PageHinkleyState:
    """Update Page-Hinkley statistic.

    delta: allowance parameter controlling sensitivity to small changes.
    """
    state.cumsum += x - mu - delta
    state.min_cumsum = min(state.min_cumsum, state.cumsum)
    state.n += 1
    return state


def ph_alarm(state: PageHinkleyState, lambda_: float = 50.0) -> bool:
    """Alarm when difference exceeds lambda_ (sensitivity threshold)."""
    return (state.cumsum - state.min_cumsum) > lambda_


def ph_reset(state: PageHinkleyState) -> PageHinkleyState:
    state.cumsum = 0.0
    state.min_cumsum = 0.0
    state.n = 0
    return state
