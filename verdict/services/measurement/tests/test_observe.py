import pytest
from ..nodes.observe import _derive_outcome_label, _measure_single_customer
from unittest.mock import AsyncMock, patch
from datetime import date


def test_outcome_label_churned():
    label = _derive_outcome_label(
        churn_score=0.85, score_reduction=0.05,
        products_closed=1, signals_cleared=False,
    )
    assert label == "churned"


def test_outcome_label_retained():
    label = _derive_outcome_label(
        churn_score=0.32, score_reduction=0.15,
        products_closed=0, signals_cleared=True,
    )
    assert label == "retained"


def test_outcome_label_partial_medium_score():
    label = _derive_outcome_label(
        churn_score=0.55, score_reduction=0.08,
        products_closed=0, signals_cleared=False,
    )
    assert label == "partial"


def test_outcome_label_unresponsive():
    label = _derive_outcome_label(
        churn_score=0.78, score_reduction=0.01,
        products_closed=0, signals_cleared=False,
    )
    assert label == "unresponsive"


def test_outcome_label_products_closed_overrides_score():
    # Even if score improved, product closure means churned
    label = _derive_outcome_label(
        churn_score=0.30, score_reduction=0.20,
        products_closed=2, signals_cleared=True,
    )
    assert label == "churned"


@pytest.mark.asyncio
async def test_measure_single_customer_uses_tempo_baseline():
    """Outcome uses pre-alarm TEMPO baseline, not post-alarm state."""
    with patch("services.measurement.nodes.observe.get_transaction_volume", new_callable=AsyncMock, return_value=18.0), \
         patch("services.measurement.nodes.observe.get_engagement_score", new_callable=AsyncMock, return_value={"delta_vs_baseline": 0.1}), \
         patch("services.measurement.nodes.observe.get_current_churn_score", new_callable=AsyncMock, return_value={"final_score": 0.35}), \
         patch("services.measurement.nodes.observe.get_active_signals", new_callable=AsyncMock, return_value=[]), \
         patch("services.measurement.nodes.observe.get_product_closures", new_callable=AsyncMock, return_value=[]), \
         patch("services.measurement.nodes.observe.get_balance_change", new_callable=AsyncMock, return_value=500.0), \
         patch("services.measurement.nodes.observe.get_tempo_baselines", new_callable=AsyncMock, return_value=[]):

        result = await _measure_single_customer(
            customer_id="C-00000001",
            send_date=date(2024, 11, 1),
            observation_window=30,
            pre_alarm_baseline={"transaction_frequency_mu": 15.0, "churn_score_at_send": 0.72},
        )

    # txn_volume_change should compare 18 vs baseline of 15 → +20%
    assert result["txn_volume_change"] == pytest.approx(20.0, abs=0.1)
    # score_reduction = 0.72 (at send) - 0.35 (now) = 0.37
    assert result["score_reduction"] == pytest.approx(0.37, abs=0.01)
    assert result["signals_cleared"] is True
    assert result["outcome_label"] == "retained"


@pytest.mark.asyncio
async def test_measure_single_customer_no_baseline():
    """Handles None baseline gracefully."""
    with patch("services.measurement.nodes.observe.get_transaction_volume", new_callable=AsyncMock, return_value=10.0), \
         patch("services.measurement.nodes.observe.get_engagement_score", new_callable=AsyncMock, return_value={"delta_vs_baseline": 0.0}), \
         patch("services.measurement.nodes.observe.get_current_churn_score", new_callable=AsyncMock, return_value={"final_score": 0.60}), \
         patch("services.measurement.nodes.observe.get_active_signals", new_callable=AsyncMock, return_value=[{"signal_type": "tempo_txn"}]), \
         patch("services.measurement.nodes.observe.get_product_closures", new_callable=AsyncMock, return_value=[]), \
         patch("services.measurement.nodes.observe.get_balance_change", new_callable=AsyncMock, return_value=0.0), \
         patch("services.measurement.nodes.observe.get_tempo_baselines", new_callable=AsyncMock, return_value=[]):

        result = await _measure_single_customer(
            customer_id="C-00000002",
            send_date=date(2024, 11, 1),
            observation_window=7,
            pre_alarm_baseline=None,
        )

    assert result["outcome_label"] in {"retained", "churned", "partial", "unresponsive"}
    assert result["active_signal_count"] == 1
    assert result["signals_cleared"] is False
