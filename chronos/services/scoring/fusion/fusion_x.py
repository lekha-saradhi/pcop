"""FUSION-X — Adaptive Bayesian Score Fusion with drift detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

import numpy as np
from scipy.special import expit

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

STATIC_TARE_WEIGHT = 0.50
STATIC_HABITAT_WEIGHT = 0.50
MIN_LABELLED_OUTCOMES = 500
ECE_WARNING_THRESHOLD = 0.08
ECE_CRITICAL_THRESHOLD = 0.15
BOOTSTRAP_SAMPLES = 200
ECE_N_BINS = 10


class DriftStatus(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class FusionWeights:
    tare: float = STATIC_TARE_WEIGHT
    habitat: float = STATIC_HABITAT_WEIGHT

    def __post_init__(self) -> None:
        total = self.tare + self.habitat
        self.tare /= total
        self.habitat /= total

    def as_dict(self) -> dict[str, float]:
        return {"tare": self.tare, "habitat": self.habitat}


@dataclass
class FusionResult:
    final_score: float
    ci_lower: float
    ci_upper: float
    tare_weight: float
    habitat_weight: float


@dataclass
class DriftAlert:
    status: DriftStatus
    ece: float
    message: str


class FusionX:
    """Adaptive Bayesian Score Fusion combining TARE and HABITAT outputs."""

    def __init__(self) -> None:
        self._weights = FusionWeights()
        self._weight_history: list[dict] = []

    def calibrate(
        self,
        tare_scores: Sequence[float],
        habitat_scores: Sequence[float],
        outcomes: Sequence[int],
    ) -> FusionWeights:
        """Recalibrate fusion weights based on Brier score comparison.

        Args:
            tare_scores: TARE churn probabilities for labelled samples.
            habitat_scores: HABITAT churn probabilities for same samples.
            outcomes: Binary ground-truth churn labels (0 or 1).

        Returns:
            Updated FusionWeights (also stored internally).
        """
        n = len(outcomes)
        if n < MIN_LABELLED_OUTCOMES:
            logger.warning(
                "Only %d labelled outcomes — using static weights (min=%d)", n, MIN_LABELLED_OUTCOMES
            )
            self._weights = FusionWeights()
            return self._weights

        y = np.array(outcomes, dtype=float)
        tare_arr = np.array(tare_scores, dtype=float)
        hab_arr = np.array(habitat_scores, dtype=float)

        brier_tare = float(np.mean((tare_arr - y) ** 2))
        brier_hab = float(np.mean((hab_arr - y) ** 2))

        # Inverse-Brier weighting
        inv_tare = 1.0 / (brier_tare + 1e-9)
        inv_hab = 1.0 / (brier_hab + 1e-9)
        total = inv_tare + inv_hab
        new_weights = FusionWeights(tare=inv_tare / total, habitat=inv_hab / total)
        self._weights = new_weights

        self._weight_history.append({
            "brier_tare": brier_tare,
            "brier_hab": brier_hab,
            **new_weights.as_dict(),
        })
        logger.info(
            "Weights recalibrated: tare=%.3f habitat=%.3f (brier_tare=%.4f brier_hab=%.4f)",
            new_weights.tare, new_weights.habitat, brier_tare, brier_hab,
        )
        return new_weights

    def fuse(self, tare_score: float, habitat_score: float) -> FusionResult:
        """Fuse two model scores into a calibrated final score with CI.

        Uses logit-space (log-odds) blending, which is more principled than
        linear averaging for probability outputs — especially when models
        have very different calibration scales.

        Args:
            tare_score: TARE churn probability.
            habitat_score: HABITAT churn probability.

        Returns:
            FusionResult with final_score and 95% bootstrap CI bounds.
        """
        EPS = 1e-7
        tare_s = np.clip(tare_score, EPS, 1 - EPS)
        hab_s = np.clip(habitat_score, EPS, 1 - EPS)
        tare_logit = np.log(tare_s / (1 - tare_s))
        hab_logit = np.log(hab_s / (1 - hab_s))

        w_t = self._weights.tare
        w_h = self._weights.habitat
        final_logit = w_t * tare_logit + w_h * hab_logit
        final = float(expit(final_logit))

        # Bootstrap CI in probability space
        rng = np.random.default_rng(seed=None)
        boot_logits = w_t * (tare_logit + rng.normal(0, 0.1, BOOTSTRAP_SAMPLES)) \
                      + w_h * (hab_logit + rng.normal(0, 0.1, BOOTSTRAP_SAMPLES))
        boot_scores = expit(boot_logits)
        ci_lower = float(np.percentile(boot_scores, 2.5))
        ci_upper = float(np.percentile(boot_scores, 97.5))

        return FusionResult(
            final_score=float(np.clip(final, 0, 1)),
            ci_lower=float(np.clip(ci_lower, 0, 1)),
            ci_upper=float(np.clip(ci_upper, 0, 1)),
            tare_weight=w_t,
            habitat_weight=w_h,
        )

    def check_drift(
        self,
        recent_predictions: Sequence[float],
        recent_outcomes: Sequence[int],
    ) -> DriftAlert:
        """Compute ECE and classify drift severity.

        Args:
            recent_predictions: Model probabilities for recent predictions.
            recent_outcomes: Ground-truth labels for those predictions.

        Returns:
            DriftAlert with status, ECE value, and description.
        """
        ece = _compute_ece(recent_predictions, recent_outcomes, n_bins=ECE_N_BINS)
        if ece >= ECE_CRITICAL_THRESHOLD:
            status = DriftStatus.CRITICAL
            msg = f"CRITICAL calibration drift: ECE={ece:.4f} (threshold={ECE_CRITICAL_THRESHOLD})"
        elif ece >= ECE_WARNING_THRESHOLD:
            status = DriftStatus.WARNING
            msg = f"WARNING calibration drift: ECE={ece:.4f} (threshold={ECE_WARNING_THRESHOLD})"
        else:
            status = DriftStatus.NORMAL
            msg = f"Calibration OK: ECE={ece:.4f}"
        logger.info(msg)
        return DriftAlert(status=status, ece=ece, message=msg)

    @property
    def weights(self) -> FusionWeights:
        return self._weights

    @property
    def weight_history(self) -> list[dict]:
        return self._weight_history


def _compute_ece(
    predictions: Sequence[float],
    outcomes: Sequence[int],
    n_bins: int = ECE_N_BINS,
) -> float:
    """Compute Expected Calibration Error with equal-frequency bins."""
    preds = np.array(predictions)
    y = np.array(outcomes)
    n = len(preds)

    sorted_idx = np.argsort(preds)
    preds_sorted = preds[sorted_idx]
    y_sorted = y[sorted_idx]

    bin_size = n // n_bins
    ece = 0.0
    for b in range(n_bins):
        start = b * bin_size
        end = start + bin_size if b < n_bins - 1 else n
        if start >= end:
            continue
        bin_preds = preds_sorted[start:end]
        bin_y = y_sorted[start:end]
        ece += (len(bin_preds) / n) * abs(bin_preds.mean() - bin_y.mean())
    return float(ece)
