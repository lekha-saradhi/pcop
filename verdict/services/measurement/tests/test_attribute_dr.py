import pytest
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch
from ..nodes.attribute import attribute_uplift, attribute_by_content_strategy, _derive_outcome_label_for_test


def _make_df(n=120, seed=42):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "customer_id": [f"C-{i:08d}" for i in range(n)],
        "treatment": rng.integers(0, 2, n),
        "outcome_label": rng.choice(["retained", "partial", "churned"], n),
        "churn_score_at_measure": rng.uniform(0.2, 0.8, n),
        "score_reduction": rng.uniform(-0.1, 0.3, n),
        "treatability_score_at_send": rng.uniform(0.2, 0.9, n),
        "final_score_at_send": rng.uniform(0.5, 0.95, n),
        "tenure_years": rng.uniform(0.5, 15, n),
        "num_active_products": rng.integers(1, 6, n),
        "digital_ratio": rng.uniform(0.1, 1.0, n),
        "complaint_count_90d": rng.integers(0, 5, n),
        "recency_days": rng.integers(1, 90, n),
        "frequency_monthly": rng.uniform(2, 30, n),
        "monetary_avg": rng.uniform(500, 50000, n),
        "active_signal_count": rng.integers(0, 4, n),
        "life_event_count_at_send": rng.integers(0, 3, n),
        "content_strategy": rng.choice(["full_retention", "graceful_retention"], n),
    })


@pytest.mark.asyncio
async def test_attribute_uplift_skips_below_50():
    """attribute_uplift skips and warns when n < 50."""
    small_df = _make_df(n=20)
    with patch("services.measurement.nodes.attribute.get_attribution_dataset",
               new_callable=AsyncMock, return_value=small_df), \
         patch("services.measurement.nodes.attribute.write_uplift_results",
               new_callable=AsyncMock) as mock_write:

        await attribute_uplift("camp-001", "email", "mass_affluent", "high")

    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_attribute_uplift_runs_with_sufficient_data():
    """attribute_uplift calls write_uplift_results when n >= 50."""
    df = _make_df(n=120)
    with patch("services.measurement.nodes.attribute.get_attribution_dataset",
               new_callable=AsyncMock, return_value=df), \
         patch("services.measurement.nodes.attribute.write_uplift_results",
               new_callable=AsyncMock) as mock_write, \
         patch("services.measurement.nodes.attribute._publish_causal_net_signal",
               new_callable=AsyncMock):

        await attribute_uplift("camp-001", "email", "mass_affluent", "high")

    mock_write.assert_called_once()
    call_data = mock_write.call_args[0][0]
    assert "dr_uplift" in call_data
    assert "overestimation_bias" in call_data
    assert call_data["estimator"] == "DR-Learner"


@pytest.mark.asyncio
async def test_causal_net_calibration_check_published():
    """CAUSAL-NET calibration signal is published when both high/low estimates exist."""
    df = _make_df(n=120)
    # Ensure both high and low treatability groups exist
    df["treatability_score_at_send"] = [0.7 if i % 2 == 0 else 0.3 for i in range(len(df))]

    with patch("services.measurement.nodes.attribute.get_attribution_dataset",
               new_callable=AsyncMock, return_value=df), \
         patch("services.measurement.nodes.attribute.write_uplift_results",
               new_callable=AsyncMock), \
         patch("services.measurement.nodes.attribute._publish_causal_net_signal",
               new_callable=AsyncMock) as mock_publish:

        await attribute_uplift("camp-001", "email", "mass_affluent", "high")

    mock_publish.assert_called_once()
    kwargs = mock_publish.call_args.kwargs
    assert "causal_net_calibrated" in kwargs
    assert isinstance(kwargs["causal_net_calibrated"], bool)


@pytest.mark.asyncio
async def test_overestimation_bias_is_naive_minus_dr():
    """Overestimation bias = naive uplift - DR uplift."""
    df = _make_df(n=120)
    with patch("services.measurement.nodes.attribute.get_attribution_dataset",
               new_callable=AsyncMock, return_value=df), \
         patch("services.measurement.nodes.attribute.write_uplift_results",
               new_callable=AsyncMock) as mock_write, \
         patch("services.measurement.nodes.attribute._publish_causal_net_signal",
               new_callable=AsyncMock):

        await attribute_uplift("camp-001", "email", "mass_affluent", "high")

    data = mock_write.call_args[0][0]
    assert abs(data["overestimation_bias"] - (data["naive_uplift"] - data["dr_uplift"])) < 1e-6


@pytest.mark.asyncio
async def test_content_strategy_attribution_slices():
    """attribute_by_content_strategy runs for each strategy slice."""
    df = _make_df(n=90)  # 30 per strategy
    with patch("services.measurement.nodes.attribute.get_attribution_dataset",
               new_callable=AsyncMock, return_value=df), \
         patch("services.measurement.nodes.attribute._attribute_uplift_slice",
               new_callable=AsyncMock) as mock_slice:

        await attribute_by_content_strategy("camp-001")

    assert mock_slice.call_count == 3
    called_labels = {c.kwargs.get("label") or c.args[1] for c in mock_slice.call_args_list}
    assert "strategy_full_retention" in called_labels
    assert "strategy_graceful_retention" in called_labels
    assert "strategy_proactive" in called_labels


def _derive_outcome_label_for_test(*args, **kwargs):
    """Alias for import in test — tests the observe module's function directly."""
    from ..nodes.observe import _derive_outcome_label
    return _derive_outcome_label(*args, **kwargs)
