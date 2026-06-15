"""Unit tests for batch scoring orchestrator."""

import pytest

from services.scoring.serving.batch_scorer import (
    BatchScorer,
    CustomerRecord,
    _assign_tier,
    RISK_TIERS,
)


def _make_record(customer_id: str = "C1", tenure_days: int = 200) -> CustomerRecord:
    return CustomerRecord(
        customer_id=customer_id,
        token_ids=[0] * 150 + [2, 3, 6, 7, 11] * 6,
        time_gaps=[0.0] * 180,
        tabular_features={
            "recency_days": 5.0,
            "monetary_avg": 1200.0,
            "monetary_total": 36000.0,
            "frequency_30d": 8.0,
            "frequency_90d": 22.0,
            "decline_rate_30d": 0.05,
            "support_contacts_90d": 2.0,
            "inactivity_streak_days": 0.0,
            "product_count": 3.0,
            "digital_ratio": 0.7,
            "avg_utilization": 0.4,
            "complaint_open_count": 0.0,
            "tenure_days": float(tenure_days),
            "channel_diversity": 2.0,
        },
        tenure_days=tenure_days,
    )


def test_tier_assignment_boundaries() -> None:
    assert _assign_tier(0.85) == "critical"
    assert _assign_tier(0.70) == "high"
    assert _assign_tier(0.50) == "medium"
    assert _assign_tier(0.10) == "low"


def test_tier_assignment_boundaries_exact() -> None:
    assert _assign_tier(0.80) == "critical"
    assert _assign_tier(0.60) == "high"
    assert _assign_tier(0.35) == "medium"
    assert _assign_tier(0.00) == "low"


def test_run_pipeline_with_dummy_records() -> None:
    scorer = BatchScorer()
    records = [_make_record(f"C{i}") for i in range(5)]
    results = scorer.run_full_pipeline(records)

    assert len(results) == 5
    for r in results:
        assert r.customer_id.startswith("C")
        assert 0.0 <= r.final_score <= 1.0
        assert r.risk_tier in RISK_TIERS


def test_cold_start_routing() -> None:
    from ml.features.sequence_builder import is_cold_start

    scorer = BatchScorer()
    cold_record = CustomerRecord(
        customer_id="COLD",
        token_ids=[0] * 175 + [2] * 5,  # only 5 non-PAD → cold start
        time_gaps=[0.0] * 180,
        tabular_features={
            "tenure_days": 30.0,
            "product_count": 2.0,
            "age_bucket": 1.0,
            "income_band": 2.0,
            "channel_acquisition": 1.0,
            "credit_score_band": 3.0,
            "city_tier": 1.0,
        },
        tenure_days=30,
    )

    assert is_cold_start(cold_record.token_ids) is True
    result = scorer._score_single(cold_record)
    assert result.is_cold_start is True
