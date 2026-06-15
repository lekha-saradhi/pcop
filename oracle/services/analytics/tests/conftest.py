import pytest
import pandas as pd
import numpy as np


def make_training_df(n=100, seed=42):
    rng = np.random.default_rng(seed)
    dr_uplifts = rng.uniform(-0.05, 0.15, n)
    return pd.DataFrame({
        "customer_id": [f"C-{i:08d}" for i in range(n)],
        "outcome_label": rng.choice(["retained", "partial", "churned"], n),
        "churn_label": rng.integers(0, 2, n),
        "dr_uplift": dr_uplifts,
        "sample_weight": np.clip(dr_uplifts / 0.15, 0.3, 1.0),
        "churn_score_at_measure": rng.uniform(0.2, 0.9, n),
        "treatability_score_at_send": rng.uniform(0.2, 0.9, n),
        "risk_tier": rng.choice(["high", "medium", "watch"], n),
        "channel": rng.choice(["email", "sms", "app"], n),
        "score_reduction": rng.uniform(-0.1, 0.4, n),
        "signals_cleared": rng.choice([True, False], n),
    })


def make_prompt_versions(channel="email"):
    return [
        {"version_id": "v1", "channel": channel, "bandit_alpha": 8.0, "bandit_beta": 4.0, "dr_uplift": 0.08, "new_observations_today": 15},
        {"version_id": "v2", "channel": channel, "bandit_alpha": 5.0, "bandit_beta": 6.0, "dr_uplift": 0.02, "new_observations_today": 10},
    ]


def make_ab_variant_pair(a_retained=45, a_total=80, b_retained=62, b_total=80):
    return [{"version_id": "v1", "a_retained": a_retained, "a_total": a_total, "b_retained": b_retained, "b_total": b_total}]
