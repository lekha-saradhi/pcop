"""
Canonical schemas shared across all Layer 2 detection agents.
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------- Input event schema (from Kafka) ----------
class CanonicalEvent(BaseModel):
    event_id: str
    customer_id: str
    event_type: str
    event_timestamp: datetime
    source_system: str
    payload: dict[str, Any]
    schema_version: str = "1.0"


# ---------- Baseline (loaded from DB at agent startup) ----------
class Baseline(BaseModel):
    mu_0: float
    sigma: float
    computed_from: Optional[str] = None
    lambda_0: Optional[float] = None  # For Poisson agents


# ---------- Output schemas ----------
class SignalResult(BaseModel):
    """One row written to signal_results table + one Kafka message."""
    customer_id: str
    signal_type: str
    detected: bool
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    raw_data: dict[str, Any]
    cusum_value: Optional[float] = None
    alarm_threshold: Optional[float] = None
    method_used: str
    evaluated_at: datetime


class AlarmMessage(BaseModel):
    """Published to pcop.alarms.v1 Kafka topic."""
    alarm_id: str
    customer_id: str
    signal_type: str
    method_used: str
    detected: bool
    confidence: float
    cusum_value: Optional[float]
    alarm_threshold: Optional[float]
    evidence: list[str]
    raw_data: dict[str, Any]
    evaluated_at: datetime
