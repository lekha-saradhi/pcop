import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timezone
from ..nodes.observe import observe_outcomes
from ..nodes.holdout import run_rescue_check


@pytest.mark.asyncio
async def test_observe_outcomes_full_t1_pass():
    """observe_outcomes T+1 pass writes outcomes for all dispatched customers."""
    dispatched = [
        {
            "customer_id": "C-00000001",
            "outreach_id": 1,
            "dispatched_at": datetime(2024, 11, 1, tzinfo=timezone.utc),
            "holdout_group": False,
            "treatability_score": 0.6,
            "final_score": 0.72,
            "argus_baseline": {"transaction_frequency_mu": 15.0, "churn_score_at_send": 0.72},
        },
    ]

    mock_write = AsyncMock()

    with patch("services.measurement.nodes.observe.get_dispatched_customers_for_window",
               new_callable=AsyncMock, return_value=dispatched), \
         patch("services.measurement.nodes.observe.get_transaction_volume",
               new_callable=AsyncMock, return_value=16.0), \
         patch("services.measurement.nodes.observe.get_engagement_score",
               new_callable=AsyncMock, return_value={"delta_vs_baseline": 0.05}), \
         patch("services.measurement.nodes.observe.get_current_churn_score",
               new_callable=AsyncMock, return_value={"final_score": 0.65}), \
         patch("services.measurement.nodes.observe.get_active_signals",
               new_callable=AsyncMock, return_value=[]), \
         patch("services.measurement.nodes.observe.get_product_closures",
               new_callable=AsyncMock, return_value=[]), \
         patch("services.measurement.nodes.observe.get_balance_change",
               new_callable=AsyncMock, return_value=200.0), \
         patch("services.measurement.nodes.observe.get_tempo_baselines",
               new_callable=AsyncMock, return_value=[]), \
         patch("services.measurement.nodes.observe.write_outcome", mock_write):

        await observe_outcomes(observation_window_days=1)

    mock_write.assert_called_once()
    call_data = mock_write.call_args[0][0]
    assert call_data["customer_id"] == "C-00000001"
    assert call_data["observation_window"] == 1
    assert call_data["outcome_label"] in {"retained", "churned", "partial", "unresponsive"}


@pytest.mark.asyncio
async def test_holdout_rescue_publishes_alarm_to_compass():
    """Rescued holdout customers are published to pcop.alarms.v1 for COMPASS."""
    from .conftest import make_holdout_entry
    holdout = make_holdout_entry(days_ago=5)

    mock_producer = MagicMock()
    mock_producer.produce = MagicMock()
    mock_producer.flush = MagicMock()

    with patch("services.measurement.nodes.holdout.get_active_holdouts",
               new_callable=AsyncMock, return_value=[holdout]), \
         patch("services.measurement.nodes.holdout.get_current_churn_score",
               new_callable=AsyncMock, return_value={"final_score": 0.93}), \
         patch("services.measurement.nodes.holdout.rescue_holdout_customer",
               new_callable=AsyncMock), \
         patch("services.measurement.nodes.holdout.get_kafka_producer",
               return_value=mock_producer):

        await run_rescue_check()

    import json
    call_kwargs = mock_producer.produce.call_args.kwargs
    payload = json.loads(call_kwargs["value"].decode("utf-8"))
    assert payload["rescue_from_holdout"] is True
    assert payload["alarm_severity"] == "CRITICAL"
    assert payload["customer_id"] == holdout["customer_id"]
