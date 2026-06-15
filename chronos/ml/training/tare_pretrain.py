"""TARE self-supervised pre-training via masked action prediction on MBD-mini."""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path
from typing import Any

import mlflow
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DIR = ROOT / "ml" / "checkpoints"
DATA_DIR = ROOT / "data" / "datasets" / "mbd-mini"

MASK_FRACTION = 0.15
BATCH_SIZE = 256
EPOCHS = 10
LR = 1e-3
SAVE_EVERY_N_EPOCHS = 2


class MBDSequenceDataset(Dataset):
    """Loads pre-tokenised MBD-mini sequences from parquet."""

    def __init__(self, parquet_path: Path, subset_fraction: float = 1.0) -> None:
        import pandas as pd

        df = pd.read_parquet(parquet_path)
        if subset_fraction < 1.0:
            df = df.sample(frac=subset_fraction, random_state=42)
        self.token_ids = torch.tensor(df["token_ids"].tolist(), dtype=torch.long)
        self.time_gaps = torch.tensor(df["time_gaps"].tolist(), dtype=torch.float32)
        logger.info("MBD dataset loaded: %d sequences", len(self.token_ids))

    def __len__(self) -> int:
        return len(self.token_ids)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.token_ids[idx], self.time_gaps[idx]


def _mask_tokens(
    token_ids: torch.Tensor, vocab_size: int, mask_fraction: float = MASK_FRACTION, pad_id: int = 0
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Apply random masking; return (masked_ids, labels, mask_positions).

    Labels are -100 at non-masked positions (ignored by CrossEntropyLoss).
    """
    labels = token_ids.clone()
    masked = token_ids.clone()
    mask = (token_ids != pad_id) & (torch.rand_like(token_ids.float()) < mask_fraction)
    masked[mask] = vocab_size  # MASK token id (out-of-vocab sentinel)
    labels[~mask] = -100
    return masked, labels, mask


def train_epoch(
    model: nn.Module,
    pretrain_head: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    vocab_size: int,
) -> dict[str, float]:
    model.train()
    pretrain_head.train()
    total_loss = 0.0
    total_grad_norm = 0.0

    for batch_idx, (token_ids, time_gaps) in enumerate(loader):
        token_ids = token_ids.to(device)
        time_gaps = time_gaps.to(device)

        masked_ids, labels, _ = _mask_tokens(token_ids, vocab_size)
        _, _ = model(token_ids, time_gaps)  # warm up attention on unmasked

        # Get GRU output directly for pretrain head
        embed = model.embedding(masked_ids) + model.time_encoding(time_gaps)
        gru_out, _ = model.gru(embed)
        logits = pretrain_head(gru_out)  # (B, L, vocab)

        B, L, V = logits.shape
        loss = criterion(logits.view(B * L, V), labels.view(B * L))

        optimizer.zero_grad()
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(
            list(model.parameters()) + list(pretrain_head.parameters()), max_norm=1.0
        ).item()
        optimizer.step()

        total_loss += loss.item()
        total_grad_norm += grad_norm

    n = len(loader)
    return {"loss": total_loss / n, "grad_norm": total_grad_norm / n}


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    )

    parser = argparse.ArgumentParser(description="TARE pre-training via masked action prediction")
    parser.add_argument("--subset", type=float, default=1.0, help="Fraction of data (0-1) for dev runs")
    parser.add_argument("--resume", type=str, default=None, help="Path to checkpoint to resume from")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=LR)
    parser.add_argument("--experiment", default="TARE-PreTrain")
    args = parser.parse_args()

    from services.scoring.models.tare_encoder import (
        VOCAB_SIZE,
        TAREEncoder,
        TAREPretrainHead,
    )

    if torch.backends.mps.is_available():
        device = torch.device("mps")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    logger.info("Using device: %s", device)

    data_path = DATA_DIR / "train.parquet"
    if not data_path.exists():
        raise FileNotFoundError(f"MBD-mini train data not found at {data_path}. Run download_public_datasets.py first.")

    dataset = MBDSequenceDataset(data_path, subset_fraction=args.subset)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=2, pin_memory=True)

    model = TAREEncoder(vocab_size=VOCAB_SIZE + 1).to(device)
    pretrain_head = TAREPretrainHead(vocab_size=VOCAB_SIZE).to(device)
    optimizer = torch.optim.Adam(
        list(model.parameters()) + list(pretrain_head.parameters()), lr=args.lr
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = nn.CrossEntropyLoss(ignore_index=-100)

    start_epoch = 0
    if args.resume:
        ckpt = torch.load(args.resume, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        pretrain_head.load_state_dict(ckpt["pretrain_head_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = ckpt["epoch"] + 1
        logger.info("Resumed from epoch %d", start_epoch)

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    mlflow.set_experiment(args.experiment)
    with mlflow.start_run():
        mlflow.log_params({"epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr, "subset": args.subset})

        for epoch in range(start_epoch, args.epochs):
            metrics = train_epoch(model, pretrain_head, loader, optimizer, criterion, device, VOCAB_SIZE)
            scheduler.step()
            current_lr = scheduler.get_last_lr()[0]

            logger.info(
                "epoch=%d loss=%.4f grad_norm=%.3f lr=%.6f",
                epoch + 1, metrics["loss"], metrics["grad_norm"], current_lr,
            )
            mlflow.log_metrics(
                {"loss": metrics["loss"], "grad_norm": metrics["grad_norm"], "lr": current_lr},
                step=epoch,
            )

            if (epoch + 1) % SAVE_EVERY_N_EPOCHS == 0:
                ckpt_path = CHECKPOINT_DIR / f"tare_pretrain_epoch{epoch+1}.pt"
                torch.save({
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "pretrain_head_state_dict": pretrain_head.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "metrics": metrics,
                    "model_config": {
                        "vocab_size": VOCAB_SIZE,
                    },
                }, ckpt_path)
                logger.info("Checkpoint saved: %s", ckpt_path)

        final_path = CHECKPOINT_DIR / "tare_pretrain_final.pt"
        torch.save({"epoch": args.epochs - 1, "model_state_dict": model.state_dict(), "model_config": {}}, final_path)
        mlflow.log_artifact(str(final_path))
        logger.info("Pre-training complete. Final checkpoint: %s", final_path)


if __name__ == "__main__":
    main()
