"""Survival-Adjusted EWMA for transaction recency detection.

Correctly handles monthly, weekly, and daily transactors via a
customer-specific exponential inter-arrival distribution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class SAEWMAState:
    z: float             # EWMA of log-survival
    mu_z: float          # baseline mean of log-survival EWMA
    sigma_z: float       # baseline std of log-survival EWMA
    lam_customer: float  # exponential rate (1/avg_inter_arrival_days)
    alpha: float = 0.2   # EWMA smoothing


def sa_ewma_init(inter_arrival_days: np.ndarray, alpha: float = 0.2) -> SAEWMAState:
    """Initialise SA-EWMA from historical inter-arrival days.

    inter_arrival_days: array of days between successive transactions.
    """
    mean_ia = float(np.mean(inter_arrival_days)) if len(inter_arrival_days) > 0 else 7.0
    lam = 1.0 / max(mean_ia, 0.5)

    # Bootstrap initial Z values from history
    log_survivals = [-lam * d for d in inter_arrival_days]
    ewma_vals: list[float] = []
    z = float(np.mean(log_survivals)) if log_survivals else 0.0
    for ls in log_survivals:
        z = alpha * ls + (1.0 - alpha) * z
        ewma_vals.append(z)

    mu_z = float(np.mean(ewma_vals)) if ewma_vals else z
    sigma_z = float(np.std(ewma_vals)) if len(ewma_vals) > 1 else 1.0

    return SAEWMAState(z=mu_z, mu_z=mu_z, sigma_z=sigma_z, lam_customer=lam, alpha=alpha)


def sa_ewma_update(state: SAEWMAState, days_since_last_txn: float) -> SAEWMAState:
    """Update state with current days-since-last-transaction."""
    log_s = -state.lam_customer * days_since_last_txn
    state.z = state.alpha * log_s + (1.0 - state.alpha) * state.z
    return state


def sa_ewma_alarm(state: SAEWMAState, L: float = 3.0) -> bool:
    """Alarm when log-survival EWMA exceeds UCL (high = customer taking longer between txns)."""
    ucl = state.mu_z + L * state.sigma_z
    return state.z > ucl


def sa_ewma_p_value(state: SAEWMAState) -> float:
    """One-sided p-value: probability of observing this high a log-survival EWMA under H0."""
    z_score = (state.z - state.mu_z) / (state.sigma_z + 1e-12)
    return float(stats.norm.sf(z_score))


def survival_percentile(state: SAEWMAState, days_since_last_txn: float) -> float:
    """Percentile rank of current inter-arrival gap in customer's historical distribution."""
    # P(X <= t) = 1 - exp(-lam * t) for exponential distribution
    return float(1.0 - math.exp(-state.lam_customer * days_since_last_txn))
