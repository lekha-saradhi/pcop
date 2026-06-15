"""Pydantic models for CHRONOS risk scoring API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ReasonCodeV2(BaseModel):
    category: str
    description: str
    importance: float = Field(ge=0.0, le=1.0)
    source: Literal["sequence", "tabular", "both"]


class ChurnScoreResponse(BaseModel):
    customer_id: str
    final_score: float = Field(ge=0.0, le=1.0)
    risk_tier: Literal["critical", "high", "medium", "low"]
    tare_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    habitat_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    treatability_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    action_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    scoring_pass: Optional[str] = None
    reason_codes: list[str] = Field(default_factory=list)  # legacy TEXT[]
    reason_codes_v2: list[ReasonCodeV2] = Field(default_factory=list)
    anomaly_flag: bool = False
    model_version: str
    scored_at: datetime
    is_cold_start: bool = False


class AttentionWeight(BaseModel):
    position: int
    token: str
    weight: float


class ShapValue(BaseModel):
    feature: str
    shap_value: float
    direction: str


class AnalyzeResponse(ChurnScoreResponse):
    token_count: int = 0
    tabular_features: dict[str, float] = Field(default_factory=dict)
    attention_weights: list[AttentionWeight] = Field(default_factory=list)
    shap_values: list[ShapValue] = Field(default_factory=list)
    fusion_tare_weight: float = 0.0
    fusion_habitat_weight: float = 0.0
    fusion_ci_lower: float = 0.0
    fusion_ci_upper: float = 0.0
    tare_duration_ms: float = 0.0
    habitat_duration_ms: float = 0.0
    fusion_duration_ms: float = 0.0
    prism_duration_ms: float = 0.0
    is_cold_start: bool = False


class ChurnScoreListResponse(BaseModel):
    customers: list[ChurnScoreResponse]
    total: int
    page: int = 1
    page_size: int = 50


class TokenSequenceResponse(BaseModel):
    customer_id: str
    token_ids: list[int]
    time_gaps: list[float]
    token_labels: list[str]
    non_pad_count: int


class ModelComponentStatus(BaseModel):
    name: str
    version: str
    last_updated: Optional[datetime]
    status: Literal["healthy", "degraded", "unavailable"]
    metrics: dict[str, Any] = Field(default_factory=dict)


class ModelHealthResponse(BaseModel):
    fusion_tare_weight: float
    fusion_habitat_weight: float
    fusion_ece: Optional[float]
    fusion_last_calibration: Optional[datetime]
    aegis_drift_status: str
    components: list[ModelComponentStatus]
    overall_status: Literal["healthy", "degraded", "unavailable"]
