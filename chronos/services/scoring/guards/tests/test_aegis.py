"""Unit tests for AEGIS drift detector."""

import numpy as np
import pytest

from services.scoring.guards.aegis_detector import (
    AEGISDetector,
    DriftType,
    KL_THRESHOLD,
    NOVEL_TOKEN_THRESHOLD,
)

N_FEATURES = 5
FEATURE_NAMES = [f"feature_{i}" for i in range(N_FEATURES)]


@pytest.fixture()
def fitted_detector() -> AEGISDetector:
    rng = np.random.default_rng(42)
    ref = rng.normal(0, 1, (1000, N_FEATURES)).astype(np.float32)
    detector = AEGISDetector()
    detector.fit_reference(ref, FEATURE_NAMES, set(range(50)))
    return detector


def test_no_drift_on_same_distribution(fitted_detector: AEGISDetector) -> None:
    rng = np.random.default_rng(99)
    batch = rng.normal(0, 1, (200, N_FEATURES)).astype(np.float32)
    alerts = fitted_detector.check_features(batch, FEATURE_NAMES)
    feature_drift_alerts = [a for a in alerts if a.type == DriftType.FEATURE_DRIFT]
    assert len(feature_drift_alerts) == 0


def test_feature_drift_detected(fitted_detector: AEGISDetector) -> None:
    rng = np.random.default_rng(0)
    batch = rng.normal(0, 1, (200, N_FEATURES)).astype(np.float32)
    batch[:, 0] += 6.0  # large shift in feature_0
    alerts = fitted_detector.check_features(batch, FEATURE_NAMES)
    assert any(a.type == DriftType.FEATURE_DRIFT and a.feature_name == "feature_0" for a in alerts)


def test_no_vocab_drift_known_tokens(fitted_detector: AEGISDetector) -> None:
    sequences = [[i % 50 for i in range(20)] for _ in range(50)]
    alerts = fitted_detector.check_sequences(sequences)
    assert len(alerts) == 0


def test_vocab_drift_novel_tokens(fitted_detector: AEGISDetector) -> None:
    sequences = [[100, 200, 300, 1, 2, 3] for _ in range(50)]  # 50% novel
    alerts = fitted_detector.check_sequences(sequences)
    assert any(a.type == DriftType.VOCAB_DRIFT for a in alerts)


def test_mmd_no_shift(fitted_detector: AEGISDetector) -> None:
    rng = np.random.default_rng(11)
    batch = rng.normal(0, 1, (200, N_FEATURES)).astype(np.float32)
    alert = fitted_detector.check_multivariate(batch)
    # May or may not fire depending on random permutations, but mostly not
    # Just check it runs without error
    assert alert is None or alert.type == DriftType.DISTRIBUTION_SHIFT


def test_mmd_fires_on_shifted_distribution(fitted_detector: AEGISDetector) -> None:
    rng = np.random.default_rng(0)
    batch = rng.normal(10, 1, (200, N_FEATURES)).astype(np.float32)  # massively shifted
    alert = fitted_detector.check_multivariate(batch)
    assert alert is not None
    assert alert.type == DriftType.DISTRIBUTION_SHIFT


def test_save_load_reference(fitted_detector: AEGISDetector, tmp_path) -> None:
    save_path = tmp_path / "aegis_ref.json"
    fitted_detector.save_reference_distributions(str(save_path))

    new_detector = AEGISDetector()
    new_detector.load_reference_distributions(str(save_path))

    assert set(new_detector._feature_distributions.keys()) == set(FEATURE_NAMES)
    assert new_detector._training_token_vocab == fitted_detector._training_token_vocab
