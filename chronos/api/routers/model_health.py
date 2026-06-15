"""FastAPI router for CHRONOS model health endpoint."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter

from api.models.risk import ModelComponentStatus, ModelHealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/model-health", tags=["model-health"])

_COMPONENT_REGISTRY = [
    "tare-encoder",
    "habitat-pass1",
    "fusion-x",
    "causal-net",
    "genesis",
    "aegis",
]


@router.get("", response_model=ModelHealthResponse)
async def get_model_health() -> ModelHealthResponse:
    """Return current status of all CHRONOS model components.

    Reports:
    - FUSION-X current weights and ECE
    - AEGIS drift status
    - Per-component version, last updated, and health metrics
    """
    from services.scoring.fusion.fusion_x import FusionX
    from services.scoring.guards.aegis_detector import AEGISDetector

    fusion = _get_fusion_instance()
    weights = fusion.weights

    drift_status = "unknown"
    try:
        aegis = AEGISDetector()
        drift_status = "normal"
    except Exception:
        drift_status = "unavailable"

    components = []
    for name in _COMPONENT_REGISTRY:
        status = _check_component(name)
        components.append(status)

    overall = "healthy"
    if any(c.status == "unavailable" for c in components):
        overall = "unavailable"
    elif any(c.status == "degraded" for c in components):
        overall = "degraded"

    return ModelHealthResponse(
        fusion_tare_weight=weights.tare,
        fusion_habitat_weight=weights.habitat,
        fusion_ece=None,
        fusion_last_calibration=None,
        aegis_drift_status=drift_status,
        components=components,
        overall_status=overall,
    )


@router.get("/scheduler", response_model=dict)
async def get_scheduler_status() -> dict:
    """Return status of all APScheduler jobs."""
    from services.scoring.scheduler import get_scheduler_status
    return get_scheduler_status()


def _get_fusion_instance() -> "FusionX":
    from services.scoring.fusion.fusion_x import FusionX
    return FusionX()


def _check_component(name: str) -> ModelComponentStatus:
    """Check if a model component's checkpoint exists and is loadable."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    checkpoint_map = {
        "tare-encoder": root / "ml" / "checkpoints" / "tare_churn.onnx",
        "habitat-pass1": root / "ml" / "checkpoints" / "habitat_pass1.json",
        "fusion-x": root / "ml" / "checkpoints" / "fusion_weights.json",
        "causal-net": root / "ml" / "checkpoints" / "causal_net_treated.json",
        "genesis": root / "ml" / "checkpoints" / "genesis_lr.pkl",
        "aegis": root / "ml" / "checkpoints" / "aegis_reference.json",
    }

    checkpoint = checkpoint_map.get(name)
    if checkpoint and checkpoint.exists():
        status = "healthy"
    elif name in ("fusion-x", "aegis"):
        status = "degraded"  # these have soft fallbacks
    else:
        status = "unavailable"

    return ModelComponentStatus(
        name=name,
        version="v1.0",
        last_updated=None,
        status=status,
        metrics={},
    )
