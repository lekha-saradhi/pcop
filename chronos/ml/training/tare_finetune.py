"""Fine-tune TARE on synthetic BankChurners sequences for binary churn classification."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import torch
import torch.nn as nn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    classification_report,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DIR = ROOT / "ml" / "checkpoints"
DATA_PATH = ROOT / "data" / "datasets" / "bankchurners" / "synthetic_sequences.parquet"

EPOCHS = 15
BATCH_SIZE = 128
LR = 5e-4
EARLY_STOP_PATIENCE = 5


class ChurnSequenceDataset(Dataset):
    def __init__(self, token_ids: np.ndarray, time_gaps: np.ndarray, labels: np.ndarray) -> None:
        self.token_ids = torch.tensor(token_ids, dtype=torch.long)
        self.time_gaps = torch.tensor(time_gaps, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.token_ids[idx], self.time_gaps[idx], self.labels[idx]


def _extract_reason_codes(attn_weights: torch.Tensor, token_ids: torch.Tensor, top_k: int = 3) -> list[list[int]]:
    """Return top-k non-PAD token IDs by attention weight per sample."""
    results = []
    for weights, ids in zip(attn_weights.cpu().numpy(), token_ids.cpu().numpy()):
        non_pad_mask = ids != 0
        if not non_pad_mask.any():
            results.append([])
            continue
        masked_weights = np.where(non_pad_mask, weights, -np.inf)
        top_indices = np.argsort(masked_weights)[-top_k:][::-1]
        results.append([int(ids[i]) for i in top_indices if non_pad_mask[i]])
    return results


def train(args: argparse.Namespace) -> None:
    import pandas as pd
    from services.scoring.models.tare_encoder import TAREEncoder, VOCAB_SIZE

    if torch.backends.mps.is_available():
        device = torch.device("mps")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")


    df = pd.read_parquet(DATA_PATH)
    X_ids = np.array(df["token_ids"].tolist())
    X_gaps = np.array(df["time_gaps"].tolist())
    y = df["label"].values.astype(np.float32)

    # Stratified 70/15/15 split
    X_ids_tr, X_ids_tmp, X_gaps_tr, X_gaps_tmp, y_tr, y_tmp = train_test_split(
        X_ids, X_gaps, y, test_size=0.30, stratify=y, random_state=42
    )
    X_ids_val, X_ids_te, X_gaps_val, X_gaps_te, y_val, y_te = train_test_split(
        X_ids_tmp, X_gaps_tmp, y_tmp, test_size=0.50, stratify=y_tmp, random_state=42
    )

    # Class-weighted sampler (auto-compute ratio ~5.5:1)
    class_counts = np.bincount(y_tr.astype(int))
    weights = 1.0 / class_counts[y_tr.astype(int)]
    sampler = WeightedRandomSampler(weights, len(weights))

    train_ds = ChurnSequenceDataset(X_ids_tr, X_gaps_tr, y_tr)
    val_ds = ChurnSequenceDataset(X_ids_val, X_gaps_val, y_val)
    test_ds = ChurnSequenceDataset(X_ids_te, X_gaps_te, y_te)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    if args.pretrain_checkpoint:
        model = TAREEncoder.from_pretrained(args.pretrain_checkpoint)
    else:
        logger.warning("No pretrain checkpoint — training from scratch")
        model = TAREEncoder()

    # Freeze embedding layer
    for param in model.embedding.parameters():
        param.requires_grad = False

    model = model.to(device)
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=LR)
    criterion = nn.BCELoss()

    best_auc = 0.0
    patience_counter = 0

    mlflow.set_experiment(args.experiment)
    with mlflow.start_run():
        for epoch in range(args.epochs):
            model.train()
            for token_ids, time_gaps, labels in train_loader:
                token_ids, time_gaps, labels = token_ids.to(device), time_gaps.to(device), labels.to(device)
                preds, _ = model(token_ids, time_gaps)
                loss = criterion(preds, labels)
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

            # Validation
            model.eval()
            val_preds, val_labels = [], []
            with torch.no_grad():
                for token_ids, time_gaps, labels in val_loader:
                    p, _ = model(token_ids.to(device), time_gaps.to(device))
                    val_preds.extend(p.cpu().numpy())
                    val_labels.extend(labels.numpy())

            val_auc = roc_auc_score(val_labels, val_preds)
            val_brier = brier_score_loss(val_labels, val_preds)
            val_f1 = f1_score(val_labels, [int(p > 0.5) for p in val_preds], zero_division=0)

            logger.info("epoch=%d val_auc=%.4f val_brier=%.4f val_f1=%.4f", epoch + 1, val_auc, val_brier, val_f1)
            mlflow.log_metrics({"val_auc": val_auc, "val_brier": val_brier, "val_f1": val_f1}, step=epoch)

            if val_auc > best_auc:
                best_auc = val_auc
                patience_counter = 0
                best_ckpt = CHECKPOINT_DIR / "tare_finetune_best.pt"
                torch.save({"epoch": epoch, "model_state_dict": model.state_dict(), "val_auc": val_auc}, best_ckpt)
            else:
                patience_counter += 1
                if patience_counter >= EARLY_STOP_PATIENCE:
                    logger.info("Early stopping at epoch %d (best val_auc=%.4f)", epoch + 1, best_auc)
                    break

        # Platt scaling calibration on validation set
        val_preds_arr = np.array(val_preds).reshape(-1, 1)
        platt = LogisticRegression(C=1e10, solver="lbfgs")
        platt.fit(val_preds_arr, np.array(val_labels))
        platt_a = float(platt.coef_[0][0])
        platt_b = float(platt.intercept_[0])
        logger.info("Platt scaling: a=%.4f b=%.4f", platt_a, platt_b)
        mlflow.log_params({"platt_a": platt_a, "platt_b": platt_b})

        # Test evaluation
        model.eval()
        test_preds, test_labels = [], []
        with torch.no_grad():
            for token_ids, time_gaps, labels in test_loader:
                p, _ = model(token_ids.to(device), time_gaps.to(device))
                test_preds.extend(p.cpu().numpy())
                test_labels.extend(labels.numpy())

        test_auc = roc_auc_score(test_labels, test_preds)
        test_brier = brier_score_loss(test_labels, test_preds)
        logger.info("TEST AUC=%.4f Brier=%.4f", test_auc, test_brier)
        mlflow.log_metrics({"test_auc": test_auc, "test_brier": test_brier})

        final_path = CHECKPOINT_DIR / "tare_finetune_final.pt"
        torch.save({
            "model_state_dict": model.state_dict(),
            "platt_a": platt_a,
            "platt_b": platt_b,
            "test_auc": test_auc,
            "model_config": {},
        }, final_path)
        mlflow.log_artifact(str(final_path))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrain-checkpoint", type=str, default=None)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--experiment", default="TARE-FineTune")
    args = parser.parse_args()
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    train(args)


if __name__ == "__main__":
    main()
