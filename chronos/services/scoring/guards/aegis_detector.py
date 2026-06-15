"""AEGIS — Input signal integrity guard with drift detection."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

KL_THRESHOLD = 0.5
NOVEL_TOKEN_THRESHOLD = 0.05
MMD_P_VALUE_THRESHOLD = 0.01
MMD_PERMUTATIONS = 200


class DriftType(Enum):
    FEATURE_DRIFT = "feature_drift"
    VOCAB_DRIFT = "vocab_drift"
    DISTRIBUTION_SHIFT = "distribution_shift"


@dataclass
class DriftAlert:
    type: DriftType
    feature_name: Optional[str]
    kl_divergence: Optional[float]
    message: str


class AEGISDetector:
    """Monitor input batches for feature drift, vocab drift, and distribution shift."""

    def __init__(self) -> None:
        self._feature_distributions: dict[str, dict] = {}
        self._training_token_vocab: set[int] = set()
        self._reference_matrix: np.ndarray | None = None

    def load_reference_distributions(self, training_stats_path: str | Path) -> None:
        """Load pre-computed reference distributions from training.

        Args:
            training_stats_path: Path to JSON file with feature statistics.
        """
        path = Path(training_stats_path)
        with open(path) as f:
            stats_data = json.load(f)
        self._feature_distributions = stats_data.get("feature_distributions", {})
        self._training_token_vocab = set(stats_data.get("training_token_vocab", []))
        ref_matrix = stats_data.get("reference_matrix")
        if ref_matrix:
            self._reference_matrix = np.array(ref_matrix)
        logger.info("AEGIS reference distributions loaded from %s", path)

    def save_reference_distributions(self, output_path: str | Path) -> None:
        """Serialize current reference distributions to JSON."""
        data = {
            "feature_distributions": self._feature_distributions,
            "training_token_vocab": sorted(self._training_token_vocab),
            "reference_matrix": self._reference_matrix.tolist() if self._reference_matrix is not None else None,
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("AEGIS reference distributions saved to %s", output_path)

    def fit_reference(
        self,
        feature_matrix: np.ndarray,
        feature_names: list[str],
        token_vocab: set[int],
    ) -> None:
        """Compute and store reference distributions from training data.

        Args:
            feature_matrix: (n_samples, n_features) training feature matrix.
            feature_names: Names of features in column order.
            token_vocab: Set of valid token IDs seen during training.
        """
        self._training_token_vocab = token_vocab
        self._reference_matrix = feature_matrix.copy()

        for i, name in enumerate(feature_names):
            col = feature_matrix[:, i]
            hist, bin_edges = np.histogram(col, bins=20, density=True)
            self._feature_distributions[name] = {
                "hist": hist.tolist(),
                "bin_edges": bin_edges.tolist(),
                "mean": float(col.mean()),
                "std": float(col.std()),
            }

    def check_features(self, batch_features: np.ndarray, feature_names: list[str]) -> list[DriftAlert]:
        """Check per-feature KL divergence against reference.

        Args:
            batch_features: (n_samples, n_features) float array.
            feature_names: Feature names in column order.

        Returns:
            List of DriftAlert for features exceeding threshold.
        """
        alerts: list[DriftAlert] = []
        for i, name in enumerate(feature_names):
            ref = self._feature_distributions.get(name)
            if not ref:
                continue

            col = batch_features[:, i]
            bin_edges = np.array(ref["bin_edges"])
            ref_hist = np.array(ref["hist"])

            batch_hist, _ = np.histogram(col, bins=bin_edges, density=True)
            # Add small epsilon to avoid log(0)
            kl = float(stats.entropy(batch_hist + 1e-9, ref_hist + 1e-9))

            if kl > KL_THRESHOLD:
                msg = f"Feature '{name}' KL divergence {kl:.3f} > threshold {KL_THRESHOLD}"
                logger.warning(msg)
                alerts.append(DriftAlert(
                    type=DriftType.FEATURE_DRIFT,
                    feature_name=name,
                    kl_divergence=kl,
                    message=msg,
                ))
        return alerts

    def check_sequences(self, batch_sequences: list[list[int]]) -> list[DriftAlert]:
        """Check for novel tokens not seen during training.

        Args:
            batch_sequences: List of token ID lists.

        Returns:
            DriftAlert if novel token fraction exceeds threshold.
        """
        if not self._training_token_vocab:
            return []

        total = sum(len(seq) for seq in batch_sequences)
        if total == 0:
            return []

        novel = sum(
            1 for seq in batch_sequences for tok in seq
            if tok != 0 and tok not in self._training_token_vocab
        )
        novel_fraction = novel / total

        if novel_fraction > NOVEL_TOKEN_THRESHOLD:
            msg = f"Novel token fraction {novel_fraction:.3f} > threshold {NOVEL_TOKEN_THRESHOLD}"
            logger.warning(msg)
            return [DriftAlert(
                type=DriftType.VOCAB_DRIFT,
                feature_name=None,
                kl_divergence=None,
                message=msg,
            )]
        return []

    def check_multivariate(self, batch_features: np.ndarray) -> Optional[DriftAlert]:
        """MMD two-sample test for overall distribution shift.

        Args:
            batch_features: (n_samples, n_features) float array.

        Returns:
            DriftAlert if MMD p-value < threshold, else None.
        """
        if self._reference_matrix is None:
            logger.warning("AEGIS: no reference matrix available for MMD test")
            return None

        p_value = _mmd_permutation_test(self._reference_matrix, batch_features, n_permutations=MMD_PERMUTATIONS)

        if p_value < MMD_P_VALUE_THRESHOLD:
            msg = f"MMD distribution shift detected: p_value={p_value:.4f} < {MMD_P_VALUE_THRESHOLD}"
            logger.error(msg)
            return DriftAlert(
                type=DriftType.DISTRIBUTION_SHIFT,
                feature_name=None,
                kl_divergence=None,
                message=msg,
            )
        return None


def _rbf_kernel(X: np.ndarray, Y: np.ndarray, sigma: float = 1.0) -> float:
    """Compute mean RBF kernel value between samples in X and Y."""
    gamma = 1.0 / (2.0 * sigma ** 2)
    XX = np.sum(X ** 2, axis=1, keepdims=True)
    YY = np.sum(Y ** 2, axis=1, keepdims=True)
    XY = X @ Y.T
    dist2 = XX - 2 * XY + YY.T
    return float(np.exp(-gamma * dist2).mean())


def _mmd_stat(X: np.ndarray, Y: np.ndarray) -> float:
    return _rbf_kernel(X, X) + _rbf_kernel(Y, Y) - 2 * _rbf_kernel(X, Y)


def _mmd_permutation_test(
    reference: np.ndarray,
    batch: np.ndarray,
    n_permutations: int = MMD_PERMUTATIONS,
) -> float:
    """Estimate p-value for MMD statistic via permutation test."""
    n_ref = min(len(reference), 500)
    n_bat = min(len(batch), 500)
    ref_sub = reference[np.random.choice(len(reference), n_ref, replace=False)]
    bat_sub = batch[np.random.choice(len(batch), n_bat, replace=False)]

    observed_mmd = _mmd_stat(ref_sub, bat_sub)
    combined = np.vstack([ref_sub, bat_sub])
    n_total = len(combined)

    count_exceeding = 0
    for _ in range(n_permutations):
        perm = np.random.permutation(n_total)
        perm_ref = combined[perm[:n_ref]]
        perm_bat = combined[perm[n_ref:n_ref + n_bat]]
        if _mmd_stat(perm_ref, perm_bat) >= observed_mmd:
            count_exceeding += 1

    return (count_exceeding + 1) / (n_permutations + 1)
