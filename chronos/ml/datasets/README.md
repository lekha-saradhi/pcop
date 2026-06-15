# CHRONOS Training Datasets

## Dataset Provenance and Licenses

| Dataset | Source | License | Size | Purpose |
|---------|--------|---------|------|---------|
| MBD-mini | HuggingFace `ai-lab/MBD-mini` | Research | ~50K rows | TARE pre-training (sequence data) |
| PKDD'99 Czech Financial | Kaggle `niteshyadav3103/czech-financial-dataset-pkdd-1999` | Public Domain | ~1M transactions | HABITAT tabular validation |
| Bank Customer Churn | Kaggle `gauravtopre/bank-customer-churn-dataset` | CC0 Public Domain | 10K rows | HABITAT Pass 1 + GENESIS training |
| Credit Card Customers (BankChurners) | Kaggle `sakshigoyal7/credit-card-customers` | DbCL 1.0 | 10K rows | TARE fine-tuning (synthetic sequences) |
| Hillstrom MineThatData | `scikit-uplift fetch_hillstrom()` | Public Domain | 64K rows | CAUSAL-NET fine-tuning |
| Criteo Uplift | `scikit-uplift fetch_criteo()` | Criteo Research | ~25M rows | CAUSAL-NET pre-training |
| UCI Bank Marketing | UCI ML Repository | CC BY 4.0 | 45K rows | GENESIS training |

## Data Storage

All datasets are stored under `data/datasets/` (gitignored). Raw data is never committed to git.

## Downloading

```bash
python ml/datasets/download_public_datasets.py
# or for a single dataset:
python ml/datasets/download_public_datasets.py --dataset bankchurners
# dry run (preview without downloading):
python ml/datasets/download_public_datasets.py --dry-run
```

**Prerequisites:**
- Kaggle API token at `~/.kaggle/kaggle.json`
- HuggingFace CLI logged in (`huggingface-cli login`) for MBD-mini if private

## No PII

All datasets are public research datasets. No real customer PII is used at any stage of CHRONOS development or training.
