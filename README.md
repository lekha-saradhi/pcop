# PCOP — Predictive Customer Outreach Platform

> **NextGenHacks 2026** · Open-Ended AI Track

---

## Problem Statement

Financial institutions lose customers silently. Churn takes 60–90 days to appear in account closure data — by which point intervention is too late. There is no widely accessible tool that watches behavioural signals in real time, predicts which customers are approaching a decision point, and automatically reaches out with the right message before they disengage.

PCOP solves this with a fully agentic, seven-layer AI/ML platform that does exactly that.

---

## Live Demo

🔗 **Live App:** *(coming soon — being redeployed)*

🎥 **Demo Video:** *(coming soon)*

📓 **Technical Walkthrough:** [Open in Google Colab](https://colab.research.google.com/drive/1tiDh2XmvveAawni4vIpCrFXk_Pn8FhYx?usp=sharing)

**Demo credentials:**

| Role | Username | Password |
|------|----------|----------|
| Administrator | `admin` | `admin123` |
| Portfolio Manager | `manager` | `manager123` |
| Risk Analyst | `analyst` | `analyst123` |

---

## Tech Stack

**Frontend**
- Next.js 16 (App Router) · React 19 · TypeScript 5
- Tailwind CSS v4 · shadcn/ui · Recharts v3 · Lucide React

**Backend**
- Node.js · Express 5 · JWT (HS256, 8h) · KafkaJS
- Server-Sent Events (SSE) for real-time streaming

**AI / LLM**
- NVIDIA DeepSeek V4 Pro via `integrate.api.nvidia.com/v1`
- LangGraph (agentic orchestration — COMPASS layer)

**ML / Data Science**
- Python 3.11 · FastAPI · PyTorch 2.2 · ONNX Runtime
- XGBoost 2.0 · scikit-learn · scikit-uplift
- GraphSAGE (PyTorch Geometric) · DeepHit survival modelling
- SHAP (explainability) · Pandas · NumPy

**Infrastructure**
- Apache Kafka (real-time event streaming; simulation fallback if broker absent)
- Docker Compose (local Postgres + Kafka + MLflow stack)
- MLflow (experiment tracking + model registry)

---

## How to Run Locally

### Prerequisites
- Node.js ≥ 20
- Python 3.11+ with Poetry (`pip install poetry`) — only for ML layer
- Docker Desktop — only for full Kafka stack

---

### Step 1 — Start the API server (port 8000)

```bash
cd server
npm install
```

Create `server/.env`:

```env
PORT=8000
JWT_SECRET=pcop-hackathon-2026-secret

# NVIDIA DeepSeek V4 Pro (for HERALD outreach generation)
NVIDIA_ENDPOINT=https://integrate.api.nvidia.com/v1/chat/completions
NVIDIA_API_KEY=<your-nvidia-api-key>
NVIDIA_MODEL=deepseek-ai/deepseek-v4-pro

# Kafka (optional — simulation fallback fires automatically if absent)
KAFKA_BROKERS=localhost:9092
KAFKA_CLIENT_ID=pcop-server
KAFKA_GROUP_ID=pcop-consumers
```

```bash
node index.js
```

The server starts with an in-memory data store and Kafka simulation mode — **no additional services required for a working demo**.

---

### Step 2 — Start the frontend (port 3000)

```bash
cd client
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and log in with `admin / admin123`.

---

### Step 3 (optional) — Start the bank data server (port 3001)

```bash
cd bank
npm install
cp .env.example .env
npm run dev
```

---

### Step 4 (optional) — Run the ML scoring service (port 8001)

```bash
cd chronos
poetry install
cp .env.example .env
poetry run uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

Pre-computed score snapshots in `chronos/data/` are used by default — the FastAPI service is only needed for live re-scoring.

---

### Step 5 (optional) — Train models from scratch

```bash
cd chronos
poetry run python ml/datasets/download_public_datasets.py
poetry run python -m ml.generators.synthetic_sequences_from_bankchurners
poetry run python ml/training/genesis_train.py
poetry run python -m ml.training.tare_pretrain --epochs 10
poetry run python -m ml.training.tare_finetune \
  --pretrain-checkpoint ml/checkpoints/tare_pretrain_final.pt
poetry run python -m ml.training.export_onnx \
  --checkpoint ml/checkpoints/tare_finetune_final.pt \
  --output ml/checkpoints/tare_churn.onnx
poetry run python ml/training/habitat_train.py
poetry run python ml/register_all_models.py
```

---

## The Seven Layers

PCOP processes every customer through a sequential intelligence pipeline:

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │  Layer 1 · DATA INGESTION                                           │
 │  bank/  →  CBS snapshots, transactions, CRM logs for 20 customers   │
 └───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │  Layer 2 · ARGUS · Signal Detection                                 │
 │  argus/  →  CUSUM, BOCPD, SPRT, SA-EWMA, BH-FDR              │
 │  Fires risk signals to Kafka topic: risk.signal_detections          │
 └───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │  Layer 3 · CHRONOS · Precision Risk Engine                          │
 │  chronos/  →  5-model ensemble (TARE + HABITAT + GraphSAGE +        │
 │               DeepHit + GENESIS) fused via FusionXV2                │
 │  Output: churn score 0–1, survival curve, urgency horizon           │
 └───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │  Layer 4 · COMPASS · Action Intelligence                            │
 │  compass/  →  LangGraph 7-node agent           │
 │  Output: next-best-offer, channel, timing, rationale                │
 └───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │  Layer 5 · HERALD · Outreach Engine                                 │
 │  herald/  →  NVIDIA DeepSeek V4 Pro       │
 │  Output: personalised email, SMS, push notification                 │
 └───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │  Layer 6 · VERDICT · Measurement                                    │
 │  verdict/  →  Doubly Robust causal uplift         │
 │  Output: incremental uplift E[Y(1)−Y(0)|X], campaign ROI            │
 └───────────────────────────────┬─────────────────────────────────────┘
                                 ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │  Layer 7 · ORACLE · Analytics & Retraining                          │
 │  oracle/  →  Portfolio insights + weight           │
 │                                recalibration via VERDICT feedback   │
 └─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
pcop/
│
├── README.md                           ← This file
├── docker-compose.yml                  ← Postgres + Kafka + MLflow stack
│
├── bank/                               ← Layer 1: Demo CBS data server (port 3001)
│   └── src/
│
├── argus/                              ← Layer 2: ARGUS detection engine (advanced)
├── argus_v1/                           ← Layer 2: ARGUS base implementation
│
├── chronos/                            ← Layer 3: Precision Risk Engine
│   ├── api/                            ← FastAPI scoring service (port 8001)
│   ├── ml/
│   │   ├── checkpoints/                ← Trained model artifacts (committed)
│   │   ├── training/                   ← TARE, HABITAT, GraphSAGE, DeepHit scripts
│   │   └── generators/                 ← Synthetic data generation
│   ├── services/scoring/               ← Inference + FusionXV2 ensemble
│   └── data/                           ← Pre-computed JSON outputs (scores, plans, content)
│
├── compass/       ← Layer 4: LangGraph action planning
├── herald/   ← Layer 5: NVIDIA DeepSeek outreach
├── verdict/         ← Layer 6: DR-Learner uplift measurement
├── oracle/            ← Layer 7: Portfolio analytics + retraining
│
├── server/                             ← Express API gateway (port 8000)
│   ├── index.js
│   ├── middleware/auth.js
│   ├── routes/
│   └── services/
│       ├── kafkaService.js             ← Kafka consumer + 8s simulation fallback
│       ├── dataStore.js                ← In-memory customer + signal store
│       └── analysisService.js          ← NVIDIA DeepSeek integration
│
└── client/                             ← Next.js 16 frontend (port 3000)
    └── src/
        ├── app/
        │   ├── dashboard/              ← Portfolio overview + live Kafka feed
        │   ├── customers/[id]/         ← Full customer risk profile + AI outreach
        │   ├── analytics/              ← Statistical dashboards + model attribution
        │   ├── signals/                ← ARGUS alarm feed + coverage matrix
        │   ├── outreach/               ← Campaign hub
        │   └── pipeline/               ← Kafka stream inspector
        ├── components/
        │   ├── dashboard/              ← KnowledgeGraphCard, KafkaFeed, ChronosCards
        │   └── detail/                 ← SurvivalPanel, CompassPanel, OutreachPanel
        ├── hooks/                      ← usePortfolio, useCustomerDetail, useAuth
        └── lib/api.ts                  ← Typed API client (40+ endpoints)
```

---

## Dataset

All data is **100% synthetic** — no real customer PII was used at any stage.

**Demo dataset (`server/data/` and `chronos/data/`):**
- 20 synthetic retail banking customers
- Fields: account balance, transaction history, NPS score, product holdings, life events, digital engagement score, segment, tenure
- 8 static JSON files (~314 KB total) served by the Express gateway
- Kafka simulation generates realistic live banking events every 8 seconds

**ML training datasets (public):**

| Dataset | Source | Used for |
|---------|--------|----------|
| Bank Customer Churn | Kaggle (10K rows) | HABITAT XGBoost training + GENESIS LR |
| UCI Bank Marketing | UCI ML Repository (45K rows) | GENESIS cold-start features |
| MBD-mini | HuggingFace (~50K rows) | TARE encoder pre-training |
| Synthetic action sequences | Generated from BankChurners (10K rows) | TARE fine-tuning |
| Synthetic survival records | Generated (20K rows) | DeepHit training |
| Customer–Product k-NN graph | Constructed from above (10,127 nodes) | GraphSAGE training |

---

## Model Performance (on Synthetic Test Set)

| Model | Role | Key Metric | Value |
|-------|------|------------|-------|
| **GraphSAGE** · Network Risk Intelligence | 20% weight | AUC | **0.93** |
| **HABITAT** · XGBoost Tabular Scorer | 30% weight | AUC | **0.88** |
| **DeepHit** · Survival Analytics | 15% weight | Brier score | **< 0.25** |
| **TARE** · Temporal Sequence Encoder (GRU) | 35% weight | Val loss | **0.0956** |
| **GENESIS** · Cold-Start LR | Fallback | CV AUC | **0.65+** |
| **FusionXV2** · Conformal Ensemble | Final output | ECE | **0.032** |

**ARGUS Signal Detection (Layer 2):**

| Detector | Method | Sensitivity |
|----------|--------|-------------|
| Drift Monitor | CUSUM | Detects 0.5σ sustained shifts over 7 days |
| Behavioural Shift | BOCPD (Bayesian) | Online, no window assumption |
| Sequential Alerter | SPRT | α = 0.01, β = 0.05 |
| Multi-Signal FDR | BH procedure | Controls false discovery at q = 0.05 across 18 signals |

---

## API Reference (Summary)

All routes except `/auth/*` require `Authorization: Bearer <JWT>`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Get JWT token |
| GET | `/api/portfolio/stats` | Aggregate KPIs |
| GET | `/api/portfolio/top-at-risk` | Top customers by churn score |
| GET | `/api/customers` | All 20 customers (filterable) |
| GET | `/api/customers/:id/snapshot` | Full customer profile |
| GET | `/api/customers/:id/signals` | Active ARGUS signals |
| POST | `/api/analysis/analyze` | Trigger AI risk analysis |
| POST | `/api/outreach/generate` | Generate HERALD outreach content |
| GET | `/api/v2/scores` | Ensemble scores + survival horizons |
| GET | `/api/v2/action-plans` | COMPASS action plans |
| GET | `/api/v2/model-health` | Model health + ensemble config |
| GET | `/api/kafka/stream` | SSE live event stream |

---

## Port Map

| Service | Port | Command |
|---------|------|---------|
| Frontend (Next.js) | 3000 | `npm run dev` in `client/` |
| Express API gateway | 8000 | `node index.js` in `server/` |
| Bank data server | 3001 | `npm run dev` in `bank/` |
| CHRONOS FastAPI | 8001 | `uvicorn api.main:app` in `chronos/` |
| PostgreSQL | 5432 | Docker Compose |
| Kafka | 9092 | Docker Compose |
| MLflow UI | 5000 | Docker Compose |

---

## Authors

| Name | Role |
|------|------|
| **Atrijo Pal** | COMPASS (LangGraph orchestration), HERALD (AI outreach), VERDICT (causal measurement), ORACLE (analytics & retraining) |
| *(collaborator)* | *(to be updated)* |

**Contact:** covalentradius80@gmail.com

---

## NextGenHacks 2026 Submission
