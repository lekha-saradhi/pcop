"""Unit tests for FUSION-X adaptive score fusion."""

import pytest
import numpy as np

from services.scoring.fusion.fusion_x import (
    FusionX,
    FusionWeights,
    DriftStatus,
    STATIC_TARE_WEIGHT,
    STATIC_HABITAT_WEIGHT,
    MIN_LABELLED_OUTCOMES,
)


@pytest.fixture()
def fusion() -> FusionX:
    return FusionX()


def test_default_weights(fusion: FusionX) -> None:
    w = fusion.weights
    assert abs(w.tare - STATIC_TARE_WEIGHT) < 1e-9
    assert abs(w.habitat - STATIC_HABITAT_WEIGHT) < 1e-9


def test_weights_sum_to_one(fusion: FusionX) -> None:
    assert abs(fusion.weights.tare + fusion.weights.habitat - 1.0) < 1e-9


def test_fuse_output_in_range(fusion: FusionX) -> None:
    result = fusion.fuse(0.7, 0.5)
    assert 0.0 <= result.final_score <= 1.0
    assert 0.0 <= result.ci_lower <= result.final_score
    assert result.final_score <= result.ci_upper <= 1.0


def test_calibrate_with_sufficient_outcomes(fusion: FusionX) -> None:
    n = MIN_LABELLED_OUTCOMES + 100
    tare = np.random.default_rng(0).uniform(0.3, 0.8, n).tolist()
    hab = np.random.default_rng(1).uniform(0.2, 0.7, n).tolist()
    outcomes = [int(t > 0.5) for t in tare]

    weights = fusion.calibrate(tare, hab, outcomes)
    assert abs(weights.tare + weights.habitat - 1.0) < 1e-9


def test_calibrate_static_fallback_insufficient(fusion: FusionX) -> None:
    tare = [0.5] * 10
    hab = [0.4] * 10
    outcomes = [0] * 5 + [1] * 5

    weights = fusion.calibrate(tare, hab, outcomes)
    assert abs(weights.tare - STATIC_TARE_WEIGHT) < 1e-6


def test_drift_detection_normal(fusion: FusionX) -> None:
    # Well-calibrated predictions
    preds = [0.1 * (i % 10) for i in range(100)]
    outcomes = [int(p > 0.5) for p in preds]
    alert = fusion.check_drift(preds, outcomes)
    assert alert.status in (DriftStatus.NORMAL, DriftStatus.WARNING)


def test_drift_detection_critical(fusion: FusionX) -> None:
    # Completely miscalibrated: all predictions 0.9 but all outcomes 0
    preds = [0.9] * 200
    outcomes = [0] * 200
    alert = fusion.check_drift(preds, outcomes)
    assert alert.status == DriftStatus.CRITICAL


def test_bootstrap_ci_coverage(fusion: FusionX) -> None:
    result = fusion.fuse(0.6, 0.5)
    assert result.ci_lower <= result.final_score <= result.ci_upper
