import json
import logging
import numpy as np
import pandas as pd
from causalml.inference.meta import BaseDRLearner
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from ..db.reads import get_attribution_dataset, get_active_prompt_versions, update_prompt_version_uplift
from ..db.writes import write_uplift_results, write_model_calibration_signal

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "final_score_at_send",
    "treatability_score_at_send",
    "tenure_years",
    "num_active_products",
    "digital_ratio",
    "complaint_count_90d",
    "recency_days",
    "frequency_monthly",
    "monetary_avg",
    "active_signal_count",
    "life_event_count_at_send",
]


async def attribute_uplift(
    campaign_id: str,
    channel: str,
    segment: str,
    risk_tier: str,
    observation_window: int = 30,
):
    """
    Computes causal uplift for a specific campaign × channel × segment × tier slice.

    Uses the DR-Learner (Doubly Robust Learner) from the CausalML library.
    This is methodologically consistent with CAUSAL-NET (Layer 3D) which
    uses the same framework for treatability prediction.

    Variables:
      X = pre-treatment covariates (CHRONOS features at time of outreach)
      T = treatment indicator (1 = received outreach, 0 = holdout)
      Y = outcome (1 = retained, 0 = churned) at T+30

    DR estimator:
      τ_DR(x) = E[Y|T=1,X=x] - E[Y|T=0,X=x]
              + (T-p(x))/p(x) * (Y - E[Y|T=1,X=x])
              - (T-p(x))/(1-p(x)) * (Y - E[Y|T=0,X=x])

    Doubly robust: consistent if either nuisance model is correct.
    """
    logger.info(
        f"ATTRIBUTE: Computing DR uplift for "
        f"campaign={campaign_id} channel={channel} "
        f"segment={segment} tier={risk_tier}"
    )

    df = await get_attribution_dataset(
        campaign_id=campaign_id,
        channel=channel,
        segment=segment,
        risk_tier=risk_tier,
        observation_window=observation_window,
    )

    if len(df) < 50:
        logger.warning(
            f"ATTRIBUTE: Insufficient data for DR estimation "
            f"(n={len(df)}, need ≥50). Skipping."
        )
        return

    X = df[FEATURE_COLS].fillna(0).values
    T = df["treatment"].values
    Y = (df["outcome_label"] == "retained").astype(int).values

    learner = BaseDRLearner(
        learner=GradientBoostingRegressor(n_estimators=100, max_depth=4),
        treatment_effect_learner=GradientBoostingRegressor(n_estimators=100, max_depth=3),
        propensity_learner=LogisticRegression(C=1.0, max_iter=500),
    )

    learner.fit(X, T, Y)
    tau_hat = learner.predict(X)

    ate = float(np.mean(tau_hat))
    ate_se = float(np.std(tau_hat) / np.sqrt(len(tau_hat)))

    naive_uplift = (
        df[df["treatment"] == 1]["outcome_label"].eq("retained").mean()
        - df[df["treatment"] == 0]["outcome_label"].eq("retained").mean()
    )
    overestimation_bias = float(naive_uplift - ate)

    high_treat_mask = df["treatability_score_at_send"] >= 0.5
    ate_high_treat = float(np.mean(tau_hat[high_treat_mask])) if high_treat_mask.any() else None
    ate_low_treat = float(np.mean(tau_hat[~high_treat_mask])) if (~high_treat_mask).any() else None

    logger.info(
        f"ATTRIBUTE: DR uplift = {ate:.4f} ± {ate_se:.4f} "
        f"(naive = {naive_uplift:.4f}, bias = {overestimation_bias:.4f}) "
        f"n_treatment={T.sum()}, n_holdout={(1-T).sum()}"
    )

    await write_uplift_results({
        "campaign_id": campaign_id,
        "channel": channel,
        "segment": segment,
        "risk_tier": risk_tier,
        "observation_window": observation_window,
        "treatment_n": int(T.sum()),
        "holdout_n": int((1 - T).sum()),
        "treatment_retention_rate": float(Y[T == 1].mean()) if T.sum() > 0 else 0.0,
        "holdout_retention_rate": float(Y[T == 0].mean()) if (1 - T).sum() > 0 else 0.0,
        "naive_uplift": float(naive_uplift),
        "dr_uplift": ate,
        "dr_uplift_se": ate_se,
        "overestimation_bias": overestimation_bias,
        "ate_high_treatability": ate_high_treat,
        "ate_low_treatability": ate_low_treat,
        "psm_adjusted": False,
        "estimator": "DR-Learner",
        "calculated_at": pd.Timestamp.now().isoformat(),
    })

    if ate_high_treat is not None and ate_low_treat is not None:
        causal_net_calibrated = ate_high_treat > ate_low_treat
        logger.info(
            f"ATTRIBUTE: CAUSAL-NET calibration check — "
            f"high_treat_uplift={ate_high_treat:.4f} "
            f"low_treat_uplift={ate_low_treat:.4f} "
            f"calibrated={causal_net_calibrated}"
        )
        await _publish_causal_net_signal(
            channel=channel,
            segment=segment,
            causal_net_calibrated=causal_net_calibrated,
            ate_high=ate_high_treat,
            ate_low=ate_low_treat,
            n_samples=len(df),
        )


async def attribute_by_content_strategy(campaign_id: str, observation_window: int = 30):
    """
    Computes DR uplift separately for each content_strategy label.
    Results feed into Layer 7 REFINE to adjust HERALD's strategy selection logic.
    """
    for strategy in ["full_retention", "graceful_retention", "proactive"]:
        df = await get_attribution_dataset(
            campaign_id=campaign_id,
            content_strategy=strategy,
            observation_window=observation_window,
        )
        if len(df) >= 30:
            await _attribute_uplift_slice(df, label=f"strategy_{strategy}", campaign_id=campaign_id)


async def attribute_by_prompt_version(channel: str, observation_window: int = 30):
    """
    Computes DR uplift per prompt_version_id per channel.
    Uses DR over raw conversion rate to control for selection effects.
    Results feed directly into Layer 7 REFINE → Thompson sampling bandit update.
    """
    versions = await get_active_prompt_versions(channel=channel)
    for version_id in versions:
        df = await get_attribution_dataset(
            prompt_version_id=version_id,
            channel=channel,
            observation_window=observation_window,
        )
        if len(df) >= 20:
            dr_uplift = await _compute_mini_dr_uplift(df)
            await update_prompt_version_uplift(version_id, dr_uplift)
            logger.info(
                f"ATTRIBUTE: prompt={version_id} channel={channel} "
                f"dr_uplift={dr_uplift:.4f}"
            )


async def _attribute_uplift_slice(df: pd.DataFrame, label: str, campaign_id: str):
    """Runs DR on a pre-filtered DataFrame slice."""
    if len(df) < 30:
        return
    X = df[FEATURE_COLS].fillna(0).values
    T = df["treatment"].values
    Y = (df["outcome_label"] == "retained").astype(int).values

    try:
        learner = BaseDRLearner(
            learner=GradientBoostingRegressor(n_estimators=50, max_depth=3),
            treatment_effect_learner=GradientBoostingRegressor(n_estimators=50),
            propensity_learner=LogisticRegression(C=1.0, max_iter=300),
        )
        learner.fit(X, T, Y)
        tau_hat = learner.predict(X)
        ate = float(np.mean(tau_hat))
        logger.info(f"ATTRIBUTE: slice={label} campaign={campaign_id} dr_uplift={ate:.4f}")
    except Exception as e:
        logger.warning(f"ATTRIBUTE: Slice DR failed for {label}: {e}")


async def _compute_mini_dr_uplift(df: pd.DataFrame) -> float:
    """Computes a single DR uplift estimate from a pre-filtered DataFrame."""
    X = df[FEATURE_COLS].fillna(0).values
    T = df["treatment"].values
    Y = (df["outcome_label"] == "retained").astype(int).values

    try:
        learner = BaseDRLearner(
            learner=GradientBoostingRegressor(n_estimators=50, max_depth=3),
            treatment_effect_learner=GradientBoostingRegressor(n_estimators=50),
            propensity_learner=LogisticRegression(C=1.0, max_iter=300),
        )
        learner.fit(X, T, Y)
        return float(np.mean(learner.predict(X)))
    except Exception as e:
        logger.warning(f"ATTRIBUTE: Mini DR failed: {e}")
        return 0.0


async def _publish_causal_net_signal(
    channel: str,
    segment: str,
    causal_net_calibrated: bool,
    ate_high: float,
    ate_low: float,
    n_samples: int,
):
    """Publishes CAUSAL-NET calibration signal to pcop.model_signals.v1 for Layer 7 RETRAIN."""
    from ..kafka.producer import get_kafka_producer

    await write_model_calibration_signal({
        "model_name": "causal_net",
        "channel": channel,
        "segment": segment,
        "calibration_ok": causal_net_calibrated,
        "ate_high": ate_high,
        "ate_low": ate_low,
        "n_samples": n_samples,
    })

    try:
        producer = get_kafka_producer()
        producer.produce(
            topic="pcop.model_signals.v1",
            key=f"{channel}:{segment}",
            value=json.dumps({
                "model": "causal_net",
                "channel": channel,
                "segment": segment,
                "calibration_ok": causal_net_calibrated,
                "ate_high_treat": ate_high,
                "ate_low_treat": ate_low,
                "n_samples": n_samples,
            }).encode("utf-8"),
        )
        producer.flush()
    except Exception as e:
        logger.warning(f"ATTRIBUTE: Failed to publish model signal: {e}")
