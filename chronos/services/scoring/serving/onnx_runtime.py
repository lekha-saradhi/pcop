"""ONNX Runtime inference wrapper for TARE model."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ONNX_PATH = ROOT / "ml" / "checkpoints" / "tare_churn.onnx"


class TARERuntimeSession:
    """Thread-safe ONNX Runtime session for TARE inference."""

    def __init__(self, onnx_path: str | Path = DEFAULT_ONNX_PATH) -> None:
        import onnxruntime as ort

        self._path = Path(onnx_path)
        if not self._path.exists():
            raise FileNotFoundError(f"TARE ONNX model not found at {self._path}")

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = 1  # single-customer real-time path

        self._session = ort.InferenceSession(
            str(self._path),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )
        logger.info("ONNX Runtime session initialised from %s", self._path)

    def score(
        self,
        token_ids: np.ndarray,
        time_gaps: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run inference on a batch of sequences.

        Args:
            token_ids: (batch, seq_len) int64 array.
            time_gaps: (batch, seq_len) float32 array.

        Returns:
            churn_probs: (batch,) float32 churn probabilities.
            attention_weights: (batch, seq_len) float32 attention scores.
        """
        outputs = self._session.run(
            None,
            {"token_ids": token_ids.astype(np.int64), "time_gaps": time_gaps.astype(np.float32)},
        )
        return outputs[0], outputs[1]

    def score_single(
        self,
        token_ids: list[int],
        time_gaps: list[float],
    ) -> tuple[float, list[float]]:
        """Score a single customer sequence.

        Args:
            token_ids: List of token IDs (length MAX_SEQ_LEN).
            time_gaps: List of time gaps (length MAX_SEQ_LEN).

        Returns:
            (churn_prob, attention_weights)
        """
        ids_arr = np.array([token_ids], dtype=np.int64)
        gaps_arr = np.array([time_gaps], dtype=np.float32)
        probs, attn = self.score(ids_arr, gaps_arr)
        return float(probs[0]), attn[0].tolist()
