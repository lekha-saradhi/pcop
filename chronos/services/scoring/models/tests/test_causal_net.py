"""Unit tests for CAUSAL-NET two-tower uplift model."""

import torch
import pytest

from services.scoring.models.causal_net import (
    CausalNet,
    TreatabilityHead,
    ActionTier,
    DEFAULT_TREATABILITY,
    _action_tier,
)

SEQ_LEN = 180
BATCH = 2
TABULAR_DIM = 14


@pytest.fixture()
def model() -> CausalNet:
    return CausalNet(tare_checkpoint=None)


def test_output_shapes(model: CausalNet) -> None:
    ids = torch.zeros(BATCH, SEQ_LEN, dtype=torch.long)
    gaps = torch.zeros(BATCH, SEQ_LEN, dtype=torch.float32)
    tabular = torch.zeros(BATCH, TABULAR_DIM, dtype=torch.float32)
    treatment = torch.zeros(BATCH, 1, dtype=torch.float32)

    p_churn, p_treatable, action_score = model(ids, gaps, tabular, treatment)
    assert p_churn.shape == (BATCH,)
    assert p_treatable.shape == (BATCH,)
    assert action_score.shape == (BATCH,)


def test_probabilities_in_range(model: CausalNet) -> None:
    ids = torch.randint(1, 50, (BATCH, SEQ_LEN))
    gaps = torch.zeros(BATCH, SEQ_LEN)
    tabular = torch.rand(BATCH, TABULAR_DIM)
    treatment = torch.zeros(BATCH, 1)

    p_churn, p_treatable, action_score = model(ids, gaps, tabular, treatment)
    assert (p_churn >= 0).all() and (p_churn <= 1).all()
    assert (p_treatable >= 0).all() and (p_treatable <= 1).all()
    assert (action_score >= 0).all() and (action_score <= 1).all()


def test_default_treatability(model: CausalNet) -> None:
    ids = torch.zeros(BATCH, SEQ_LEN, dtype=torch.long)
    gaps = torch.zeros(BATCH, SEQ_LEN)
    tabular = torch.zeros(BATCH, TABULAR_DIM)
    treatment = torch.zeros(BATCH, 1)

    _, p_treatable, _ = model(ids, gaps, tabular, treatment)
    for pt in p_treatable:
        assert abs(float(pt) - DEFAULT_TREATABILITY) < 1e-5


def test_action_score_equals_product(model: CausalNet) -> None:
    ids = torch.zeros(BATCH, SEQ_LEN, dtype=torch.long)
    gaps = torch.zeros(BATCH, SEQ_LEN)
    tabular = torch.zeros(BATCH, TABULAR_DIM)
    treatment = torch.zeros(BATCH, 1)

    p_churn, p_treatable, action_score = model(ids, gaps, tabular, treatment)
    expected = p_churn * p_treatable
    assert torch.allclose(action_score, expected, atol=1e-6)


def test_tare_weights_frozen(model: CausalNet) -> None:
    for param in model.tare.parameters():
        assert not param.requires_grad


def test_treatability_head_trainable(model: CausalNet) -> None:
    trainable = any(p.requires_grad for p in model.treatability_head.parameters())
    assert trainable


def test_action_tier_priority() -> None:
    assert _action_tier(0.85, 0.65) == ActionTier.PRIORITY


def test_action_tier_none() -> None:
    assert _action_tier(0.1, 0.1) == ActionTier.NONE


def test_treatability_head_shape() -> None:
    head = TreatabilityHead(context_dim=256, tabular_dim=TABULAR_DIM)
    ctx = torch.randn(BATCH, 256)
    tab = torch.randn(BATCH, TABULAR_DIM)
    flag = torch.zeros(BATCH, 1)
    out = head(ctx, tab, flag)
    assert out.shape == (BATCH,)
    assert (out >= 0).all() and (out <= 1).all()
