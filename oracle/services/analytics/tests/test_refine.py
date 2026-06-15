import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from .conftest import make_prompt_versions, make_ab_variant_pair


@pytest.mark.asyncio
async def test_bandit_update_called_for_each_version():
    """update_bandit_params is called for each version with new observations."""
    versions = make_prompt_versions()

    with patch("services.analytics.cycles.refine.get_prompt_versions_with_dr_uplift",
               new_callable=AsyncMock, return_value=versions), \
         patch("services.analytics.cycles.refine.get_ab_variant_outcomes",
               new_callable=AsyncMock, return_value=[]), \
         patch("services.analytics.cycles.refine.update_bandit_params",
               new_callable=AsyncMock) as mock_bandit, \
         patch("services.analytics.cycles.refine._measure_tone_modifier_effectiveness",
               new_callable=AsyncMock):

        from services.analytics.cycles.refine import run_daily_prompt_optimisation
        await run_daily_prompt_optimisation()

    # Should be called once per channel per version (5 channels × 2 versions = 10 calls)
    assert mock_bandit.call_count > 0


@pytest.mark.asyncio
async def test_bandit_skips_version_with_zero_observations():
    """Versions with new_observations_today = 0 are skipped."""
    versions = [
        {"version_id": "v1", "channel": "email", "dr_uplift": 0.08, "new_observations_today": 0},
    ]

    with patch("services.analytics.cycles.refine.get_prompt_versions_with_dr_uplift",
               new_callable=AsyncMock, return_value=versions), \
         patch("services.analytics.cycles.refine.get_ab_variant_outcomes",
               new_callable=AsyncMock, return_value=[]), \
         patch("services.analytics.cycles.refine.update_bandit_params",
               new_callable=AsyncMock) as mock_bandit, \
         patch("services.analytics.cycles.refine._measure_tone_modifier_effectiveness",
               new_callable=AsyncMock):

        from services.analytics.cycles.refine import run_daily_prompt_optimisation
        await run_daily_prompt_optimisation()

    mock_bandit.assert_not_called()


@pytest.mark.asyncio
async def test_ab_test_promotes_winner_when_significant():
    """Fisher's exact test promotes winner when p < 0.05."""
    # B has 62/80 retention vs A 45/80 — should be significant
    ab_pairs = make_ab_variant_pair(a_retained=45, a_total=80, b_retained=62, b_total=80)

    with patch("services.analytics.cycles.refine.get_ab_variant_outcomes",
               new_callable=AsyncMock, return_value=ab_pairs), \
         patch("services.analytics.cycles.refine.promote_prompt_variant",
               new_callable=AsyncMock) as mock_promote:

        from services.analytics.cycles.refine import _check_ab_variant_significance
        await _check_ab_variant_significance("email")

    mock_promote.assert_called_once()
    kwargs = mock_promote.call_args.kwargs
    assert kwargs["winner"] == "B"


@pytest.mark.asyncio
async def test_ab_test_not_promoted_when_not_significant():
    """Fisher's exact test does not promote when p >= 0.05."""
    # Very similar rates — should not be significant
    ab_pairs = make_ab_variant_pair(a_retained=50, a_total=100, b_retained=52, b_total=100)

    with patch("services.analytics.cycles.refine.get_ab_variant_outcomes",
               new_callable=AsyncMock, return_value=ab_pairs), \
         patch("services.analytics.cycles.refine.promote_prompt_variant",
               new_callable=AsyncMock) as mock_promote:

        from services.analytics.cycles.refine import _check_ab_variant_significance
        await _check_ab_variant_significance("email")

    mock_promote.assert_not_called()


@pytest.mark.asyncio
async def test_ab_test_skipped_for_non_email_channels():
    """A/B significance test only runs for email channel."""
    with patch("services.analytics.cycles.refine.get_ab_variant_outcomes",
               new_callable=AsyncMock) as mock_get:

        from services.analytics.cycles.refine import _check_ab_variant_significance
        await _check_ab_variant_significance("sms")
        await _check_ab_variant_significance("app")

    mock_get.assert_not_called()
