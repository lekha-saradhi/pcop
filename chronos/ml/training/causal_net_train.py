"""CAUSAL-NET training: S-Learner on Criteo, T-Learner fine-tune on Hillstrom."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
CRITEO_PATH = ROOT / "data" / "datasets" / "criteo-uplift" / "criteo_uplift.parquet"
HILLSTROM_PATH = ROOT / "data" / "datasets" / "hillstrom" / "hillstrom.parquet"
CHECKPOINT_DIR = ROOT / "ml" / "checkpoints"

HILLSTROM_FEATURE_MAP = {
    "recency": "recency_days",
    "history": "monetary_avg",
    "newbie": "tenure_lt_12_months",
    "channel": "preferred_channel",
}


def _compute_auuc(y_true: np.ndarray, uplift: np.ndarray, treatment: np.ndarray) -> float:
    """Area Under Uplift Curve (simplified Qini coefficient)."""
    n = len(y_true)
    sorted_idx = np.argsort(-uplift)
    y_sorted = y_true[sorted_idx]
    t_sorted = treatment[sorted_idx]

    n_treated = max(t_sorted.sum(), 1)
    n_control = max((1 - t_sorted).sum(), 1)

    cumulative_uplift = []
    cum_t, cum_c = 0, 0
    for i in range(n):
        if t_sorted[i] == 1:
            cum_t += y_sorted[i]
        else:
            cum_c += y_sorted[i]
        uplift_i = cum_t / n_treated - cum_c / n_control
        cumulative_uplift.append(uplift_i)

    return float(np.trapz(cumulative_uplift) / n)


def train_criteo_s_learner(criteo_path: Path) -> xgb.Booster:
    """Phase 1: S-Learner on Criteo uplift data."""
    logger.info("Loading Criteo Uplift dataset from %s", criteo_path)
    df = pd.read_parquet(criteo_path)

    feature_cols = [c for c in df.columns if c not in ["target", "treatment"]]
    df["treatment"] = df["treatment"].astype(float)

    X = df[feature_cols + ["treatment"]].values.astype(np.float32)
    y = df["target"].values.astype(np.float32)

    X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.10, random_state=42)
    dtrain = xgb.DMatrix(X_tr, label=y_tr)
    dval = xgb.DMatrix(X_val, label=y_val)

    params = {
        "max_depth": 6,
        "eta": 0.05,
        "subsample": 0.8,
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "seed": 42,
    }
    model = xgb.train(
        params, dtrain, num_boost_round=200,
        evals=[(dval, "val")], early_stopping_rounds=20, verbose_eval=50,
    )

    # Estimate uplift
    X_val_t1 = X_val.copy(); X_val_t1[:, -1] = 1.0
    X_val_t0 = X_val.copy(); X_val_t0[:, -1] = 0.0
    uplift = model.predict(xgb.DMatrix(X_val_t1)) - model.predict(xgb.DMatrix(X_val_t0))

    auuc = _compute_auuc(y_val, uplift, X_val[:, -1].astype(int))
    logger.info("Criteo S-Learner AUUC=%.4f", auuc)
    return model


def train_hillstrom_t_learner(hillstrom_path: Path) -> tuple[xgb.Booster, xgb.Booster]:
    """Phase 2: T-Learner on Hillstrom dataset."""
    logger.info("Loading Hillstrom dataset from %s", hillstrom_path)
    df = pd.read_parquet(hillstrom_path)

    # Map Hillstrom → PCOP features
    rename = {k: v for k, v in HILLSTROM_FEATURE_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)
    if "tenure_lt_12_months" in df.columns:
        df["tenure_lt_12_months"] = (df["tenure_lt_12_months"] == 1).astype(float)

    if "preferred_channel" in df.columns:
        df["preferred_channel"] = df["preferred_channel"].map({"Phone": 0, "Multichannel": 1, "Web": 2}).fillna(0)

    # Encode remaining categorical columns
    if "history_segment" in df.columns:
        seg_map = {s: i for i, s in enumerate(sorted(df["history_segment"].unique()))}
        df["history_segment"] = df["history_segment"].map(seg_map).fillna(0)

    if "zip_code" in df.columns:
        zip_map = {z: i for i, z in enumerate(sorted(df["zip_code"].unique()))}
        df["zip_code"] = df["zip_code"].map(zip_map).fillna(0)

    if df["treatment"].dtype == "object":
        df["treatment"] = df["treatment"].map({"No E-Mail": 0, "Mens E-Mail": 1, "Womens E-Mail": 2}).fillna(0)

    feature_cols = [c for c in df.columns if c not in ["target", "treatment", "visit", "conversion", "spend"]]
    X = df[feature_cols].fillna(0).values.astype(np.float32)
    y_col = "target" if "target" in df.columns else ("conversion" if "conversion" in df.columns else "visit")
    y = df[y_col].fillna(0).values.astype(np.float32)
    t = df["treatment"].fillna(0).values

    treated_mask = t > 0
    control_mask = t == 0

    X_t, y_t = X[treated_mask], y[treated_mask]
    X_c, y_c = X[control_mask], y[control_mask]

    params = {"max_depth": 4, "eta": 0.1, "objective": "binary:logistic", "eval_metric": "auc", "seed": 42}

    model_t = xgb.train(params, xgb.DMatrix(X_t, label=y_t), num_boost_round=100, verbose_eval=False)
    model_c = xgb.train(params, xgb.DMatrix(X_c, label=y_c), num_boost_round=100, verbose_eval=False)

    uplift = model_t.predict(xgb.DMatrix(X)) - model_c.predict(xgb.DMatrix(X))
    auuc = _compute_auuc(y, uplift, (t > 0).astype(int))
    qini = auuc * len(X)
    logger.info("Hillstrom T-Learner AUUC=%.4f Qini=%.2f", auuc, qini)
    return model_t, model_c


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Train CAUSAL-NET uplift models")
    parser.add_argument("--skip-criteo", action="store_true", help="Skip Criteo pre-training")
    parser.add_argument("--experiment", default="CAUSAL-NET")
    args = parser.parse_args()

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    mlflow.set_experiment(args.experiment)
    with mlflow.start_run():
        if not args.skip_criteo and CRITEO_PATH.exists():
            s_model = train_criteo_s_learner(CRITEO_PATH)
            s_model.save_model(str(CHECKPOINT_DIR / "causal_net_s_learner.json"))
        else:
            logger.info("Skipping Criteo S-Learner training")

        if HILLSTROM_PATH.exists():
            model_t, model_c = train_hillstrom_t_learner(HILLSTROM_PATH)
            model_t.save_model(str(CHECKPOINT_DIR / "causal_net_treated.json"))
            model_c.save_model(str(CHECKPOINT_DIR / "causal_net_control.json"))
        else:
            logger.warning("Hillstrom dataset not found at %s", HILLSTROM_PATH)


if __name__ == "__main__":
    main()
