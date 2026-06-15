"""Pre-tokenize MBD-mini PTLS transaction data into train.parquet for TARE pre-training."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
MBD_DIR = ROOT / "data" / "datasets" / "mbd-mini"
OUTPUT_PATH = MBD_DIR / "train.parquet"

MAX_SEQ_LEN = 180
PAD_ID = 0
UNK_ID = 1
AVAILABLE_TOKENS = list(range(2, 50))  # 48 tokens (indices 2–49)


def _build_event_type_mapping(ptls_dir: Path) -> dict[int, int]:
    """Build a deterministic mapping from MBD event_type codes to VOCAB tokens."""
    import glob

    pattern = str(ptls_dir / "trx" / "fold=*" / "*.parquet")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No parquet files found in {ptls_dir / 'trx'}")

    all_types: set[int] = set()
    for f in files:
        df = pd.read_parquet(f, columns=["event_type"])
        for arr in df["event_type"]:
            all_types.update(int(t) for t in arr)

    sorted_types = sorted(all_types)
    mapping: dict[int, int] = {}
    for i, code in enumerate(sorted_types):
        mapping[code] = AVAILABLE_TOKENS[i % len(AVAILABLE_TOKENS)]
    logger.info(
        "Mapped %d unique MBD event_type codes to VOCAB tokens (%d–%d)",
        len(sorted_types),
        min(mapping.values()),
        max(mapping.values()),
    )
    return mapping


def _process_fold(
    fold: int,
    ptls_dir: Path,
    mapping: dict[int, int],
    client_split_dir: Path,
) -> pd.DataFrame:
    """Tokenize all clients in a single fold and return a DataFrame."""
    import glob

    pattern = str(ptls_dir / "trx" / f"fold={fold}" / "*.parquet")
    files = sorted(glob.glob(pattern))
    if not files:
        logger.warning("No trx files for fold=%d, skipping", fold)
        return pd.DataFrame()

    dfs = [pd.read_parquet(f) for f in files]
    trx_df = pd.concat(dfs, ignore_index=True)

    records: list[dict] = []
    for _, row in trx_df.iterrows():
        client_id = row["client_id"]
        event_times = np.asarray(row["event_time"], dtype=np.int64)
        event_types = np.asarray(row["event_type"], dtype=np.int32)

        if len(event_times) == 0:
            continue

        # Map event types to token IDs
        token_ids = [mapping.get(int(t), UNK_ID) for t in event_types]

        # Compute time gaps in days (event_time is unix seconds)
        time_gaps = [0.0] + [
            (event_times[i] - event_times[i - 1]) / 86400.0
            for i in range(1, len(event_times))
        ]

        # Truncate to last MAX_SEQ_LEN events
        if len(token_ids) > MAX_SEQ_LEN:
            token_ids = token_ids[-MAX_SEQ_LEN:]
            time_gaps = time_gaps[-MAX_SEQ_LEN:]

        # Left-pad to MAX_SEQ_LEN
        pad_len = MAX_SEQ_LEN - len(token_ids)
        token_ids = [PAD_ID] * pad_len + token_ids
        time_gaps = [0.0] * pad_len + time_gaps

        records.append({
            "client_id": client_id,
            "token_ids": token_ids,
            "time_gaps": time_gaps,
            "fold": fold,
        })

    result = pd.DataFrame(records)
    logger.info("Fold=%d: tokenized %d clients", fold, len(result))
    return result


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    )

    ptls_dir = MBD_DIR / "ptls"
    client_split_dir = MBD_DIR / "client_split"

    mapping = _build_event_type_mapping(ptls_dir)

    all_folds: list[pd.DataFrame] = []
    for fold in range(5):
        df = _process_fold(fold, ptls_dir, mapping, client_split_dir)
        if not df.empty:
            all_folds.append(df)

    if not all_folds:
        logger.error("No data found — aborting")
        return

    combined = pd.concat(all_folds, ignore_index=True)
    logger.info("Total tokenized sequences: %d", len(combined))

    # Use folds 0-3 for training, fold 4 for validation/test
    train_mask = combined["fold"].isin([0, 1, 2, 3])
    train_df = combined[train_mask].copy()
    logger.info("Training sequences: %d", len(train_df))

    train_df = train_df.drop(columns=["fold", "client_id"])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    train_df.to_parquet(OUTPUT_PATH, index=False)
    logger.info("Saved training data to %s", OUTPUT_PATH)


if __name__ == "__main__":
    main()
