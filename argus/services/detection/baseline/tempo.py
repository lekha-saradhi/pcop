"""TEMPO — Adaptive Baseline Manager via Kalman filter.

Replaces quarterly rebaseline with continuous online updating.
Baseline is frozen (alarm-locked) when a signal alarm is active to
prevent baseline contamination during a churn episode.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_Q_SLOW = 0.001    # process noise fraction of sigma^2 (normal drift)
_Q_FAST = 0.100    # process noise fraction during fast-update mode
_RESUME_DAYS = 7   # days after alarm clear before baseline resumes


@dataclass
class TEMPOState:
    """Kalman-filter baseline state for a single signal stream."""

    signal_type: str
    mu: float                        # current baseline mean
    sigma: float                     # current baseline std
    P: float                         # Kalman estimation variance
    update_status: str = "active"    # "active" | "alarm_locked" | "fast_update"
    alarm_cleared_date: Optional[date] = None
    fast_update_start: Optional[date] = None
    fast_update_days_remaining: int = 0


def tempo_init(signal_type: str, mu: float, sigma: float) -> TEMPOState:
    """Initialise TEMPO state from historical mean and std."""
    return TEMPOState(
        signal_type=signal_type,
        mu=mu,
        sigma=max(sigma, 1e-6),
        P=sigma ** 2,   # initial estimation variance = signal variance
    )


def tempo_update(state: TEMPOState, x: float, today: date) -> TEMPOState:
    """Apply one Kalman step — skipped if alarm_locked.

    Should be called once per new observation when no alarm is active.
    """
    if state.update_status == "alarm_locked":
        return state

    # Check if resume delay has elapsed
    if state.update_status == "active" and state.alarm_cleared_date is not None:
        if (today - state.alarm_cleared_date).days < _RESUME_DAYS:
            return state
        state.alarm_cleared_date = None

    # Select process noise
    if state.update_status == "fast_update":
        q_frac = _Q_FAST
        state.fast_update_days_remaining -= 1
        if state.fast_update_days_remaining <= 0:
            state.update_status = "active"
            logger.info("TEMPO %s: returning to slow-drift mode", state.signal_type)
    else:
        q_frac = _Q_SLOW

    Q = q_frac * state.sigma ** 2
    R = state.sigma ** 2   # measurement noise = signal variance

    # Prediction
    P_pred = state.P + Q

    # Update
    K = P_pred / (P_pred + R)
    state.mu = state.mu + K * (x - state.mu)
    state.P = (1.0 - K) * P_pred

    return state


def tempo_lock(state: TEMPOState) -> TEMPOState:
    """Freeze baseline when WARDEN fires an alarm for this signal."""
    state.update_status = "alarm_locked"
    return state


def tempo_unlock(state: TEMPOState, cleared_date: date) -> TEMPOState:
    """Resume baseline update _RESUME_DAYS after the alarm is cleared."""
    state.update_status = "active"
    state.alarm_cleared_date = cleared_date
    return state


def tempo_fast_update(state: TEMPOState, today: date, days: int = 30) -> TEMPOState:
    """Activate fast-update mode when Layer 4 confirms a life event."""
    state.update_status = "fast_update"
    state.fast_update_start = today
    state.fast_update_days_remaining = days
    logger.info("TEMPO %s: fast-update mode activated for %d days", state.signal_type, days)
    return state
