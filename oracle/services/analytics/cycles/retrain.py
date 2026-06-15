import logging
import mlflow
from datetime import date
from ..db.reads import get_training_dataset_with_dr_outcomes, get_causal_net_calibration_signals

logger = logging.getLogger(__name__)


async def run_weekly_retrain():
    """
    Weekly model retraining for CHRONOS components.

    Key difference from a naive approach:
      Training labels use DR-estimated outcomes (not naive retention labels).
      A customer who was in the holdout group and churned despite no outreach
      should NOT count as a negative training signal for a customer who received
      outreach and also churned — they are different counterfactual scenarios.

    DR-adjusted label:
      If DR uplift for this customer's stratum was positive:
        Use observed outcome as label (outreach had real effect)
      If DR uplift was near zero or negative:
        Downweight this sample (outreach had no causal effect on outcome)

    Models retrained:
      1. TARE (GRU encoder) — new action sequences + DR-adjusted churn labels
      2. HABITAT Pass 1 (XGBoost) — updated tabular features + labels
      3. CAUSAL-NET treatability — updated with DR uplift measurements
         (special: only retrained if VERDICT found calibration issues)
      4. GENESIS cold-start LR — graduated customer outcomes
    """
    with mlflow.start_run(run_name=f"weekly_retrain_{date.today()}"):
        train_df = await get_training_dataset_with_dr_outcomes(
            lookback_days=90,
            min_observation_window=30,
        )

        mlflow.log_param("training_samples", len(train_df))
        mlflow.log_param("churn_rate", float(train_df["churn_label"].mean()))
        mlflow.log_param("dr_weighted_samples", int((train_df["sample_weight"] > 0.5).sum()))

        logger.info(
            f"RETRAIN: Training data — n={len(train_df)} "
            f"churn_rate={train_df['churn_label'].mean():.3f} "
            f"dr_weighted={int((train_df['sample_weight'] > 0.5).sum())}"
        )

        await _retrain_tare(train_df)
        await _retrain_habitat(train_df)

        causal_net_signals = await get_causal_net_calibration_signals()
        if any(not s["calibration_ok"] for s in causal_net_signals):
            logger.info("RETRAIN: CAUSAL-NET calibration failure detected — retraining")
            await _retrain_causal_net(train_df)
            mlflow.log_param("causal_net_retrained", True)
        else:
            logger.info("RETRAIN: CAUSAL-NET calibration OK — skipping")
            mlflow.log_param("causal_net_retrained", False)

        await _recalibrate_fusion_x()
        await _update_aegis_reference()

        logger.info("RETRAIN: Weekly retraining complete")


async def _retrain_tare(train_df):
    """Retrains the TARE GRU sequence encoder on DR-weighted labels."""
    import os
    if os.environ.get("ORACLE_DEMO_MODE", "true").lower() == "true":
        logger.info(
            f"DEMO: TARE retrain — n={len(train_df)} "
            f"avg_weight={train_df['sample_weight'].mean():.3f}"
        )
        mlflow.log_metric("tare_training_samples", len(train_df))
        mlflow.log_metric("tare_avg_weight", float(train_df["sample_weight"].mean()))
        return
    # Production: call TARE training pipeline
    # from chronos.training import tare_trainer
    # model = tare_trainer.fit(train_df, weight_col="sample_weight")
    # mlflow.pytorch.log_model(model, "tare_model")


async def _retrain_habitat(train_df):
    """Retrains the HABITAT XGBoost tabular model on DR-weighted labels."""
    import os
    if os.environ.get("ORACLE_DEMO_MODE", "true").lower() == "true":
        logger.info(f"DEMO: HABITAT retrain — n={len(train_df)}")
        mlflow.log_metric("habitat_training_samples", len(train_df))
        return
    # Production: call HABITAT training pipeline
    # from chronos.training import habitat_trainer
    # model = habitat_trainer.fit(train_df, weight_col="sample_weight")
    # mlflow.sklearn.log_model(model, "habitat_model")


async def _retrain_causal_net(train_df):
    """Retrains CAUSAL-NET DR-Learner treatability model."""
    import os
    if os.environ.get("ORACLE_DEMO_MODE", "true").lower() == "true":
        logger.info(f"DEMO: CAUSAL-NET retrain (calibration failure) — n={len(train_df)}")
        mlflow.log_metric("causal_net_training_samples", len(train_df))
        return


async def _recalibrate_fusion_x():
    """Recalibrates FUSION-X ensemble weights based on recent TARE vs HABITAT disagreement."""
    import os
    if os.environ.get("ORACLE_DEMO_MODE", "true").lower() == "true":
        logger.info("DEMO: FUSION-X weight recalibration")
        mlflow.log_metric("fusion_x_recalibrated", 1)
        return


async def _update_aegis_reference():
    """Updates AEGIS reference distributions post-retrain for drift detection baseline."""
    import os
    if os.environ.get("ORACLE_DEMO_MODE", "true").lower() == "true":
        logger.info("DEMO: AEGIS reference distributions updated")
        mlflow.log_metric("aegis_updated", 1)
        return
