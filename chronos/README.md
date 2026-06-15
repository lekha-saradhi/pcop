# CHRONOS — Neural Risk Intelligence Engine
### Layer 3 ML Scoring System

CHRONOS is the machine-learning scoring layer of the PCOP (Proactive Customer Outreach Platform). It predicts customer churn probability, treatability, and recommended action tier using a pipeline of six neural and statistical models coordinated through adaptive fusion.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Model Components](#2-model-components)
3. [Scoring Pipeline](#3-scoring-pipeline)
4. [Project Structure](#4-project-structure)
5. [Setup & Installation](#5-setup--installation)
6. [Dataset Download](#6-dataset-download)
7. [Training Guide](#7-training-guide)
8. [Running the Service](#8-running-the-service)
9. [API Reference](#9-api-reference)
10. [Scheduled Tasks](#10-scheduled-tasks)
11. [Monitoring & Drift Detection](#11-monitoring--drift-detection)
12. [Sprint Audit Checklists](#12-sprint-audit-checklists)
13. [Development Guide](#13-development-guide)
14. [Runbook — Common Failure Scenarios](#14-runbook--common-failure-scenarios)

---

## 1. Architecture Overview

```
                        ┌─────────────────────────────────────────────┐
                        │            CHRONOS Layer 3                   │
                        │                                               │
  Customer              │  ┌─────────┐    ┌──────────┐                │
  Action History ──────►│  │  TARE   │    │ HABITAT  │                │
  (token sequence)      │  │  GRU+   │    │ XGBoost  │                │
                        │  │ Attn.   │    │ Pass 1   │                │
  Tabular Features ────►│  └────┬────┘    └────┬─────┘                │
                        │       │              │                        │
                        │       └──────┬───────┘                       │
                        │              │                                │
                        │         ┌────▼─────┐                         │
                        │         │ FUSION-X │  Adaptive weights       │
                        │         │ Bayesian │  + ECE calibration      │
                        │         └────┬─────┘                         │
                        │              │                                │
                        │    ┌─────────▼──────────┐                    │
                        │    │      PRISM          │  Reason codes      │
                        │    │  9-category merge   │  (top 3)           │
                        │    └─────────┬───────────┘                    │
                        │              │                                │
                        │    ┌─────────▼───────────┐                   │
                        │    │     CAUSAL-NET       │  Treatability     │
                        │    │   Two-tower uplift   │  + Action score   │
                        │    └─────────────────────┘                   │
                        │                                               │
  New customer          │  ┌─────────┐   SENTINEL   AEGIS              │
  (< 90 days) ─────────►│  │ GENESIS │   Real-time  Drift              │
                        │  │   LR    │   re-scoring  guard             │
                        │  └─────────┘                                 │
                        └─────────────────────────────────────────────┘
```

### System interactions

| Layer | System | Direction |
|-------|--------|-----------|
| Upstream | PCOP account events (`pcop.account_events.v1`) | → CHRONOS |
| Upstream | BOCPD alarm signals (`pcop.alarms.v1`) | → CHRONOS |
| Upstream | Layer 4 life events | → CHRONOS (Pass 2 trigger) |
| Downstream | Risk scores (`pcop.scores.v1`) | CHRONOS → |
| Downstream | `churn_scores` table | CHRONOS → |
| Sidecar | Redis feature cache | CHRONOS ↔ |
| Sidecar | MLflow experiment tracker | CHRONOS → |

---

## 2. Model Components

### TARE — Temporal Action Recurrence Encoder
**File:** `services/scoring/models/tare_encoder.py`

Sequence model that processes a customer's ordered action history (up to 180 tokens) and outputs a churn probability plus attention weights used as reason codes.

| Property | Value |
|----------|-------|
| Architecture | Embedding(50→128) + TimeGapEncoding + BiGRU(128×2, 2 layers) + Bahdanau Attention + Dense(256→64→1) |
| Parameters | ~855K |
| Input | `token_ids` (int64, len=180) + `time_gaps` (float32, len=180) |
| Output | `churn_prob` (float), `attention_weights` (len=180) |
| Serving | ONNX Runtime (CPU), target < 50ms single customer |
| Pre-training | Masked action prediction on MBD-mini |
| Fine-tuning | Binary churn on synthetic BankChurners sequences |

**Token vocabulary:** 50 action types including `CARD_SWIPE`, `SUPPORT_CONTACT`, `INACTIVITY_7D/14D/30D`, `ACCOUNT_CLOSURE_REQUEST`, etc. See `ml/features/sequence_builder.py::VOCAB`.

---

### HABITAT — Hierarchical Adaptive Behaviour and Interaction Tabular scorer
**Files:** `services/scoring/models/habitat_scorer.py`, `habitat_pass2.py`

XGBoost model scoring customers on 14 tabular behavioural features. Pass 2 adds 9 life-event features when triggered by Layer 4.

| Property | Pass 1 | Pass 2 |
|----------|--------|--------|
| Features | 14 | 23 (14 + 9 life events) |
| Trigger | Always | score ≥ 0.35 AND life_events ≥ 1 |
| Training data | Bank Customer Churn (10K) | Production data (week 8+) |
| Validation | PKDD'99 Czech Financial | — |
| Format | XGBoost JSON | XGBoost JSON |
| Reason codes | SHAP values → top 3 features | SHAP values |

**Pass 1 features:** `recency_days`, `monetary_avg`, `monetary_total`, `frequency_30d`, `frequency_90d`, `decline_rate_30d`, `support_contacts_90d`, `inactivity_streak_days`, `product_count`, `digital_ratio`, `avg_utilization`, `complaint_open_count`, `tenure_days`, `channel_diversity`

---

### FUSION-X — Adaptive Bayesian Score Fusion
**File:** `services/scoring/fusion/fusion_x.py`

Combines TARE and HABITAT scores with daily recalibrated weights. Falls back to static weights (0.55/0.45) when fewer than 500 labelled outcomes are available.

| Property | Value |
|----------|-------|
| Default weights | TARE: 0.55, HABITAT: 0.45 |
| Recalibration | Daily, Inverse-Brier weighting |
| CI method | 200-sample bootstrap |
| ECE warning | 0.08 |
| ECE critical | 0.15 |
| Drift check | Every 6 hours |

---

### PRISM — Probabilistic Reason Integration & Signal Merging
**File:** `services/scoring/fusion/prism_reconciler.py`

Maps TARE attention tokens and HABITAT SHAP codes to a shared 9-category taxonomy, weights by fusion weights, deduplicates semantic overlaps, and outputs top-3 unified reason codes.

**Taxonomy categories:**
`transaction_decline` · `engagement_drop` · `complaint_escalation` · `financial_stress` · `income_change` · `competitor_risk` · `location_change` · `product_disengagement` · `inactivity`

---

### GENESIS — Graduated Entry Neural-less Initial Scoring System
**File:** `services/scoring/models/genesis_scorer.py`

Logistic Regression cold-start scorer for customers with < 90 days tenure or < 30 action tokens. Graduates customers to TARE+HABITAT once both thresholds are crossed.

| Property | Value |
|----------|-------|
| Features | 7 (tenure, products, age_bucket, income_band, channel, credit_score_band, city_tier) |
| Algorithm | L2 Logistic Regression (C=1.0, balanced class weights) |
| Training data | Bank Customer Churn (10K) + UCI Bank Marketing (45K) |
| Graduation | tenure_days ≥ 90 AND token_count ≥ 30 |
| Retraining | Monthly |

---

### CAUSAL-NET — Counterfactual Action Uplift System
**File:** `services/scoring/models/causal_net.py`

Two-tower uplift model sharing TARE's frozen GRU backbone. Outputs treatability probability (P(respond to intervention | churner)) and combines it with churn probability to produce an action score.

| Property | Value |
|----------|-------|
| Backbone | Frozen TARE encoder (weights do not update) |
| Treatability head | Dense(320→64) + LayerNorm + ReLU + Dropout + Dense(64→1) |
| Combined output | `action_score = p_churn × p_treatable` |
| Pre-training | S-Learner on Criteo Uplift (25M rows) |
| Fine-tuning | T-Learner on Hillstrom (64K rows) |
| Default mode | treatability = 0.5 (until training completes, week 12+) |
| Retraining | Bi-weekly |

**Action tiers:**

| Tier | p_churn | p_treatable |
|------|---------|-------------|
| PRIORITY | > 0.80 | > 0.60 |
| ESCALATE | > 0.60 | > 0.50 |
| STANDARD | > 0.40 | > 0.40 |
| MONITOR | > 0.20 | any |
| NONE | ≤ 0.20 | any |

---

### SENTINEL — Real-Time Re-Scorer
**File:** `services/scoring/serving/sentinel_realtime.py`

Kafka consumer that re-scores individual customers within 50ms when triggered events arrive.

**Trigger conditions:**
- `ACCOUNT_CLOSURE_REQUEST` event type
- BOCPD joint detector fires (`bocpd_fired: true`)
- Current Pass 1 score crosses 0.80
- Customer is at High tier and receives any new signal

---

### AEGIS — Automated Explicit Guard for Input Signals
**File:** `services/scoring/guards/aegis_detector.py`

Per-batch drift guard that runs before scoring on every batch.

| Check | Method | Threshold | Action |
|-------|--------|-----------|--------|
| Feature drift | KL divergence vs training dist. | KL > 0.5 per feature | Log warning, continue, flag dashboard |
| Vocab drift | Novel token fraction | > 5% | Map to UNK, continue |
| Distribution shift | MMD two-sample test (RBF kernel) | p-value < 0.01 | Set `anomaly_flag=TRUE`, alert ML team |

---

## 3. Scoring Pipeline

### Full 6-hour batch pipeline

```
┌─────────────────────────────────────────────────────────┐
│  batch_scorer.run_full_pipeline()                        │
│                                                          │
│  1. AEGIS input validation                               │
│  2. Tenure gate                                          │
│     ├─ tenure < 90d OR tokens < 30 → GENESIS (cold)     │
│     └─ otherwise → continue                              │
│  3. TARE + HABITAT Pass 1 (parallel, ThreadPoolExecutor) │
│     ├─ TARE fails → use HABITAT only                     │
│     └─ HABITAT fails → use TARE only                     │
│  4. FUSION-X: combine scores + bootstrap CI              │
│  5. PRISM: reconcile reason codes                        │
│  6. Assign risk tier (critical/high/medium/low)          │
│  7. Write to churn_scores (PostgreSQL)                   │
│  8. Publish tier changes to pcop.scores.v1 (Kafka)       │
└─────────────────────────────────────────────────────────┘
```

### After Layer 4 (life events available)

```
HABITAT Pass 2 runs if:
  pass1_score ≥ 0.35  AND  life_event_count ≥ 1

Then CAUSAL-NET scores treatable customers:
  action_score = p_churn × p_treatable
```

### Real-time path (SENTINEL, < 50ms target)

```
Kafka message → _should_trigger() → Redis feature cache
              → ONNX Runtime inference → write DB + publish Kafka
```

---

## 4. Project Structure

```
layer3 ml scoring/
├── api/                              # FastAPI service
│   ├── main.py                       # App entry point + scheduler startup
│   ├── models/
│   │   └── risk.py                   # Pydantic response schemas
│   └── routers/
│       ├── risk_scores.py            # GET /scores, GET /scores/{id}
│       └── model_health.py           # GET /model-health
│
├── ml/                               # Training and data code
│   ├── checkpoints/                  # Saved model artifacts (gitignored)
│   ├── datasets/
│   │   ├── download_public_datasets.py
│   │   ├── manifest.json             # Dataset registry with checksums
│   │   └── README.md                 # Dataset provenance & licenses
│   ├── features/
│   │   ├── sequence_builder.py       # Token vocab, build_sequence(), is_cold_start()
│   │   ├── tabular_features.py       # extract_pass1_features(), extract_pass2_features()
│   │   ├── cold_start_features.py    # extract_cold_start_features()
│   │   └── tests/
│   ├── generators/
│   │   ├── synthetic_sequences_from_bankchurners.py
│   │   └── tests/
│   ├── training/
│   │   ├── tare_pretrain.py          # Masked action prediction pre-training
│   │   ├── tare_finetune.py          # Binary churn fine-tuning
│   │   ├── export_onnx.py            # ONNX export + verify + benchmark
│   │   ├── habitat_train.py          # XGBoost Pass 1
│   │   ├── genesis_train.py          # Logistic Regression cold-start
│   │   └── causal_net_train.py       # S-Learner + T-Learner uplift
│   └── register_all_models.py        # MLflow model registration
│
├── services/
│   └── scoring/
│       ├── models/
│       │   ├── tare_encoder.py       # TAREEncoder, BahdanauAttention, TAREPretrainHead
│       │   ├── habitat_scorer.py     # HABITATScorer (XGBoost + SHAP)
│       │   ├── habitat_pass2.py      # HabitatPass2Scorer, is_eligible_for_pass2()
│       │   ├── genesis_scorer.py     # GENESISScorer, is_graduated()
│       │   ├── causal_net.py         # CausalNet, TreatabilityHead, ActionTier
│       │   └── tests/
│       ├── fusion/
│       │   ├── fusion_x.py           # FusionX, DriftStatus, _compute_ece()
│       │   ├── calibration.py        # PlattCalibrator
│       │   ├── prism_reconciler.py   # PRISMReconciler, ReasonCode, taxonomy maps
│       │   └── tests/
│       ├── guards/
│       │   ├── aegis_detector.py     # AEGISDetector, DriftAlert, _mmd_permutation_test()
│       │   └── tests/
│       ├── serving/
│       │   ├── sentinel_realtime.py  # SENTINELRealTimeScorer, Kafka consumer
│       │   ├── onnx_runtime.py       # TARERuntimeSession (ONNX Runtime wrapper)
│       │   ├── batch_scorer.py       # BatchScorer, run_full_pipeline()
│       │   └── tests/
│       ├── tests/
│       │   ├── conftest.py           # 20 dummy customers + fixtures
│       │   └── test_integration.py   # 10 end-to-end integration tests
│       ├── scheduler.py              # APScheduler — 10 recurring tasks
│       └── Dockerfile
│
├── infra/
│   └── postgres/
│       └── migrations/
│           └── versions/
│               ├── 001_rename_transformer_to_tare.py
│               ├── 002_add_chronos_columns.py    # treatability, action, scoring_pass, reason_codes_v2, anomaly_flag
│               └── 003_add_signal_expiry.py       # expires_at on signal_results
│
├── data/                             # Downloaded datasets (gitignored)
│   └── datasets/
│       ├── mbd-mini/
│       ├── pkdd99/
│       ├── bank-churn/
│       ├── bankchurners/
│       ├── hillstrom/
│       ├── criteo-uplift/
│       └── uci-bank-marketing/
│
├── docker-compose.yml                # Postgres, Redis, Kafka, MLflow, scoring service
├── pyproject.toml                    # Dependencies + pytest + mypy + ruff config
├── .env.example                      # Environment variable template
└── README.md                         # This file
```

---

## 5. Setup & Installation

### Prerequisites

- Python 3.11+
- Poetry (`pip install poetry`)
- Docker + Docker Compose
- Kaggle API token at `~/.kaggle/kaggle.json`

### Install dependencies

```bash
cd "layer3 ml scoring"
poetry install
```

### Environment configuration

```bash
cp .env.example .env
# Edit .env with your database URL, Redis, Kafka, MLflow settings
```

---

## 6. Dataset Download

Seven public datasets are required for training. Download all at once:

```bash
python ml/datasets/download_public_datasets.py
```

Download a single dataset:

```bash
python ml/datasets/download_public_datasets.py --dataset bankchurners
```

Preview without downloading:

```bash
python ml/datasets/download_public_datasets.py --dry-run
```

| Dataset | Used by | Size |
|---------|---------|------|
| `mbd-mini` (HuggingFace) | TARE pre-training | ~50K rows |
| `pkdd99` (Kaggle) | HABITAT validation | ~1M transactions |
| `bank-churn` (Kaggle `gauravtopre`) | HABITAT Pass 1 + GENESIS | 10K rows |
| `bankchurners` (Kaggle `sakshigoyal7`) | TARE fine-tuning (synthetic) | 10K rows |
| `hillstrom` (scikit-uplift) | CAUSAL-NET fine-tuning | 64K rows |
| `criteo-uplift` (scikit-uplift) | CAUSAL-NET pre-training | 25M rows |
| `uci-bank-marketing` (UCI) | GENESIS training | 45K rows |

---

## 7. Training Guide

Run training scripts in the following order. Each script is standalone — pass `--help` for all options.

### Step 1 — Generate synthetic sequences

```bash
python ml/generators/synthetic_sequences_from_bankchurners.py
# optional: visualise 5 example sequences
python ml/generators/synthetic_sequences_from_bankchurners.py --visualize
```

Output: `data/datasets/bankchurners/synthetic_sequences.parquet`

---

### Step 2 — Train GENESIS (fastest, no GPU needed)

```bash
python ml/training/genesis_train.py
```

Output: `ml/checkpoints/genesis_lr.pkl`
Target: 5-fold CV AUC > 0.65

---

### Step 3 — Pre-train TARE

```bash
# Quick dev run (1% of data)
python ml/training/tare_pretrain.py --subset 0.01

# Full pre-training
python ml/training/tare_pretrain.py --epochs 10
```

Output: `ml/checkpoints/tare_pretrain_final.pt`
Resume from checkpoint: `--resume ml/checkpoints/tare_pretrain_epoch4.pt`

---

### Step 4 — Fine-tune TARE

```bash
python ml/training/tare_finetune.py \
  --pretrain-checkpoint ml/checkpoints/tare_pretrain_final.pt
```

Output: `ml/checkpoints/tare_finetune_final.pt` (includes Platt scaling params)
Target: AUC > 0.70 on BankChurners test set

---

### Step 5 — Export TARE to ONNX

```bash
python ml/training/export_onnx.py \
  --checkpoint ml/checkpoints/tare_finetune_final.pt \
  --output ml/checkpoints/tare_churn.onnx
```

This also runs:
- PyTorch vs ONNX output verification (max diff < 1e-5)
- Throughput benchmark at batch sizes 1, 16, 64

---

### Step 6 — Train HABITAT Pass 1

```bash
python ml/training/habitat_train.py
```

Output: `ml/checkpoints/habitat_pass1.json` + `habitat_shap_summary.png`
Target: AUC > 0.75 on Bank Customer Churn test set

---

### Step 7 — Train CAUSAL-NET (optional, can run in default mode)

```bash
# Full pipeline (Criteo + Hillstrom)
python ml/training/causal_net_train.py

# Hillstrom only (faster, skip 25M-row Criteo)
python ml/training/causal_net_train.py --skip-criteo
```

Output: `ml/checkpoints/causal_net_treated.json`, `causal_net_control.json`
Note: Until this completes, CAUSAL-NET runs in default mode (treatability = 0.5).

---

### Step 8 — Register all models in MLflow

```bash
python ml/register_all_models.py
# dry run:
python ml/register_all_models.py --dry-run
# single model:
python ml/register_all_models.py --model tare-encoder
```

---

### Step 9 — Apply database migrations

```bash
cd infra/postgres
alembic upgrade head
```

---

## 8. Running the Service

### Docker Compose (recommended)

```bash
docker-compose up -d
```

Services started:
| Service | Port |
|---------|------|
| Scoring API | 8003 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Kafka | 9092 |
| MLflow UI | 5000 |

### Local development

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8003 --reload
```

### Health check

```bash
curl http://localhost:8003/health
# → {"status":"ok","service":"chronos-scoring"}
```

---

## 9. API Reference

### GET `/scores/{customer_id}`

Return the latest CHRONOS score for a single customer.

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `customer_id` | string | |
| `final_score` | float [0,1] | Fused churn probability |
| `risk_tier` | enum | `critical` / `high` / `medium` / `low` |
| `tare_score` | float? | TARE model output |
| `habitat_score` | float? | HABITAT Pass 1 or 2 output |
| `treatability_score` | float? | CAUSAL-NET treatability |
| `action_score` | float? | `p_churn × p_treatable` |
| `scoring_pass` | string? | `pass1` / `pass2` / `cold-start` |
| `reason_codes` | string[] | Legacy TEXT[] reason codes |
| `reason_codes_v2` | ReasonCode[] | PRISM structured reason codes |
| `anomaly_flag` | bool | AEGIS flagged this customer |
| `model_version` | string | e.g. `fusion-x-v1.0` |
| `scored_at` | datetime | |
| `is_cold_start` | bool | Scored by GENESIS |

**ReasonCode schema:**
```json
{
  "category": "inactivity",
  "description": "Extended periods of account inactivity",
  "importance": 0.87,
  "source": "sequence"
}
```

---

### GET `/scores`

List scores with optional filtering.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `anomaly_only` | bool | Return only `anomaly_flag=TRUE` |
| `tier` | string | Comma-separated tiers: `critical,high` |
| `page` | int | Default 1 |
| `page_size` | int | Default 50, max 500 |

---

### GET `/scores/{customer_id}/reason-codes`

Return full PRISM `reason_codes_v2` for a customer.

---

### GET `/model-health`

Return current state of all CHRONOS components.

**Response:**
```json
{
  "fusion_tare_weight": 0.55,
  "fusion_habitat_weight": 0.45,
  "fusion_ece": 0.032,
  "fusion_last_calibration": "2026-05-12T04:00:00Z",
  "aegis_drift_status": "normal",
  "components": [
    {"name": "tare-encoder", "version": "v1.0", "status": "healthy", "metrics": {}},
    {"name": "habitat-pass1", "version": "v1.0", "status": "healthy", "metrics": {}},
    {"name": "fusion-x",     "version": "v1.0", "status": "healthy", "metrics": {}},
    {"name": "causal-net",   "version": "v1.0", "status": "healthy", "metrics": {}},
    {"name": "genesis",      "version": "v1.0", "status": "healthy", "metrics": {}},
    {"name": "aegis",        "version": "v1.0", "status": "healthy", "metrics": {}}
  ],
  "overall_status": "healthy"
}
```

---

### GET `/model-health/scheduler`

Return APScheduler job status.

---

## 10. Scheduled Tasks

All tasks managed by `services/scoring/scheduler.py` using APScheduler.

| Task | Schedule | Function |
|------|----------|----------|
| Full batch scoring | Every 6 hours | `batch_scorer.run_full_pipeline()` |
| AEGIS drift check | Every 6 hours | `aegis.check_drift()` |
| FUSION-X ECE check | Every 6 hours | `fusion_x.check_ece()` |
| FUSION-X recalibration | Daily 04:00 UTC | `fusion_x.recalibrate_weights()` |
| GENESIS graduations | Daily 05:00 UTC | `genesis.evaluate_graduations()` |
| HABITAT Pass 2 | Daily 07:00 UTC (after Layer 4) | `habitat_pass2.run_conditional()` |
| CAUSAL-NET scoring | Daily 08:00 UTC (after Pass 2) | `causal_net.score_treatable()` |
| MLflow retrain trigger | Weekly Sunday 02:00 UTC | |
| CAUSAL-NET retraining | Bi-weekly Monday 03:00 UTC | |
| GENESIS retraining | Monthly 1st 06:00 UTC | |

---

## 11. Monitoring & Drift Detection

### AEGIS checks (every 6 hours)

```python
from services.scoring.guards.aegis_detector import AEGISDetector

detector = AEGISDetector()
detector.load_reference_distributions("ml/checkpoints/aegis_reference.json")

feature_alerts = detector.check_features(batch_features, feature_names)
vocab_alerts   = detector.check_sequences(batch_sequences)
mmd_alert      = detector.check_multivariate(batch_features)
```

### FUSION-X calibration monitoring

```python
from services.scoring.fusion.fusion_x import FusionX, DriftStatus

fusion = FusionX()
alert = fusion.check_drift(recent_predictions, recent_outcomes)
if alert.status == DriftStatus.CRITICAL:
    # ECE > 0.15 — trigger emergency retraining
    ...
```

### SENTINEL latency monitoring

```python
from services.scoring.serving.sentinel_realtime import SENTINELRealTimeScorer

latency = SENTINELRealTimeScorer.latency_percentiles()
# {"p50": 12.3, "p95": 38.7, "p99": 49.1}
```

### Key metrics to watch

| Metric | Warning | Critical | Location |
|--------|---------|----------|----------|
| TARE AUC | < 0.70 | < 0.65 | MLflow |
| HABITAT AUC | < 0.75 | < 0.70 | MLflow |
| FUSION-X ECE | > 0.08 | > 0.15 | `/model-health` |
| SENTINEL p99 latency | > 40ms | > 50ms | `/model-health` |
| AEGIS novel token % | > 3% | > 5% | Logs |
| GENESIS CV AUC | < 0.65 | < 0.60 | MLflow |

---

## 12. Sprint Audit Checklists

### Sprint 1 — Foundation

```
□ All 7 datasets download successfully with checksum match
□ Alembic migrations apply cleanly (upgrade + downgrade)
□ sequence_builder produces valid token sequences from dummy data
□ tabular_features extracts all 14 Pass 1 features
□ cold_start_features extracts all 7 features
□ Synthetic sequence generator produces 10K sequences
□ All unit tests pass
□ No hardcoded credentials or API keys in any file
□ All files have type hints and docstrings
□ pyproject.toml updated with new dependencies
```

### Sprint 2 — TARE

```
□ TAREEncoder forward pass produces correct output shapes
□ Parameter count matches spec (~855K)
□ Pre-training script runs on --subset without errors
□ Pre-training loss decreases over epochs
□ Fine-tuning achieves AUC > 0.70 on BankChurners test set
□ Attention weights sum to 1.0 for each sequence
□ Reason codes extract correctly (top-3 non-PAD tokens)
□ ONNX export matches PyTorch output within 1e-5
□ ONNX throughput > 300 seq/sec at batch=64
□ All checkpoints saved with metadata
□ No data leakage between train/val/test splits
□ MLflow experiment tracking working
```

### Sprint 3 — HABITAT

```
□ HABITAT Pass 1 achieves AUC > 0.75 on Bank Customer Churn
□ All 14 features extract correctly from both datasets
□ SHAP values compute without errors for all test samples
□ SHAP reason codes are human-readable and sensible
□ Feature importance ranking logged to MLflow
□ Pass 2 scaffold compiles and passes type checks
□ Pass 2 trigger logic correctly filters on score + life events
□ No feature leakage (target not included in features)
□ Model saved in XGBoost JSON format (not pickle)
```

### Sprint 4 — FUSION-X, PRISM, GENESIS

```
□ FUSION-X produces calibrated probabilities (ECE < 0.05)
□ Adaptive weights sum to 1.0
□ Bootstrap CI covers true churn rate in 95% of samples
□ Drift detection correctly flags synthetic drift injection
□ PRISM maps all TARE token types to taxonomy categories
□ PRISM maps all HABITAT features to taxonomy categories
□ PRISM deduplication works when both models flag same category
□ PRISM output matches ReasonCode schema
□ GENESIS achieves AUC > 0.65 on cross-validation
□ GENESIS graduation logic correctly identifies eligible customers
□ All unit tests pass with > 90% code coverage
```

### Sprint 5 — CAUSAL-NET

```
□ CausalNet forward pass produces all three outputs correctly
□ TARE backbone weights do not change during treatability training
□ Treatability head trains without gradient flow to TARE
□ Criteo S-Learner produces non-zero uplift estimates
□ Hillstrom T-Learner achieves positive Qini coefficient
□ Action score = p_churn × p_treatable for all test samples
□ Decision matrix maps correctly for all tier combinations
□ Default mode (treatability=0.5) produces expected action scores
□ Uplift curve saved as MLflow artifact
```

### Sprint 6 — SENTINEL & AEGIS

```
□ SENTINEL re-scores a single customer in < 50ms
□ SENTINEL correctly triggers on all 4 event types
□ SENTINEL circuit breaker activates on Redis failure
□ AEGIS detects synthetic feature drift (inject 2σ shift)
□ AEGIS detects novel tokens (inject unknown action type)
□ AEGIS MMD test fires on shuffled distribution
□ Batch scorer processes 1000 dummy customers without error
□ Batch scorer parallelises TARE and HABITAT correctly
□ Batch scorer handles TARE failure gracefully (HABITAT fallback)
□ All results written to churn_scores with correct model_version
□ Tier changes published to Kafka topic
```

### Sprint 7 — Integration & API

```
□ All new API endpoints return valid JSON
□ Existing endpoints still work (no regressions)
□ /model-health returns current state of all components
□ All 7 models registered in MLflow with full metadata
□ All 10 integration tests pass
□ Cold-start routing works for tenure < 90 days
□ Pass 2 trigger logic works correctly
□ Backward compatibility: old TEXT[] reason_codes still populated
□ API response times < 200ms for single customer queries
□ No N+1 query patterns in new endpoints
```

### Sprint 8 — Hardening

```
□ All scheduled tasks run on time in local dev
□ Scheduler health endpoint returns correct status
□ Docker image builds successfully
□ Docker compose starts scoring service with all dependencies
□ Scoring service connects to Postgres, Redis, Kafka
□ Service handles graceful shutdown (SIGTERM)
□ Memory usage stable over 24-hour soak test
□ No uncaught exceptions in logs during soak test
□ All model checkpoints loadable from Docker volume mount
```

---

## 13. Development Guide

### Running tests

```bash
# All tests
pytest

# Single module
pytest ml/features/tests/

# With coverage report
pytest --cov=. --cov-report=html

# Integration tests only
pytest services/scoring/tests/test_integration.py -v
```

### Code quality

```bash
# Lint
ruff check .

# Type check
mypy .
```

### Per-sprint code review checklist (before merge)

```
CODE QUALITY
  □ All functions have type hints
  □ All public functions have docstrings
  □ No functions exceed 50 lines
  □ No files exceed 500 lines
  □ No hardcoded credentials, API keys, or secrets
  □ No print() statements (use logging module)
  □ No TODO/FIXME without linked issue number
  □ Conventional commit messages on all commits

TESTING
  □ Unit test coverage > 85% for new code
  □ All edge cases tested (empty input, None, boundary values)
  □ No tests depend on external services (mock everything)
  □ Tests run in < 60 seconds total

SECURITY
  □ No SQL injection vectors (parameterised queries only)
  □ No pickle deserialization of untrusted data
  □ XGBoost models saved as JSON, not pickle
  □ No eval() or exec() anywhere
  □ All user-facing inputs validated with Pydantic

DATA INTEGRITY
  □ No data leakage between train/val/test splits
  □ No future information in features (no look-ahead bias)
  □ All feature computations use as_of_date parameter
  □ Customer PII never logged or stored in model artifacts

MODEL GOVERNANCE
  □ All models registered in MLflow with full metadata
  □ Model version string: {model}-{pass}-v{major}.{minor}
  □ Calibration metrics (ECE, Brier) computed and logged
  □ Reason codes are human-readable and not misleading
```

### What to NEVER include

```
✗ Real customer data (all development uses synthetic/public datasets)
✗ Production database credentials
✗ Customer PII in test fixtures
✗ Model weights in git (use MLflow artifact store or git-lfs)
✗ Jupyter notebooks in main branch (scripts only)
✗ Commented-out code blocks
✗ Multiple model architectures "just in case"
✗ Wandb, Neptune, or other trackers (MLflow only)
✗ Pickle for XGBoost models (use JSON format)
✗ Compliance/regulatory text in code comments
```

---

## 14. Runbook — Common Failure Scenarios

### SENTINEL latency exceeds 50ms

**Symptom:** `p99 latency > 50ms` in `/model-health`

**Investigation:**
```bash
# Check Redis cache hit rate
redis-cli info stats | grep keyspace

# Check ONNX session initialization
grep "ONNX Runtime session" logs/scoring.log
```

**Resolution:**
1. Verify Redis is healthy and features are pre-warmed
2. If Redis is down, SENTINEL falls back to DB — increase DB connection pool
3. If ONNX model is too large, reduce batch size or switch to quantised model

---

### AEGIS flags `DISTRIBUTION_SHIFT` (MMD p-value < 0.01)

**Symptom:** `anomaly_flag=TRUE` on large fraction of customers; AEGIS alert in logs

**Investigation:**
```bash
grep "MMD distribution shift" logs/scoring.log
# Check which features are drifting
grep "FEATURE_DRIFT" logs/scoring.log
```

**Resolution:**
1. Check if upstream data pipeline changed feature extraction
2. Check if new event types are being ingested (VOCAB_DRIFT first)
3. If legitimate distribution shift: update AEGIS reference distributions and trigger retraining
4. If data pipeline bug: roll back upstream, do NOT retrain on corrupted data

---

### FUSION-X ECE exceeds 0.15 (CRITICAL)

**Symptom:** `/model-health` shows `aegis_drift_status: critical`; ECE alert in MLflow

**Resolution:**
1. Re-run Platt scaling calibration on recent labelled outcomes
2. If fewer than 500 outcomes: wait or use static weights (auto-fallback)
3. If persistent: trigger emergency TARE/HABITAT retraining via MLflow pipeline
4. Check that outcome labels are correct (not stale/mislabelled)

---

### Model checkpoint missing at startup

**Symptom:** `FileNotFoundError` in service logs; `/model-health` shows `unavailable`

**Resolution:**
```bash
# Verify checkpoint volume mount
docker inspect chronos-scoring | grep -A5 Mounts

# Re-download from MLflow
python ml/register_all_models.py --dry-run  # find the run ID
mlflow artifacts download --run-id <run_id> --artifact-path model -d ml/checkpoints/

# Or re-train from scratch (see Training Guide step 3+)
```

---

### GENESIS graduation not firing

**Symptom:** Customers with > 90 days tenure still getting cold-start scores

**Check:**
```python
from services.scoring.models.genesis_scorer import GENESISScorer
scorer = GENESISScorer()
print(scorer.is_graduated(tenure_days=95, token_count=35))  # should be True
```

**Resolution:**
1. Check `tenure_days` field is being populated correctly in CustomerRecord
2. Check `token_count` (non-PAD tokens) is being computed before routing decision
3. Verify daily graduation job is running: `GET /model-health/scheduler`

---

### Kafka consumer (SENTINEL) stops processing

**Symptom:** No SENTINEL re-scores for > 10 minutes despite events in topic

**Resolution:**
```bash
# Check consumer group lag
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group chronos-sentinel

# Restart consumer (rolling, no data loss)
docker-compose restart scoring
```

---

*For additional support, file an issue in the PCOP ML team tracker.*
