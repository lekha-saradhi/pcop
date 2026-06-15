"""Register all CHRONOS models in MLflow Model Registry."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_DIR = ROOT / "ml" / "checkpoints"

MODEL_REGISTRY = [
    {
        "name": "tare-encoder",
        "version": "v1.0",
        "checkpoint": "tare_finetune_final.pt",
        "description": "TARE GRU sequence encoder — binary churn classifier",
        "tags": {"framework": "pytorch", "pass": "1"},
    },
    {
        "name": "habitat-pass1",
        "version": "v1.0",
        "checkpoint": "habitat_pass1.json",
        "description": "HABITAT XGBoost tabular scorer — Pass 1",
        "tags": {"framework": "xgboost", "pass": "1"},
    },
    {
        "name": "fusion-x",
        "version": "v1.0",
        "checkpoint": "fusion_weights.json",
        "description": "FUSION-X adaptive Bayesian score combiner",
        "tags": {"framework": "custom", "pass": "fusion"},
    },
    {
        "name": "causal-net",
        "version": "v1.0",
        "checkpoint": "causal_net_treated.json",
        "description": "CAUSAL-NET uplift model for treatability scoring",
        "tags": {"framework": "xgboost", "pass": "treatability"},
    },
    {
        "name": "genesis",
        "version": "v1.0",
        "checkpoint": "genesis_lr.pkl",
        "description": "GENESIS Logistic Regression cold-start scorer",
        "tags": {"framework": "sklearn", "pass": "cold-start"},
    },
    {
        "name": "aegis-reference",
        "version": "v1.0",
        "checkpoint": "aegis_reference.json",
        "description": "AEGIS reference distributions for drift detection",
        "tags": {"framework": "custom", "pass": "guard"},
    },
]


def _get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def register_model(client: MlflowClient, entry: dict, git_sha: str, dry_run: bool) -> None:
    """Register a single model artifact in MLflow."""
    checkpoint_path = CHECKPOINT_DIR / entry["checkpoint"]
    if not checkpoint_path.exists():
        logger.warning("Checkpoint missing — skipping %s: %s", entry["name"], checkpoint_path)
        return

    model_name = f"chronos-{entry['name']}"
    logger.info("Registering %s (version=%s)", model_name, entry["version"])

    if dry_run:
        logger.info("[dry-run] Would register %s from %s", model_name, checkpoint_path)
        return

    with mlflow.start_run(run_name=f"register-{entry['name']}"):
        mlflow.set_tags({
            "model_name": entry["name"],
            "model_version": entry["version"],
            "git_sha": git_sha,
            **entry.get("tags", {}),
        })
        mlflow.log_artifact(str(checkpoint_path), artifact_path="model")
        mlflow.log_param("version", entry["version"])
        mlflow.log_text(entry.get("description", ""), "model_description.txt")

    try:
        client.create_registered_model(model_name, description=entry.get("description", ""))
    except Exception:
        pass  # already registered

    logger.info("Registered %s successfully", model_name)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Register all CHRONOS models in MLflow")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", help="Register only a specific model by name")
    parser.add_argument("--tracking-uri", default="http://localhost:5001")
    args = parser.parse_args()

    mlflow.set_tracking_uri(args.tracking_uri)
    client = MlflowClient()
    git_sha = _get_git_sha()
    logger.info("Git SHA: %s", git_sha)

    registry = MODEL_REGISTRY
    if args.model:
        registry = [m for m in registry if m["name"] == args.model]
        if not registry:
            raise SystemExit(f"Model '{args.model}' not in registry")

    for entry in registry:
        try:
            register_model(client, entry, git_sha, dry_run=args.dry_run)
        except Exception:
            logger.exception("Failed to register %s", entry["name"])

    logger.info("Model registration complete (%d models)", len(registry))


if __name__ == "__main__":
    main()
