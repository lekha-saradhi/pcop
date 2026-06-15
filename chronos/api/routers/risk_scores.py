"""FastAPI router for CHRONOS risk score endpoints."""

from __future__ import annotations

import logging
from collections.abc import Generator
from datetime import date, datetime
from typing import Annotated, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.models.risk import AnalyzeResponse, ChurnScoreListResponse, ChurnScoreResponse, ReasonCodeV2, TokenSequenceResponse
from ml.features.sequence_builder import VOCAB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scores", tags=["risk-scores"])


def _get_db() -> Generator[Session, None, None]:
    from api.database import get_db
    yield from get_db()


@router.get("/{customer_id}", response_model=ChurnScoreResponse)
async def get_customer_score(
    customer_id: str,
    db: Annotated[Session, Depends(_get_db)] = None,  # type: ignore[assignment]
) -> ChurnScoreResponse:
    """Return the latest CHRONOS score for a single customer.

    Includes TARE, HABITAT, treatability, action score, reason codes v2, and anomaly flag.
    """
    row = _fetch_latest_score(customer_id, db)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No score found for customer {customer_id}")
    return _row_to_response(row)


@router.get("", response_model=ChurnScoreListResponse)
async def list_scores(
    anomaly_only: bool = Query(default=False, description="Return only customers with anomaly_flag=TRUE"),
    tier: Optional[str] = Query(default=None, description="Comma-separated risk tiers, e.g. critical,high"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Annotated[Session, Depends(_get_db)] = None,  # type: ignore[assignment]
) -> ChurnScoreListResponse:
    """List churn scores with optional filtering by tier and anomaly flag."""
    tiers = [t.strip() for t in tier.split(",")] if tier else None
    rows, total = _fetch_score_list(db, anomaly_only=anomaly_only, tiers=tiers, page=page, page_size=page_size)
    return ChurnScoreListResponse(
        customers=[_row_to_response(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{customer_id}/token-sequence", response_model=TokenSequenceResponse)
async def get_token_sequence(
    customer_id: str,
    as_of_date_str: Optional[str] = Query(default=None, description="Override the as_of_date (YYYY-MM-DD)"),
    db: Annotated[Session, Depends(_get_db)] = None,  # type: ignore[assignment]
) -> TokenSequenceResponse:
    """Build the TARE token sequence for a customer from live bank data."""
    bank_api = "http://localhost:3001/api"

    if as_of_date_str:
        as_of_date = date.fromisoformat(as_of_date_str)
    else:
        as_of_date = date.today()

    def _get(url: str, params: dict | None = None) -> dict:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    try:
        cust = _get(f"{bank_api}/core-banking/customers/{customer_id}")["data"]
        txns = _get(f"{bank_api}/core-banking/transactions", {"customer_id": customer_id, "limit": 1000})["data"]
        acct_evts = _get(f"{bank_api}/core-banking/account-events", {"customer_id": customer_id})["data"]
        app_evts = _get(f"{bank_api}/app-events", {"customer_id": customer_id, "limit": 500})["data"]
        crm_notes = _get(f"{bank_api}/crm/notes", {"customer_id": customer_id, "limit": 100})["data"]
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Bank API unavailable: {e}")

    from services.scoring.serving.bank_loader import _build_token_sequence
    token_ids, time_gaps = _build_token_sequence(cust, txns, acct_evts, app_evts, crm_notes, as_of_date)

    id_to_name = {v: k for k, v in VOCAB.items()}
    token_labels = [id_to_name.get(tid, "?") for tid in token_ids]
    non_pad_count = sum(1 for t in token_ids if t != 0)

    return TokenSequenceResponse(
        customer_id=customer_id,
        token_ids=token_ids,
        time_gaps=time_gaps,
        token_labels=token_labels,
        non_pad_count=non_pad_count,
    )


@router.post("/{customer_id}/analyze", response_model=AnalyzeResponse)
async def analyze_customer(
    customer_id: str,
    db: Annotated[Session, Depends(_get_db)] = None,
) -> AnalyzeResponse:
    """Run the full CHRONOS pipeline for a single customer on-demand.

    Fetches live data from the bank API, extracts features, scores with
    TARE + HABITAT + FusionX, generates PRISM reason codes, persists to
    the database, and returns the scored result with full diagnostics.
    """
    bank_api = "http://localhost:3001/api"
    as_of_date = date.today()

    from services.scoring.serving.bank_loader import (
        _build_tabular_features, _build_token_sequence,
        _fetch_account_events, _fetch_app_events, _fetch_crm_notes,
        _fetch_customer_full, _fetch_customers, _fetch_transaction_summary,
        _fetch_transactions,
    )
    from services.scoring.serving.batch_scorer import (
        CustomerRecord, BatchScorer, write_scores_to_db,
    )

    try:
        cust = next((c for c in _fetch_customers() if c["customer_id"] == customer_id), None)
        if cust is None:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found in bank API")

        customer_full = _fetch_customer_full(customer_id)
        transactions = _fetch_transactions(customer_id)
        txn_summary = _fetch_transaction_summary(customer_id)
        account_events = _fetch_account_events(customer_id)
        app_events = _fetch_app_events(customer_id)
        crm_notes = _fetch_crm_notes(customer_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bank API error: {e}")

    import requests
    enrichment_raw = {}
    try:
        enrichment_raw = requests.get(
            f"{bank_api}/enrichment/{customer_id}", timeout=10
        ).json().get("data", {})
    except Exception:
        pass

    token_ids, time_gaps = _build_token_sequence(
        cust, transactions, account_events, app_events, crm_notes, as_of_date,
    )
    tabular_features = _build_tabular_features(
        cust, customer_full, transactions, txn_summary, crm_notes,
        account_events, enrichment_raw, as_of_date,
    )

    record = CustomerRecord(
        customer_id=customer_id,
        token_ids=token_ids,
        time_gaps=time_gaps,
        tabular_features=tabular_features,
        tenure_days=int(cust.get("tenure_years", 0)) * 365,
    )

    from pathlib import Path
    tare_path = Path("ml/checkpoints/tare_churn.onnx")
    scorer = BatchScorer(
        tare_onnx_path=str(tare_path) if tare_path.exists() else None,
    )

    result, diag = scorer._score_single_debug(record)

    write_scores_to_db([result], scoring_pass="ondemand")

    return _diag_to_response(result, diag)


@router.get("/{customer_id}/reason-codes", response_model=list[ReasonCodeV2])
async def get_reason_codes(
    customer_id: str,
    db: Annotated[Session, Depends(_get_db)] = None,  # type: ignore[assignment]
) -> list[ReasonCodeV2]:
    """Return the full PRISM reason_codes_v2 in structured format."""
    row = _fetch_latest_score(customer_id, db)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No score found for customer {customer_id}")
    raw_v2 = row.get("reason_codes_v2") or []
    return [ReasonCodeV2(**rc) for rc in raw_v2]


def _fetch_latest_score(customer_id: str, db: Session | None) -> dict | None:
    """Fetch the most recent churn_scores row for a customer."""
    if db is None:
        return None
    row = db.execute(
        text("SELECT * FROM churn_scores WHERE customer_id = :cid ORDER BY scored_at DESC LIMIT 1"),
        {"cid": customer_id},
    ).fetchone()
    return dict(row._mapping) if row else None


def _fetch_score_list(
    db: Session | None,
    anomaly_only: bool,
    tiers: list[str] | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    if db is None:
        return [], 0
    conditions = []
    params: dict = {}
    if anomaly_only:
        conditions.append("anomaly_flag = TRUE")
    if tiers:
        conditions.append("risk_tier = ANY(:tiers)")
        params["tiers"] = tiers
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size
    sql = text(f"SELECT * FROM churn_scores {where} ORDER BY scored_at DESC LIMIT :lim OFFSET :off")
    rows = db.execute(sql, {**params, "lim": page_size, "off": offset}).fetchall()
    count_sql = text(f"SELECT COUNT(*) FROM churn_scores {where}")
    total = db.execute(count_sql, params).scalar()
    return [dict(r._mapping) for r in rows], int(total)


def _diag_to_response(s: "ScoredCustomer", d: "ScoreDiagnostics") -> AnalyzeResponse:
    from services.scoring.serving.batch_scorer import ScoredCustomer, ScoreDiagnostics
    from api.models.risk import AttentionWeight, ShapValue
    return AnalyzeResponse(
        customer_id=s.customer_id,
        final_score=s.final_score,
        risk_tier=s.risk_tier,
        tare_score=s.tare_score,
        habitat_score=s.habitat_score,
        reason_codes_v2=[ReasonCodeV2(**rc) for rc in s.reason_codes],
        model_version=s.model_version,
        scored_at=datetime.utcnow(),
        is_cold_start=s.is_cold_start,
        anomaly_flag=s.anomaly_flag,
        token_count=d.token_count,
        tabular_features=d.tabular_features,
        attention_weights=[AttentionWeight(**a) for a in d.attention_weights],
        shap_values=[ShapValue(**sv) for sv in d.shap_values],
        fusion_tare_weight=d.fusion_tare_weight,
        fusion_habitat_weight=d.fusion_habitat_weight,
        fusion_ci_lower=d.fusion_ci_lower,
        fusion_ci_upper=d.fusion_ci_upper,
        tare_duration_ms=d.tare_duration_ms,
        habitat_duration_ms=d.habitat_duration_ms,
        fusion_duration_ms=d.fusion_duration_ms,
        prism_duration_ms=d.prism_duration_ms,
    )


def _scored_to_response(s: "ScoredCustomer") -> ChurnScoreResponse:
    from services.scoring.serving.batch_scorer import ScoredCustomer
    return ChurnScoreResponse(
        customer_id=s.customer_id,
        final_score=s.final_score,
        risk_tier=s.risk_tier,
        tare_score=s.tare_score,
        habitat_score=s.habitat_score,
        reason_codes_v2=[ReasonCodeV2(**rc) for rc in s.reason_codes],
        model_version=s.model_version,
        scored_at=datetime.utcnow(),
        is_cold_start=s.is_cold_start,
        anomaly_flag=s.anomaly_flag,
    )


def _row_to_response(row: dict) -> ChurnScoreResponse:
    raw_v2 = row.get("reason_codes_v2") or []
    codes_v2 = [ReasonCodeV2(**rc) for rc in raw_v2] if raw_v2 else []
    return ChurnScoreResponse(
        customer_id=str(row["customer_id"]),
        final_score=float(row.get("final_score") or row.get("tare_score") or 0.0),
        risk_tier=row.get("risk_tier", "low"),
        tare_score=row.get("tare_score"),
        habitat_score=row.get("habitat_score"),
        treatability_score=row.get("treatability_score"),
        action_score=row.get("action_score"),
        scoring_pass=row.get("scoring_pass"),
        reason_codes=list(row.get("reason_codes") or []),
        reason_codes_v2=codes_v2,
        anomaly_flag=bool(row.get("anomaly_flag", False)),
        model_version=row.get("model_version", "unknown"),
        scored_at=row.get("scored_at") or datetime.utcnow(),
        is_cold_start=bool(row.get("is_cold_start", False)),
    )
