# PCOP — Layer 2 Detection Service

Complete implementation of the 9 statistical detection agents + BOCPD joint
detector that form Layer 2 of the Predictive Customer Outreach Platform.

## What's here

```
services/detection/
├── common/                          # Shared schemas, base agent, state store
│   ├── schemas.py                   # Pydantic: CanonicalEvent, SignalResult, AlarmMessage
│   ├── base_agent.py                # BaseAgent + sinks + baseline provider protocols
│   └── state_store.py               # Redis-backed + in-memory state for stream methods
│
├── methods/                         # Statistical method implementations
│   ├── cusum.py                     # Two-sided CUSUM control chart
│   ├── ewma.py                      # Exponentially weighted MA chart
│   ├── sprt.py                      # SPRT for Poisson counts
│   ├── page_hinkley.py              # Page-Hinkley test
│   ├── bocpd.py                     # Bayesian online changepoint (NIG conjugate)
│   └── stl_cusum.py                 # STL decomposition + CUSUM on residuals
│
├── agents/                          # 9 detection agents
│   ├── salary_agent.py              # CUSUM on amount + ref-change rule
│   ├── location_agent.py            # SQL rule on city frequency
│   ├── complaint_sentiment_agent.py # CUSUM on sentiment + intent regex
│   ├── complaint_volume_agent.py    # SPRT on monthly counts
│   ├── engagement_agent.py          # EWMA on daily engagement score
│   ├── transaction_drift_agent.py   # STL + CUSUM on daily txn counts
│   ├── stress_agent.py              # CUSUM on overdraft rate + MCC rule
│   ├── lifecycle_agent.py           # MCC + account-event whitelist
│   └── feature_usage_agent.py       # Page-Hinkley on feature counts
│
├── joint_detector/
│   └── bocpd_joint.py               # BOCPD across multiple co-active signals
│
├── db/
│   └── signal_repository.py         # PG writer + Kafka publisher + Redis pub/sub
│
├── tests/
│   └── test_methods.py              # 11 unit tests on the statistical methods
│
├── demo.py                          # End-to-end smoke test against dummy events
└── main.py                          # Service entrypoint (Kafka consumer loop)
```

## Quick start (no infra needed)

```bash
pip install pydantic numpy
# Optional: pip install pandas statsmodels   # for STL+CUSUM
cd pcop
PYTHONPATH=. python -m services.detection.demo
```

This runs every agent against the dummy event stream for customer
`C-00000001` (Arjun Sharma) and prints the SignalResults each agent emits.

Expected output: 6 distinct alarms — `salary`, `location`,
`complaint_sentiment`, `engagement`, `complaint_volume`, `bocpd_joint`.

## Unit tests

```bash
PYTHONPATH=. python -m unittest services.detection.tests.test_methods
```

All 11 tests pass.

## Production wiring

`main.py` shows the production wiring. Required services:

- **PostgreSQL 16** with the `signal_results` table from doc §4.3.1
- **Kafka** with the 10 input topics from doc §2.2.3
- **Redis** for per-customer streaming state

```bash
export DATABASE_URL=postgresql://...
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export REDIS_URL=redis://localhost:6379/0
export ANTHROPIC_API_KEY=sk-ant-...
pip install kafka-python psycopg2-binary redis
python -m services.detection.main
```

## Architecture

Each agent is a Kafka consumer that:

1. Reads `CanonicalEvent` from a Kafka topic (per `TOPIC_TO_AGENT_TYPES`)
2. Loads per-customer state from Redis (`StateStore`)
3. Loads baselines from the `customer_baselines` PG table (`BaselineProvider`)
4. Runs its statistical method (CUSUM / EWMA / SPRT / Page-Hinkley / SQL rule)
5. Persists updated state back to Redis
6. If an alarm fires, emits a `SignalResult` via `CompositeSink`:
   - Inserts row into `signal_results` PG table
   - Publishes alarm to `pcop.alarms.v1` Kafka topic
   - Pushes to `pcop:alarms` Redis pub/sub for dashboard live feed

Layers 3 and 4 (ML scoring + LangGraph orchestration) consume from
`signal_results` and the Kafka topic.

## Outputs

Per the spec, every alarm produces:

- **One PG row** in `signal_results` (durable history)
- **One Kafka message** on `pcop.alarms.v1` (live downstream)
- **One Redis pub/sub message** on `pcop:alarms` (dashboard)

See `demo.py` output for end-to-end examples.
