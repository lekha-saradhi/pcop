"""End-to-end integration tests using the 20 dummy customers from conftest."""

from __future__ import annotations

import pytest


class TestFullPipeline:
    """test_full_pipeline — score all 20 customers through batch_scorer."""

    def test_all_customers_scored(self, dummy_customers: list[dict]) -> None:
        from services.scoring.serving.batch_scorer import BatchScorer, CustomerRecord

        scorer = BatchScorer()
        records = [
            CustomerRecord(
                customer_id=c["customer_id"],
                token_ids=c["token_ids"],
                time_gaps=c["time_gaps"],
                tabular_features=c["tabular_features"],
                tenure_days=c["tenure_days"],
            )
            for c in dummy_customers
        ]
        results = scorer.run_full_pipeline(records)

        assert len(results) == len(dummy_customers)
        for r in results:
            assert 0.0 <= r.final_score <= 1.0
            assert r.risk_tier in ("critical", "high", "medium", "low")


class TestColdStartRouting:
    """test_cold_start_routing — customer with 30 days tenure routes to GENESIS."""

    def test_cold_start_goes_to_genesis(self, cold_start_customer: dict) -> None:
        from services.scoring.serving.batch_scorer import BatchScorer, CustomerRecord
        from ml.features.sequence_builder import is_cold_start

        assert is_cold_start(cold_start_customer["token_ids"]) is True

        scorer = BatchScorer()
        record = CustomerRecord(
            customer_id=cold_start_customer["customer_id"],
            token_ids=cold_start_customer["token_ids"],
            time_gaps=cold_start_customer["time_gaps"],
            tabular_features=cold_start_customer["tabular_features"],
            tenure_days=cold_start_customer["tenure_days"],
        )
        result = scorer._score_single(record)

        assert result.is_cold_start is True
        assert result.tare_score is None
        assert result.habitat_score is None


class TestGraduation:
    """test_graduation — customer crossing 90 days re-scored via TARE+HABITAT."""

    def test_graduation_check(self) -> None:
        from services.scoring.models.genesis_scorer import GENESISScorer

        scorer = GENESISScorer()
        assert scorer.is_graduated(tenure_days=91, token_count=35) is True
        assert scorer.is_graduated(tenure_days=30, token_count=35) is False
        assert scorer.is_graduated(tenure_days=91, token_count=10) is False


class TestPass2Trigger:
    """test_pass2_trigger and test_pass2_skip."""

    def test_pass2_triggered_when_eligible(self) -> None:
        from services.scoring.models.habitat_pass2 import is_eligible_for_pass2

        assert is_eligible_for_pass2(pass1_score=0.50, life_event_count=1) is True
        assert is_eligible_for_pass2(pass1_score=0.50, life_event_count=2) is True

    def test_pass2_skipped_low_score(self) -> None:
        from services.scoring.models.habitat_pass2 import is_eligible_for_pass2

        assert is_eligible_for_pass2(pass1_score=0.20, life_event_count=3) is False

    def test_pass2_skipped_no_life_events(self) -> None:
        from services.scoring.models.habitat_pass2 import is_eligible_for_pass2

        assert is_eligible_for_pass2(pass1_score=0.50, life_event_count=0) is False


class TestRealtimeTrigger:
    """test_realtime_trigger — SENTINEL trigger logic."""

    def test_triggers_on_closure_request(self) -> None:
        from services.scoring.serving.sentinel_realtime import _should_trigger

        event = {"event_type": "ACCOUNT_CLOSURE_REQUEST", "customer_id": "C1"}
        assert _should_trigger(event, current_score=0.2, is_high_tier=False) is True

    def test_triggers_on_high_score(self) -> None:
        from services.scoring.serving.sentinel_realtime import _should_trigger

        event = {"event_type": "CARD_SWIPE", "customer_id": "C1"}
        assert _should_trigger(event, current_score=0.85, is_high_tier=False) is True

    def test_no_trigger_low_risk(self) -> None:
        from services.scoring.serving.sentinel_realtime import _should_trigger

        event = {"event_type": "CARD_SWIPE", "customer_id": "C1"}
        assert _should_trigger(event, current_score=0.20, is_high_tier=False) is False


class TestDriftDetection:
    """test_drift_detection — AEGIS flags shifted features."""

    def test_feature_drift_detected(self) -> None:
        import numpy as np
        from services.scoring.guards.aegis_detector import AEGISDetector, DriftType

        detector = AEGISDetector()
        n_features = 5
        feature_names = [f"f{i}" for i in range(n_features)]
        reference = np.random.default_rng(0).normal(0, 1, (1000, n_features)).astype(np.float32)
        detector.fit_reference(reference, feature_names, set(range(50)))

        # Inject 3σ shift in feature 0
        shifted = reference.copy()
        shifted[:, 0] += 6.0

        alerts = detector.check_features(shifted, feature_names)
        alert_types = [a.type for a in alerts]
        assert DriftType.FEATURE_DRIFT in alert_types

    def test_novel_token_flagged(self) -> None:
        from services.scoring.guards.aegis_detector import AEGISDetector, DriftType

        detector = AEGISDetector()
        detector._training_token_vocab = set(range(50))

        # 50% novel tokens (well above 5% threshold)
        sequences = [[1, 2, 3, 100, 200, 300] for _ in range(100)]
        alerts = detector.check_sequences(sequences)
        assert any(a.type == DriftType.VOCAB_DRIFT for a in alerts)


class TestReasonCodeFormat:
    """test_reason_code_format — PRISM output matches ReasonCode schema."""

    def test_reason_code_schema(self) -> None:
        from services.scoring.fusion.prism_reconciler import PRISMReconciler, ReasonCode

        reconciler = PRISMReconciler()
        attention_ids = [14, 17, 43]  # DECLINE_INSUFFICIENT, SUPPORT_CONTACT, INACTIVITY_7D
        shap_codes = [
            {"feature": "decline_rate_30d", "shap_value": 0.15, "direction": "increases_risk"},
            {"feature": "support_contacts_90d", "shap_value": 0.10, "direction": "increases_risk"},
        ]
        weights = {"tare": 0.55, "habitat": 0.45}

        codes = reconciler.reconcile(attention_ids, shap_codes, weights)
        assert isinstance(codes, list)
        for code in codes:
            assert isinstance(code, ReasonCode)
            assert code.category in (
                "transaction_decline", "engagement_drop", "complaint_escalation",
                "financial_stress", "income_change", "competitor_risk",
                "location_change", "product_disengagement", "inactivity",
            )
            assert 0.0 <= code.importance <= 1.0
            assert code.source in ("sequence", "tabular", "both")


class TestTreatabilityDefault:
    """test_treatability_default — before CAUSAL-NET training, treatability=0.5."""

    def test_default_treatability(self) -> None:
        import torch
        from services.scoring.models.causal_net import CausalNet, DEFAULT_TREATABILITY

        model = CausalNet(tare_checkpoint=None)  # no checkpoint → default mode
        ids = torch.zeros(1, 180, dtype=torch.long)
        gaps = torch.zeros(1, 180, dtype=torch.float32)
        tabular = torch.zeros(1, 14, dtype=torch.float32)
        treatment = torch.zeros(1, 1, dtype=torch.float32)

        p_churn, p_treatable, action_score = model(ids, gaps, tabular, treatment)
        assert abs(float(p_treatable[0]) - DEFAULT_TREATABILITY) < 1e-5
        assert abs(float(action_score[0]) - float(p_churn[0]) * DEFAULT_TREATABILITY) < 1e-5


class TestFusionWeights:
    """Verify FUSION-X weights sum to 1."""

    def test_weights_sum_to_one(self) -> None:
        from services.scoring.fusion.fusion_x import FusionX

        fusion = FusionX()
        w = fusion.weights
        assert abs(w.tare + w.habitat - 1.0) < 1e-9

    def test_static_fallback_when_few_outcomes(self) -> None:
        from services.scoring.fusion.fusion_x import FusionX, STATIC_TARE_WEIGHT, STATIC_HABITAT_WEIGHT

        fusion = FusionX()
        fusion.calibrate([0.5] * 10, [0.4] * 10, [0] * 5 + [1] * 5)
        assert abs(fusion.weights.tare - STATIC_TARE_WEIGHT) < 1e-6
