"""Generate synthetic action token sequences from the BankChurners tabular dataset."""

from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "datasets" / "bankchurners" / "BankChurners.csv"
OUTPUT_PATH = ROOT / "data" / "datasets" / "bankchurners" / "synthetic_sequences.parquet"

_TXN_TOKENS = ["CARD_SWIPE", "CARD_TAP", "ONLINE_PURCHASE", "ONLINE_TRANSFER", "BILL_PAYMENT"]
_SUPPORT_TOKEN = "SUPPORT_CONTACT"
_INACTIVITY_TOKEN = "INACTIVITY_14D"
_COMPLAINT_TOKEN = "COMPLAINT_RAISED"

MAX_SEQ = 180
RNG_SEED = 42


def _temporal_distribution(n_txns: int, chng_q4_q1: float) -> list[float]:
    """Return normalized weights for 12 monthly buckets.

    chng_q4_q1 > 1 means more recent activity (front-loaded in timeline = back-loaded in sequence).
    """
    weights = np.ones(12)
    if chng_q4_q1 > 1.0:
        weights[8:] *= chng_q4_q1  # Q4 months get higher weight
    elif chng_q4_q1 < 1.0:
        weights[:4] *= (2.0 - chng_q4_q1)  # Q1 months get higher weight
    weights /= weights.sum()
    counts = np.random.multinomial(n_txns, weights)
    return counts.tolist()


def _build_sequence_for_row(row: dict[str, Any], rng: random.Random) -> list[str]:
    n_txns = int(row["Total_Trans_Ct"])
    chng = float(row["Total_Ct_Chng_Q4_Q1"])
    n_inactive_months = int(row["Months_Inactive_12_mon"])
    n_contacts = int(row["Contacts_Count_12_mon"])
    utilization = float(row["Avg_Utilization_Ratio"])

    monthly_counts = _temporal_distribution(n_txns, chng)
    inactive_months = set(rng.sample(range(12), min(n_inactive_months, 12)))

    tokens: list[str] = []
    for month_idx, count in enumerate(monthly_counts):
        if month_idx in inactive_months:
            tokens.append(_INACTIVITY_TOKEN)
            continue

        # Transaction tokens weighted by utilization
        if utilization > 0.7:
            weights = [0.1, 0.1, 0.4, 0.2, 0.2]  # more online/bill activity
        elif utilization > 0.3:
            weights = [0.3, 0.2, 0.25, 0.15, 0.1]
        else:
            weights = [0.5, 0.2, 0.1, 0.1, 0.1]  # mostly card swipes

        for _ in range(count):
            tokens.append(rng.choices(_TXN_TOKENS, weights=weights)[0])

    # Sprinkle support contacts
    contact_positions = sorted(rng.sample(range(len(tokens)), min(n_contacts, len(tokens))))
    for pos in reversed(contact_positions):
        tokens.insert(pos, _SUPPORT_TOKEN)

    # Add a complaint token if high contacts + churner
    if n_contacts >= 4 and row.get("Attrition_Flag") == "Attrited Customer":
        tokens.append(_COMPLAINT_TOKEN)

    return tokens[-MAX_SEQ:]  # truncate to MAX_SEQ


def generate_sequences(input_path: Path = INPUT_PATH, output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    """Generate synthetic sequences for all BankChurners customers.

    Args:
        input_path: Path to BankChurners.csv.
        output_path: Where to write the output parquet.

    Returns:
        DataFrame with columns [customer_id, token_ids, time_gaps, label].
    """
    from ml.features.sequence_builder import VOCAB, PAD_ID, MAX_SEQ_LEN

    df = pd.read_csv(input_path)
    # Drop the two naive-bayes classifier columns that Kaggle added
    drop_cols = [c for c in df.columns if "Naive_Bayes" in c]
    df.drop(columns=drop_cols, inplace=True, errors="ignore")

    rng = random.Random(RNG_SEED)
    np.random.seed(RNG_SEED)

    records: list[dict] = []
    for idx, row in df.iterrows():
        customer_id = str(row.get("CLIENTNUM", idx))
        label = 1 if row["Attrition_Flag"] == "Attrited Customer" else 0

        action_tokens = _build_sequence_for_row(row.to_dict(), rng)
        token_ids = [VOCAB.get(t, VOCAB["UNK"]) for t in action_tokens]

        # Simple uniform time gaps (1 day between each event)
        time_gaps = [0.0] + [1.0] * (len(token_ids) - 1)

        # Left-pad to MAX_SEQ_LEN
        pad_len = MAX_SEQ_LEN - len(token_ids)
        token_ids = [PAD_ID] * pad_len + token_ids
        time_gaps = [0.0] * pad_len + time_gaps

        records.append({"customer_id": customer_id, "token_ids": token_ids, "time_gaps": time_gaps, "label": label})

    result = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)
    logger.info("Generated %d synthetic sequences → %s", len(result), output_path)
    return result


def _visualize(df: pd.DataFrame, n: int = 5) -> None:
    import matplotlib.pyplot as plt
    from ml.features.sequence_builder import VOCAB

    id_to_token = {v: k for k, v in VOCAB.items()}
    fig, axes = plt.subplots(n, 1, figsize=(14, 3 * n))

    for i, ax in enumerate(axes):
        row = df.iloc[i]
        ids = [t for t in row["token_ids"] if t != 0]
        labels_str = [id_to_token.get(t, "?") for t in ids]
        ax.barh(range(len(ids)), [1] * len(ids))
        ax.set_yticks(range(len(ids)))
        ax.set_yticklabels(labels_str, fontsize=6)
        ax.set_title(f"customer={row['customer_id']} label={row['label']}")

    plt.tight_layout()
    plt.savefig("synthetic_sequences_sample.png", dpi=100)
    logger.info("Saved visualization to synthetic_sequences_sample.png")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Generate synthetic sequences from BankChurners")
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--visualize", action="store_true", help="Plot 5 example sequences")
    args = parser.parse_args()

    df = generate_sequences(args.input, args.output)
    if args.visualize:
        _visualize(df)


if __name__ == "__main__":
    main()
