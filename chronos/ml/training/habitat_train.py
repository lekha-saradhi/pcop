"""Train HABITAT Pass 1 XGBoost scorer on Bank Customer Churn dataset."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
BANK_CHURN_PATH = ROOT / "data" / "datasets" / "bank-churn" / "Bank Customer Churn Prediction.csv"
PKDD_PATH = ROOT / "data" / "datasets" / "pkdd99"
CHECKPOINT_DIR = ROOT / "ml" / "checkpoints"

FEATURE_COLUMNS = [
    "CreditScore", "Age", "Tenure", "Balance", "NumOfProducts",
    "HasCrCard", "IsActiveMember", "EstimatedSalary",
]
TARGET_COLUMN = "Exited"

XGBOOST_PARAMS = {
    "max_depth": 6,
    "eta": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "scale_pos_weight": 5.5,
    "objective": "binary:logistic",
    "eval_metric": ["auc", "logloss"],
    "seed": 42,
    "nthread": -1,
}
N_ROUNDS = 300
EARLY_STOPPING = 30


def load_bank_churn(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    feature_map = {
        "credit_score": "CreditScore",
        "age": "Age",
        "tenure": "Tenure",
        "balance": "Balance",
        "products_number": "NumOfProducts",
        "credit_card": "HasCrCard",
        "active_member": "IsActiveMember",
        "estimated_salary": "EstimatedSalary",
        "churn": "Exited",
    }
    df = df.rename(columns=feature_map)
    available = [c for c in FEATURE_COLUMNS if c in df.columns]
    df = df[available + [TARGET_COLUMN]].dropna()
    logger.info("Bank Churn loaded: %d rows, %d features", len(df), len(available))
    return df


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the 14 HABITAT Pass 1 features from raw columns."""
    from ml.features.tabular_features import PASS1_FEATURE_NAMES

    result = pd.DataFrame(index=df.index)

    # Map raw columns to HABITAT feature schema where available
    result["recency_days"] = 30.0  # not in this dataset; use median
    result["monetary_avg"] = df.get("Balance", 0) / np.maximum(df.get("Tenure", 1), 1)
    result["monetary_total"] = df.get("Balance", 0)
    result["frequency_30d"] = df.get("NumOfProducts", 1).astype(float)
    result["frequency_90d"] = df.get("NumOfProducts", 1).astype(float) * 3
    result["decline_rate_30d"] = 0.0
    result["support_contacts_90d"] = 0.0
    result["inactivity_streak_days"] = (1 - df.get("IsActiveMember", 1)) * 30
    result["product_count"] = df.get("NumOfProducts", 1).astype(float)
    result["digital_ratio"] = df.get("IsActiveMember", 0).astype(float)
    result["avg_utilization"] = np.clip(df.get("Balance", 0) / np.maximum(df.get("EstimatedSalary", 1), 1), 0, 1)
    result["complaint_open_count"] = 0.0
    result["tenure_days"] = df.get("Tenure", 0) * 30.0
    result["channel_diversity"] = df.get("HasCrCard", 0) + 1.0

    return result


def train(args: argparse.Namespace) -> None:
    df = load_bank_churn(BANK_CHURN_PATH)
    X = _engineer_features(df)
    y = df[TARGET_COLUMN].values

    X_tr, X_tmp, y_tr, y_tmp = train_test_split(X, y, test_size=0.30, stratify=y, random_state=42)
    X_val, X_te, y_val, y_te = train_test_split(X_tmp, y_tmp, test_size=0.50, stratify=y_tmp, random_state=42)

    dtrain = xgb.DMatrix(X_tr, label=y_tr, feature_names=list(X_tr.columns))
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=list(X_tr.columns))
    dtest = xgb.DMatrix(X_te, label=y_te, feature_names=list(X_tr.columns))

    evals_result: dict = {}
    mlflow.set_experiment(args.experiment)
    with mlflow.start_run():
        model = xgb.train(
            XGBOOST_PARAMS,
            dtrain,
            num_boost_round=N_ROUNDS,
            evals=[(dval, "val")],
            early_stopping_rounds=EARLY_STOPPING,
            evals_result=evals_result,
            verbose_eval=50,
        )

        test_preds = model.predict(dtest)
        test_auc = roc_auc_score(y_te, test_preds)
        test_logloss = log_loss(y_te, test_preds)

        logger.info("TEST AUC=%.4f logloss=%.4f", test_auc, test_logloss)
        mlflow.log_metrics({"test_auc": test_auc, "test_logloss": test_logloss})
        mlflow.log_params(XGBOOST_PARAMS)

        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        model_path = CHECKPOINT_DIR / "habitat_pass1.json"
        model.save_model(str(model_path))
        logger.info("HABITAT Pass 1 model saved to %s", model_path)

        # SHAP summary
        try:
            import shap
            import matplotlib.pyplot as plt

            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_tr)
            fig, ax = plt.subplots(figsize=(8, 6))
            shap.summary_plot(shap_values, X_tr, show=False)
            shap_path = CHECKPOINT_DIR / "habitat_shap_summary.png"
            plt.savefig(shap_path, bbox_inches="tight")
            plt.close()
            mlflow.log_artifact(str(shap_path))
            logger.info("SHAP summary saved to %s", shap_path)
        except Exception:
            logger.warning("SHAP plot failed — skipping")

        mlflow.log_artifact(str(model_path))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Train HABITAT Pass 1 XGBoost scorer")
    parser.add_argument("--experiment", default="HABITAT-Pass1")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
