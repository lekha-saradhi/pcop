"""NEXUS — Correlation Structure Monitor (2B).

Monitors the precision matrix (inverse covariance) of the signal vector.
Detects when signal co-movement pattern changes, even when no individual
signal has crossed its alarm threshold.

Research basis: G-BOCPD (Namoano et al., 2024); Contrastive Structured
Anomaly Detection for GGMs (Maurya & Cheung, CMU).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import stats
from sklearn.covariance import GraphicalLasso

logger = logging.getLogger(__name__)

# Signal dimensions (order must match signal vector)
SIGNAL_DIMS = [
    "txn_freq", "recency_score", "salary_amount", "sentiment_score",
    "engagement_score", "overdraft_rate", "cfsi", "login_count",
]
_P = len(SIGNAL_DIMS)   # 8 signal dimensions

_GL_ALPHA = 0.1         # graphical lasso L1 penalty
_LRT_ALPHA = 0.01       # alarm p-value threshold
_LRT_ALPHA_STRICT = 0.001  # strict threshold when Frobenius delta also large
_FROBENIUS_SIGMA = 2.0  # sigma multiplier for Frobenius boosting


@dataclass
class NEXUSState:
    omega_baseline: np.ndarray | None = None   # (p, p) precision matrix
    omega_current: np.ndarray | None = None
    frobenius_baseline_mean: float = 0.0
    frobenius_baseline_std: float = 1.0
    segment: str = "mass_market"


@dataclass
class NEXUSResult:
    nexus_detected: bool
    lrt_p_value: float
    frobenius_delta: float
    changed_edges: list[tuple[str, str]]
    confidence: float
    evidence: list[str]


def _graphical_lasso_precision(X: np.ndarray, alpha: float = _GL_ALPHA) -> np.ndarray:
    """Estimate precision matrix via graphical lasso. Returns (p, p) array."""
    gl = GraphicalLasso(alpha=alpha, max_iter=200)
    gl.fit(X)
    return gl.precision_


def _find_changed_edges(
    omega_base: np.ndarray,
    omega_curr: np.ndarray,
    threshold: float = 0.10,
) -> list[tuple[str, str]]:
    """Return signal pairs whose precision entry changed by > threshold."""
    diff = np.abs(omega_curr - omega_base)
    edges = []
    for i in range(_P):
        for j in range(i + 1, _P):
            if diff[i, j] > threshold:
                edges.append((SIGNAL_DIMS[i], SIGNAL_DIMS[j]))
    return edges


def nexus_fit_baseline(X_baseline: np.ndarray) -> NEXUSState:
    """Estimate baseline precision matrix from stable customer history (≥ 40 days).

    X_baseline: (n_days, p) signal matrix from stable period.
    """
    if X_baseline.shape[0] < 2 * _P:
        logger.warning("NEXUS: insufficient baseline data (%d rows, need %d)", X_baseline.shape[0], 2 * _P)
    state = NEXUSState()
    state.omega_baseline = _graphical_lasso_precision(X_baseline)
    return state


def nexus_evaluate(state: NEXUSState, X_current: np.ndarray) -> NEXUSResult:
    """Evaluate current 30-day window against baseline precision matrix.

    X_current: (n_days, p) signal matrix for current window (≥ 10 days).
    """
    if state.omega_baseline is None:
        return NEXUSResult(
            nexus_detected=False, lrt_p_value=1.0, frobenius_delta=0.0,
            changed_edges=[], confidence=0.0, evidence=["NEXUS: no baseline fitted"],
        )

    # Re-estimate current precision
    if X_current.shape[0] < 5:
        return NEXUSResult(
            nexus_detected=False, lrt_p_value=1.0, frobenius_delta=0.0,
            changed_edges=[], confidence=0.0, evidence=["NEXUS: insufficient current window"],
        )

    try:
        omega_curr = _graphical_lasso_precision(X_current)
    except Exception as exc:
        logger.warning("NEXUS: graphical lasso failed: %s", exc)
        return NEXUSResult(
            nexus_detected=False, lrt_p_value=1.0, frobenius_delta=0.0,
            changed_edges=[], confidence=0.0, evidence=[],
        )

    state.omega_current = omega_curr
    omega_base = state.omega_baseline

    # Sample covariance of current window
    S_curr = np.cov(X_current.T, ddof=1)
    if S_curr.ndim == 0:
        S_curr = np.array([[S_curr]])

    # LRT: tr(Omega_base @ S_curr) - log|Omega_base @ S_curr| - p
    OS = omega_base @ S_curr
    sign, logdet = np.linalg.slogdet(OS)
    if sign <= 0:
        lrt_stat = float(np.trace(OS)) - float(_P)
    else:
        lrt_stat = float(np.trace(OS)) - float(logdet) - float(_P)
    lrt_stat = max(lrt_stat, 0.0)

    df = _P * (_P + 1) // 2
    lrt_p = float(stats.chi2.sf(lrt_stat, df))

    # Frobenius norm change
    frob_delta = float(np.linalg.norm(omega_curr - omega_base, "fro"))
    frob_z = (frob_delta - state.frobenius_baseline_mean) / max(state.frobenius_baseline_std, 1e-6)
    strict_mode = frob_z > _FROBENIUS_SIGMA

    threshold = _LRT_ALPHA_STRICT if strict_mode else _LRT_ALPHA
    detected = lrt_p < threshold

    changed = _find_changed_edges(omega_base, omega_curr)
    evidence: list[str] = []
    if detected:
        for e1, e2 in changed[:5]:
            evidence.append(f"{e1}-{e2} correlation structure changed")

    confidence = max(0.0, 1.0 - lrt_p)

    return NEXUSResult(
        nexus_detected=detected,
        lrt_p_value=lrt_p,
        frobenius_delta=frob_delta,
        changed_edges=changed,
        confidence=confidence,
        evidence=evidence,
    )


def nexus_shrink_to_segment(
    omega_individual: np.ndarray | None,
    omega_segment: np.ndarray,
    tenure_months: float,
) -> np.ndarray:
    """Shrinkage estimator blending individual + segment precision matrices.

    alpha = min(1.0, tenure_months / 12) weights own history.
    """
    alpha = min(1.0, tenure_months / 12.0)
    if omega_individual is None:
        return omega_segment
    return alpha * omega_individual + (1.0 - alpha) * omega_segment
