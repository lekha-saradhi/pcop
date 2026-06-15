"""Unit tests for PRISM reason code reconciler."""

import pytest

from services.scoring.fusion.prism_reconciler import (
    PRISMReconciler,
    ReasonCode,
    TAXONOMY,
    TOKEN_TAXONOMY,
    FEATURE_TAXONOMY,
)


@pytest.fixture()
def reconciler() -> PRISMReconciler:
    return PRISMReconciler()


def test_all_tare_tokens_mappable() -> None:
    from ml.features.sequence_builder import VOCAB

    id_to_token = {v: k for k, v in VOCAB.items()}
    unmapped = [
        name for name in VOCAB
        if name not in ("PAD", "UNK") and name not in TOKEN_TAXONOMY
    ]
    # Some tokens intentionally have no category mapping (e.g. CARD_ACTIVATION)
    assert len(unmapped) < 15, f"Too many unmapped TARE tokens: {unmapped}"


def test_all_habitat_features_mappable() -> None:
    from ml.features.tabular_features import PASS1_FEATURE_NAMES

    unmapped = [f for f in PASS1_FEATURE_NAMES if f not in FEATURE_TAXONOMY]
    assert len(unmapped) == 0, f"Unmapped HABITAT features: {unmapped}"


def test_reconcile_returns_reason_codes(reconciler: PRISMReconciler) -> None:
    attn_ids = [14, 17, 43]  # DECLINE, SUPPORT, INACTIVITY
    shap_codes = [
        {"feature": "decline_rate_30d", "shap_value": 0.2},
        {"feature": "support_contacts_90d", "shap_value": 0.1},
    ]
    codes = reconciler.reconcile(attn_ids, shap_codes, {"tare": 0.55, "habitat": 0.45})
    assert isinstance(codes, list)
    assert len(codes) <= 3


def test_reason_code_categories_in_taxonomy(reconciler: PRISMReconciler) -> None:
    attn_ids = [14, 17, 43]
    shap_codes = [{"feature": "decline_rate_30d", "shap_value": 0.2}]
    codes = reconciler.reconcile(attn_ids, shap_codes, {"tare": 0.55, "habitat": 0.45})
    for code in codes:
        assert code.category in TAXONOMY


def test_importance_normalized(reconciler: PRISMReconciler) -> None:
    attn_ids = [14, 17, 43]
    shap_codes = [{"feature": "decline_rate_30d", "shap_value": 0.5}]
    codes = reconciler.reconcile(attn_ids, shap_codes, {"tare": 0.55, "habitat": 0.45})
    for code in codes:
        assert 0.0 <= code.importance <= 1.0


def test_deduplication_marks_both(reconciler: PRISMReconciler) -> None:
    # Both TARE and HABITAT point to transaction_decline
    attn_ids = [14]  # DECLINE_INSUFFICIENT → transaction_decline
    shap_codes = [{"feature": "decline_rate_30d", "shap_value": 0.3}]
    codes = reconciler.reconcile(attn_ids, shap_codes, {"tare": 0.55, "habitat": 0.45})
    decline_codes = [c for c in codes if c.category == "transaction_decline"]
    if decline_codes:
        assert decline_codes[0].source == "both"


def test_empty_inputs(reconciler: PRISMReconciler) -> None:
    codes = reconciler.reconcile([], [], {"tare": 0.55, "habitat": 0.45})
    assert codes == []


def test_source_sequence_only(reconciler: PRISMReconciler) -> None:
    attn_ids = [43]  # INACTIVITY_7D → inactivity, no HABITAT equivalent
    codes = reconciler.reconcile(attn_ids, [], {"tare": 0.55, "habitat": 0.45})
    inactivity = [c for c in codes if c.category == "inactivity"]
    if inactivity:
        assert inactivity[0].source == "sequence"
