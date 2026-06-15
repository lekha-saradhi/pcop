import pytest
from unittest.mock import AsyncMock, patch


DEMO_CELLS = [
    {"segment": "mass_affluent", "risk_tier": "high", "content_strategy": "full_retention", "primary_signal_type": "tempo_transaction_freq"},
    {"segment": "mass_affluent", "risk_tier": "medium", "content_strategy": "proactive", "primary_signal_type": None},
]

DEMO_UPLIFTS = [
    {"channel": "email", "dr_uplift": 0.07, "n_samples": 45},
    {"channel": "sms", "dr_uplift": 0.03, "n_samples": 30},
    {"channel": "app", "dr_uplift": 0.09, "n_samples": 38},
]


@pytest.mark.asyncio
async def test_route_updates_policy_for_each_cell_and_channel():
    """update_channel_policy_from_uplift calls update_channel_policy for each cell × channel."""
    with patch("services.analytics.cycles.route.get_distinct_channel_policy_cells",
               new_callable=AsyncMock, return_value=DEMO_CELLS), \
         patch("services.analytics.cycles.route.get_channel_uplift_by_cell",
               new_callable=AsyncMock, return_value=DEMO_UPLIFTS), \
         patch("services.analytics.cycles.route.update_channel_policy",
               new_callable=AsyncMock) as mock_update:

        from services.analytics.cycles.route import update_channel_policy_from_uplift
        await update_channel_policy_from_uplift()

    # 2 cells × 3 channels = 6 calls (all n_samples >= 10)
    assert mock_update.call_count == 6


@pytest.mark.asyncio
async def test_route_skips_channels_with_insufficient_data():
    """Channels with n_samples < 10 are skipped."""
    uplifts_with_small = [
        {"channel": "email", "dr_uplift": 0.07, "n_samples": 45},
        {"channel": "rm_visit", "dr_uplift": 0.12, "n_samples": 5},  # too small
    ]

    with patch("services.analytics.cycles.route.get_distinct_channel_policy_cells",
               new_callable=AsyncMock, return_value=[DEMO_CELLS[0]]), \
         patch("services.analytics.cycles.route.get_channel_uplift_by_cell",
               new_callable=AsyncMock, return_value=uplifts_with_small), \
         patch("services.analytics.cycles.route.update_channel_policy",
               new_callable=AsyncMock) as mock_update:

        from services.analytics.cycles.route import update_channel_policy_from_uplift
        await update_channel_policy_from_uplift()

    assert mock_update.call_count == 1  # only email, not rm_visit


@pytest.mark.asyncio
async def test_route_successes_failures_from_uplift():
    """Verifies alpha/beta increments are correctly computed from dr_uplift and n."""
    captured_calls = []

    async def capture_update(data):
        captured_calls.append(data)

    with patch("services.analytics.cycles.route.get_distinct_channel_policy_cells",
               new_callable=AsyncMock, return_value=[DEMO_CELLS[0]]), \
         patch("services.analytics.cycles.route.get_channel_uplift_by_cell",
               new_callable=AsyncMock, return_value=[{"channel": "email", "dr_uplift": 0.10, "n_samples": 50}]), \
         patch("services.analytics.cycles.route.update_channel_policy",
               side_effect=capture_update):

        from services.analytics.cycles.route import update_channel_policy_from_uplift
        await update_channel_policy_from_uplift()

    assert len(captured_calls) == 1
    data = captured_calls[0]
    # successes = max(0, int(50 * 0.10)) = 5
    # failures = 50 - 5 = 45
    assert data["alpha_increment"] == 5
    assert data["beta_increment"] == 45
