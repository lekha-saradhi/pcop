"""Export the fine-tuned TARE model to ONNX format and benchmark throughput."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DIR = ROOT / "ml" / "checkpoints"
DEFAULT_INPUT = CHECKPOINT_DIR / "tare_finetune_final.pt"
DEFAULT_OUTPUT = CHECKPOINT_DIR / "tare_churn.onnx"
MAX_SEQ_LEN = 180


def export(checkpoint_path: Path, output_path: Path) -> None:
    """Export TARE checkpoint to ONNX with dynamic batch axis."""
    from services.scoring.models.tare_encoder import TAREEncoder

    model = TAREEncoder.from_pretrained(checkpoint_path)
    model.eval()

    dummy_ids = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    dummy_gaps = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.float32)

    torch.onnx.export(
        model,
        (dummy_ids, dummy_gaps),
        str(output_path),
        input_names=["token_ids", "time_gaps"],
        output_names=["churn_prob", "attention_weights"],
        dynamic_shapes={
            "token_ids": {0: torch.export.Dim("batch", min=1, max=1024)},
            "time_gaps": {0: torch.export.Dim("batch", min=1, max=1024)},
        },
        opset_version=18,
        do_constant_folding=True,
    )
    logger.info("ONNX model exported to %s", output_path)


def verify(checkpoint_path: Path, onnx_path: Path, tol: float = 5e-3) -> None:
    """Verify ONNX output matches PyTorch output within tolerance."""
    from services.scoring.models.tare_encoder import TAREEncoder

    model = TAREEncoder.from_pretrained(checkpoint_path)
    model.eval()

    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

    dummy_ids = torch.randint(0, 50, (1, MAX_SEQ_LEN))
    dummy_gaps = torch.rand(1, MAX_SEQ_LEN) * 30

    with torch.no_grad():
        pt_prob, pt_attn = model(dummy_ids, dummy_gaps)

    ort_out = session.run(
        None,
        {"token_ids": dummy_ids.numpy(), "time_gaps": dummy_gaps.numpy()},
    )

    max_diff_prob = float(np.abs(pt_prob.numpy() - ort_out[0]).max())
    max_diff_attn = float(np.abs(pt_attn.numpy() - ort_out[1]).max())

    logger.info("Max diff churn_prob: %.2e | attention_weights: %.2e", max_diff_prob, max_diff_attn)

    assert max_diff_prob < tol, f"churn_prob diff {max_diff_prob:.2e} exceeds tolerance {tol}"
    assert max_diff_attn < 0.1, f"attention_weights diff {max_diff_attn:.2e} exceeds tolerance 0.1"
    logger.info("ONNX verification passed (tol=%.1e / attn=0.1)", tol)


def benchmark(onnx_path: Path, batch_sizes: list[int] = (1,), warmup: int = 5, runs: int = 50) -> None:
    """Measure ONNX Runtime throughput in sequences/sec at various batch sizes."""
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

    for bs in batch_sizes:
        ids = np.zeros((bs, MAX_SEQ_LEN), dtype=np.int64)
        gaps = np.zeros((bs, MAX_SEQ_LEN), dtype=np.float32)

        for _ in range(warmup):
            session.run(None, {"token_ids": ids, "time_gaps": gaps})

        start = time.perf_counter()
        for _ in range(runs):
            session.run(None, {"token_ids": ids, "time_gaps": gaps})
        elapsed = time.perf_counter() - start

        throughput = (bs * runs) / elapsed
        logger.info("batch=%d  throughput=%.0f seq/sec  latency=%.1f ms/batch", bs, throughput, elapsed / runs * 1000)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Export TARE to ONNX and benchmark")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--skip-benchmark", action="store_true")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    export(args.checkpoint, args.output)

    if not args.skip_verify:
        verify(args.checkpoint, args.output)
    if not args.skip_benchmark:
        benchmark(args.output)


if __name__ == "__main__":
    main()
