import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from .conftest import make_training_df


@pytest.mark.asyncio
async def test_retrain_uses_dr_adjusted_labels():
    """Weekly retrain fetches DR-adjusted training data."""
    train_df = make_training_df(n=200)

    with patch("services.analytics.cycles.retrain.get_training_dataset_with_dr_outcomes",
               new_callable=AsyncMock, return_value=train_df), \
         patch("services.analytics.cycles.retrain.get_causal_net_calibration_signals",
               new_callable=AsyncMock, return_value=[{"calibration_ok": True}]), \
         patch("services.analytics.cycles.retrain._retrain_tare", new_callable=AsyncMock), \
         patch("services.analytics.cycles.retrain._retrain_habitat", new_callable=AsyncMock), \
         patch("services.analytics.cycles.retrain._recalibrate_fusion_x", new_callable=AsyncMock), \
         patch("services.analytics.cycles.retrain._update_aegis_reference", new_callable=AsyncMock), \
         patch("mlflow.start_run") as mock_run, \
         patch("mlflow.log_param"), \
         patch("mlflow.log_metric"):

        mock_run.return_value.__enter__ = MagicMock(return_value=None)
        mock_run.return_value.__exit__ = MagicMock(return_value=False)

        from services.analytics.cycles.retrain import run_weekly_retrain
        await run_weekly_retrain()


@pytest.mark.asyncio
async def test_causal_net_retrain_triggered_on_failure():
    """CAUSAL-NET retrain fires when calibration_ok=False."""
    train_df = make_training_df()
    causal_signals = [{"calibration_ok": False, "channel": "email", "segment": "mass_affluent"}]

    with patch("services.analytics.cycles.retrain.get_training_dataset_with_dr_outcomes",
               new_callable=AsyncMock, return_value=train_df), \
         patch("services.analytics.cycles.retrain.get_causal_net_calibration_signals",
               new_callable=AsyncMock, return_value=causal_signals), \
         patch("services.analytics.cycles.retrain._retrain_tare", new_callable=AsyncMock), \
         patch("services.analytics.cycles.retrain._retrain_habitat", new_callable=AsyncMock), \
         patch("services.analytics.cycles.retrain._retrain_causal_net",
               new_callable=AsyncMock) as mock_causal, \
         patch("services.analytics.cycles.retrain._recalibrate_fusion_x", new_callable=AsyncMock), \
         patch("services.analytics.cycles.retrain._update_aegis_reference", new_callable=AsyncMock), \
         patch("mlflow.start_run") as mock_run, \
         patch("mlflow.log_param"), \
         patch("mlflow.log_metric"):

        mock_run.return_value.__enter__ = MagicMock(return_value=None)
        mock_run.return_value.__exit__ = MagicMock(return_value=False)

        from services.analytics.cycles.retrain import run_weekly_retrain
        await run_weekly_retrain()

    mock_causal.assert_called_once_with(train_df)


@pytest.mark.asyncio
async def test_causal_net_skipped_when_calibrated():
    """CAUSAL-NET retrain is skipped when all calibration signals are OK."""
    train_df = make_training_df()
    causal_signals = [{"calibration_ok": True}]

    with patch("services.analytics.cycles.retrain.get_training_dataset_with_dr_outcomes",
               new_callable=AsyncMock, return_value=train_df), \
         patch("services.analytics.cycles.retrain.get_causal_net_calibration_signals",
               new_callable=AsyncMock, return_value=causal_signals), \
         patch("services.analytics.cycles.retrain._retrain_tare", new_callable=AsyncMock), \
         patch("services.analytics.cycles.retrain._retrain_habitat", new_callable=AsyncMock), \
         patch("services.analytics.cycles.retrain._retrain_causal_net",
               new_callable=AsyncMock) as mock_causal, \
         patch("services.analytics.cycles.retrain._recalibrate_fusion_x", new_callable=AsyncMock), \
         patch("services.analytics.cycles.retrain._update_aegis_reference", new_callable=AsyncMock), \
         patch("mlflow.start_run") as mock_run, \
         patch("mlflow.log_param"), \
         patch("mlflow.log_metric"):

        mock_run.return_value.__enter__ = MagicMock(return_value=None)
        mock_run.return_value.__exit__ = MagicMock(return_value=False)

        from services.analytics.cycles.retrain import run_weekly_retrain
        await run_weekly_retrain()

    mock_causal.assert_not_called()
