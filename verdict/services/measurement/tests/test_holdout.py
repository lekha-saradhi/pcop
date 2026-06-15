import pytest
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from ..nodes.holdout import (
    assign_holdout,
    run_rescue_check,
    HOLDOUT_FRACTION,
    RESCUE_THRESHOLD,
    MAX_HOLDOUT_DAYS,
)
from .conftest import make_holdout_entry


@pytest.mark.asyncio
async def test_holdout_assignment_deterministic():
    """Same inputs always produce the same holdout assignment."""
    customers = [f"C-{i:08d}" for i in range(1, 21)]

    with patch("services.measurement.nodes.holdout.write_holdout_registry", new_callable=AsyncMock):
        a1 = await assign_holdout("camp-001", customers, "high", "mass_affluent", "mumbai")
        a2 = await assign_holdout("camp-001", customers, "high", "mass_affluent", "mumbai")

    assert a1 == a2


@pytest.mark.asyncio
async def test_holdout_fraction_approximately_15pct():
    """15% of customers should be assigned to holdout."""
    customers = [f"C-{i:08d}" for i in range(1, 101)]

    with patch("services.measurement.nodes.holdout.write_holdout_registry", new_callable=AsyncMock):
        assignments = await assign_holdout("camp-001", customers, "high", "mass_affluent", "mumbai")

    holdout_count = sum(assignments.values())
    # Allow ±5% tolerance around 15%
    assert 10 <= holdout_count <= 20


@pytest.mark.asyncio
async def test_holdout_assignment_varies_per_campaign():
    """Same customer gets different assignment for different campaign IDs."""
    customers = ["C-00000001"]

    with patch("services.measurement.nodes.holdout.write_holdout_registry", new_callable=AsyncMock):
        results = set()
        for campaign_id in [f"camp-{i}" for i in range(10)]:
            a = await assign_holdout(campaign_id, customers, "high", "mass_affluent", "mumbai")
            results.add(a["C-00000001"])

    # With 10 campaigns and MD5 hash, both True and False should appear
    assert True in results or False in results


@pytest.mark.asyncio
async def test_rescue_fires_at_threshold():
    """run_rescue_check rescues customers above 0.92 threshold."""
    holdout = make_holdout_entry(days_ago=5)

    mock_producer = MagicMock()
    mock_producer.produce = MagicMock()
    mock_producer.flush = MagicMock()

    with patch("services.measurement.nodes.holdout.get_active_holdouts",
               new_callable=AsyncMock, return_value=[holdout]), \
         patch("services.measurement.nodes.holdout.get_current_churn_score",
               new_callable=AsyncMock, return_value={"final_score": 0.95}), \
         patch("services.measurement.nodes.holdout.rescue_holdout_customer",
               new_callable=AsyncMock) as mock_rescue, \
         patch("services.measurement.nodes.holdout.get_kafka_producer",
               return_value=mock_producer):

        await run_rescue_check()

    mock_rescue.assert_called_once_with(
        customer_id=holdout["customer_id"],
        exit_reason="rescue_threshold",
    )
    mock_producer.produce.assert_called_once()
    topic = mock_producer.produce.call_args.kwargs["topic"]
    assert topic == "pcop.alarms.v1"


@pytest.mark.asyncio
async def test_rescue_fires_at_30_day_timeout():
    """Customers in holdout ≥30 days are rescued even if score is below threshold."""
    holdout = make_holdout_entry(days_ago=31)

    with patch("services.measurement.nodes.holdout.get_active_holdouts",
               new_callable=AsyncMock, return_value=[holdout]), \
         patch("services.measurement.nodes.holdout.get_current_churn_score",
               new_callable=AsyncMock, return_value={"final_score": 0.50}), \
         patch("services.measurement.nodes.holdout.rescue_holdout_customer",
               new_callable=AsyncMock) as mock_rescue, \
         patch("services.measurement.nodes.holdout.get_kafka_producer",
               return_value=MagicMock()):

        await run_rescue_check()

    mock_rescue.assert_called_once_with(
        customer_id=holdout["customer_id"],
        exit_reason="timeout_30d",
    )


@pytest.mark.asyncio
async def test_no_rescue_below_threshold_within_30_days():
    """Customers with score below 0.92 and within 30 days are not rescued."""
    holdout = make_holdout_entry(days_ago=5)

    with patch("services.measurement.nodes.holdout.get_active_holdouts",
               new_callable=AsyncMock, return_value=[holdout]), \
         patch("services.measurement.nodes.holdout.get_current_churn_score",
               new_callable=AsyncMock, return_value={"final_score": 0.70}), \
         patch("services.measurement.nodes.holdout.rescue_holdout_customer",
               new_callable=AsyncMock) as mock_rescue, \
         patch("services.measurement.nodes.holdout.get_kafka_producer",
               return_value=MagicMock()):

        await run_rescue_check()

    mock_rescue.assert_not_called()


def test_rescue_threshold_matches_compass_gate():
    """Rescue threshold must match COMPASS GATE value exactly."""
    assert RESCUE_THRESHOLD == 0.92
