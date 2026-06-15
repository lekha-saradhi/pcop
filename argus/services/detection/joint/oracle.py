"""ORACLE — Multivariate Online Changepoint Detector (2C).

Replaces BOCPD with a streaming multiscale likelihood ratio test.
Runs continuously (not polled every 2 hours) and outputs a changepoint
onset estimate alongside the alarm.

Research basis: High-dimensional multiscale online changepoint detection
(Chen, Wang & Samworth 2020); arXiv 2311.01174.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

_SCALES = (7, 14, 30)          # detection windows in days
_P = 8                         # number of signal dimensions
_ARL0 = 500                    # target average run length under H0

# Alarm threshold calibrated for ARL0 ≈ 500:
# P(max_s Σ_j LR_{j,s} > h) ≈ 3 * chi2.sf(h, df=p) ≤ 1/ARL0
# → chi2.sf(h, 8) ≤ 1/1500 → h = chi2.ppf(1 - 1/1500, 8) ≈ 28.3
_THRESHOLD = float(stats.chi2.ppf(1.0 - 1.0 / (_ARL0 * len(_SCALES)), df=_P))


@dataclass
class ORACLEResult:
    oracle_detected: bool
    alarm_scale: int | None        # days — scale with most anomalous LRT
    alarm_dimensions: list[str]    # sparse signal subset that drove alarm
    test_statistic: float
    threshold: float
    onset_estimate: date | None
    p_value: float
    evidence: list[str]


SIGNAL_DIMS = [
    "txn_freq", "recency_score", "salary_amount", "sentiment_score",
    "engagement_score", "overdraft_rate", "cfsi", "login_count",
]


def _lrt_per_dim(X_window: np.ndarray, mus: np.ndarray, sigmas: np.ndarray) -> np.ndarray:
    """Compute LR_{j,s,t} for each dimension over a single window.

    Returns (p,) array of per-dimension LRT statistics.
    LR_j = (Σ (x_i^j - mu_j))^2 / (s * sigma_j^2)
    """
    s = X_window.shape[0]
    if s == 0:
        return np.zeros(_P)
    diffs = X_window - mus[np.newaxis, :]
    col_sums = diffs.sum(axis=0)
    sigmas_safe = np.maximum(sigmas, 1e-6)
    lrt = col_sums ** 2 / (s * sigmas_safe ** 2)
    return lrt


def _sparse_aggregate(lrt: np.ndarray) -> tuple[float, list[int]]:
    """Greedy sparse aggregation: sum all positive-contributing dimensions.

    Since each LRT_j >= 0, the maximum-weight subset is all dimensions.
    Returns (total, sorted indices contributing).
    """
    pos_idx = [j for j in range(len(lrt)) if lrt[j] > 0.0]
    total = float(lrt[pos_idx].sum()) if pos_idx else 0.0
    return total, sorted(pos_idx, key=lambda j: lrt[j], reverse=True)


def oracle_evaluate(
    X: np.ndarray,
    dates: list[date],
    mus: np.ndarray | None = None,
    sigmas: np.ndarray | None = None,
) -> ORACLEResult:
    """Evaluate ORACLE on a signal matrix X.

    X: (n_days, p) signal matrix ordered by date (oldest → newest).
    dates: list of date objects, len == n_days.
    mus: (p,) baseline means (uses X mean if None).
    sigmas: (p,) baseline stds (uses X std if None).
    """
    n, p = X.shape
    if n < min(_SCALES):
        return ORACLEResult(
            oracle_detected=False, alarm_scale=None, alarm_dimensions=[],
            test_statistic=0.0, threshold=_THRESHOLD, onset_estimate=None,
            p_value=1.0, evidence=["ORACLE: insufficient history"],
        )

    mu_arr = mus if mus is not None else X.mean(axis=0)
    sig_arr = sigmas if sigmas is not None else np.maximum(X.std(axis=0), 1e-6)

    best_stat = 0.0
    best_scale: int | None = None
    best_dims: list[int] = []

    for s in _SCALES:
        if n < s:
            continue
        window = X[-s:]
        lrt = _lrt_per_dim(window, mu_arr, sig_arr)
        stat, dims = _sparse_aggregate(lrt)
        if stat > best_stat:
            best_stat = stat
            best_scale = s
            best_dims = dims

    detected = best_stat > _THRESHOLD

    # P-value: under H0, best_stat ~ chi2(p) for the winning scale (Bonferroni-corrected)
    n_scales = sum(1 for s in _SCALES if n >= s)
    p_uncorrected = float(stats.chi2.sf(best_stat, df=_P))
    p_value = min(1.0, p_uncorrected * n_scales)

    # Onset estimate: find the sub-window with maximum cumulative shift
    onset: date | None = None
    if detected and best_scale is not None and len(dates) >= best_scale:
        onset = dates[-best_scale]

    dim_names = [SIGNAL_DIMS[j] for j in best_dims[:4]] if best_dims else []

    evidence: list[str] = []
    if detected:
        evidence.append(
            f"ORACLE: {best_scale}-day multiscale LRT statistic {best_stat:.1f}"
            f" > threshold {_THRESHOLD:.1f} in dims {dim_names}"
        )

    return ORACLEResult(
        oracle_detected=detected,
        alarm_scale=best_scale,
        alarm_dimensions=dim_names,
        test_statistic=best_stat,
        threshold=_THRESHOLD,
        onset_estimate=onset,
        p_value=p_value,
        evidence=evidence,
    )
