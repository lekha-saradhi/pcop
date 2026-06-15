"""Unit tests for TARE encoder model."""

import torch
import pytest

from services.scoring.models.tare_encoder import (
    TAREEncoder,
    TAREPretrainHead,
    TimeGapEncoding,
    BahdanauAttention,
    VOCAB_SIZE,
)

# Redefine for clarity
SEQ_LEN = 180
BATCH = 4


@pytest.fixture()
def model() -> TAREEncoder:
    return TAREEncoder()


def test_parameter_count(model: TAREEncoder) -> None:
    n = model.parameter_count()
    assert 500_000 < n < 2_000_000, f"Unexpected param count: {n}"


def test_output_shapes(model: TAREEncoder) -> None:
    ids = torch.randint(0, VOCAB_SIZE, (BATCH, SEQ_LEN))
    gaps = torch.rand(BATCH, SEQ_LEN) * 10
    probs, attn = model(ids, gaps)
    assert probs.shape == (BATCH,)
    assert attn.shape == (BATCH, SEQ_LEN)


def test_probs_in_range(model: TAREEncoder) -> None:
    ids = torch.randint(0, VOCAB_SIZE, (BATCH, SEQ_LEN))
    gaps = torch.zeros(BATCH, SEQ_LEN)
    probs, _ = model(ids, gaps)
    assert (probs >= 0).all() and (probs <= 1).all()


def test_attention_sums_to_one(model: TAREEncoder) -> None:
    ids = torch.randint(1, VOCAB_SIZE, (BATCH, SEQ_LEN))  # no PAD
    gaps = torch.zeros(BATCH, SEQ_LEN)
    _, attn = model(ids, gaps)
    sums = attn.sum(dim=-1)
    assert torch.allclose(sums, torch.ones(BATCH), atol=1e-5), f"Attention sums: {sums}"


def test_padded_attention(model: TAREEncoder) -> None:
    ids = torch.zeros(BATCH, SEQ_LEN, dtype=torch.long)
    ids[:, -10:] = torch.randint(1, VOCAB_SIZE, (BATCH, 10))
    gaps = torch.zeros(BATCH, SEQ_LEN)
    probs, attn = model(ids, gaps)
    assert probs.shape == (BATCH,)


def test_context_vector_shape(model: TAREEncoder) -> None:
    ids = torch.randint(1, VOCAB_SIZE, (2, SEQ_LEN))
    gaps = torch.zeros(2, SEQ_LEN)
    ctx = model.get_context_vector(ids, gaps)
    assert ctx.shape == (2, 256)  # gru_hidden * 2


def test_pretrain_head_shape() -> None:
    head = TAREPretrainHead()
    gru_out = torch.randn(BATCH, SEQ_LEN, 256)
    logits = head(gru_out)
    assert logits.shape == (BATCH, SEQ_LEN, VOCAB_SIZE)


def test_time_gap_encoding_shape() -> None:
    enc = TimeGapEncoding(embed_dim=128)
    gaps = torch.rand(BATCH, SEQ_LEN) * 30
    out = enc(gaps)
    assert out.shape == (BATCH, SEQ_LEN, 128)


def test_bahdanau_attention_shape() -> None:
    attn = BahdanauAttention(hidden_dim=128)
    hidden = torch.randn(BATCH, SEQ_LEN, 256)
    ctx, weights = attn(hidden)
    assert ctx.shape == (BATCH, 256)
    assert weights.shape == (BATCH, SEQ_LEN)


def test_no_gradient_flow_to_frozen_embedding(model: TAREEncoder) -> None:
    for param in model.embedding.parameters():
        param.requires_grad = False
    ids = torch.randint(1, VOCAB_SIZE, (2, SEQ_LEN))
    gaps = torch.zeros(2, SEQ_LEN)
    probs, _ = model(ids, gaps)
    probs.sum().backward()
    assert model.embedding.weight.grad is None
