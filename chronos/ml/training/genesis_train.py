"""Train GENESIS cold-start Logistic Regression scorer."""

from __future__ import annotations

import argparse
import logging
import pickle
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
BANK_CHURN_PATH = ROOT / "data" / "datasets" / "bank-churn" / "Bank Customer Churn Prediction.csv"
UCI_PATH = ROOT / "data" / "datasets" / "uci-bank-marketing" / "bank-additional-full.csv"
CHECKPOINT_DIR = ROOT / "ml" / "checkpoints"

FEATURE_NAMES = [
    "tenure_days",
    "product_count",
    "age_bucket",
    "income_band",
    "channel_acquisition",
    "credit_score_band",
    "city_tier",
]


def _load_bank_churn(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    result = pd.DataFrame()
    result["tenure_days"] = df.get("Tenure", df.get("tenure", 0)) * 30.0
    result["product_count"] = df.get("NumOfProducts", df.get("products_number", 1)).astype(float)
    age = df.get("Age", df.get("age", 35))
    result["age_bucket"] = pd.cut(age, bins=[0, 25, 35, 45, 55, 120], labels=[0, 1, 2, 3, 4]).astype(float)
    result["income_band"] = pd.qcut(df.get("EstimatedSalary", df.get("estimated_salary", 50000)), q=5, labels=False, duplicates="drop").astype(float)
    result["channel_acquisition"] = 1.0  # UCI/BankChurn = mostly online
    credit = df.get("CreditScore", df.get("credit_score", 600))
    result["credit_score_band"] = pd.cut(credit, bins=[0, 500, 580, 670, 740, 850], labels=[0, 1, 2, 3, 4]).astype(float)
    result["city_tier"] = 2.0  # unknown; use tier-1 city default
    result["label"] = df.get("Exited", df.get("churn", 0)).astype(int)
    return result.dropna()


def _load_uci(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    result = pd.DataFrame()
    age = df.get("age", pd.Series([35] * len(df)))
    result["tenure_days"] = df.get("duration", pd.Series([0] * len(df))).astype(float) / 30
    result["product_count"] = 1.0
    result["age_bucket"] = pd.cut(age, bins=[0, 25, 35, 45, 55, 120], labels=[0, 1, 2, 3, 4]).astype(float)
    result["income_band"] = 2.0
    result["channel_acquisition"] = df.get("contact", "telephone").map({"telephone": 0, "cellular": 1, "unknown": 0}).astype(float)
    result["credit_score_band"] = 2.0
    result["city_tier"] = 1.0
    result["label"] = (df["y"] == "yes").astype(int)  # subscription → retention proxy
    return result.dropna()


def train(args: argparse.Namespace) -> None:
    df_bank = _load_bank_churn(BANK_CHURN_PATH)
    df_uci = _load_uci(UCI_PATH) if UCI_PATH.exists() else pd.DataFrame()
    df = pd.concat([df_bank, df_uci], ignore_index=True) if len(df_uci) > 0 else df_bank

    X = df[FEATURE_NAMES].fillna(0).values
    y = df["label"].values

    model = LogisticRegression(
        C=1.0,
        solver="lbfgs",
        max_iter=500,
        class_weight="balanced",
        random_state=42,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_aucs = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
    logger.info("5-fold CV AUC: %.4f ± %.4f", cv_aucs.mean(), cv_aucs.std())

    model.fit(X, y)

    mlflow.set_experiment(args.experiment)
    with mlflow.start_run():
        mlflow.log_metrics({"cv_auc_mean": cv_aucs.mean(), "cv_auc_std": cv_aucs.std()})
        mlflow.log_params({"C": 1.0, "class_weight": "balanced", "n_train": len(X)})

        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        model_path = CHECKPOINT_DIR / "genesis_lr.pkl"
        with open(model_path, "wb") as f:
            pickle.dump({"model": model, "feature_names": FEATURE_NAMES}, f)
        logger.info("GENESIS model saved to %s", model_path)
        mlflow.log_artifact(str(model_path))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Train GENESIS cold-start scorer")
    parser.add_argument("--experiment", default="GENESIS")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
