"""TARE (Temporal Action Recurrence Encoder) — GRU + attention sequence model."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

VOCAB_SIZE = 50
EMBED_DIM = 128
GRU_HIDDEN = 128
GRU_LAYERS = 2
GRU_DROPOUT = 0.2
DENSE_HIDDEN = 64
CLASSIFIER_DROPOUT = 0.3


class TimeGapEncoding(nn.Module):
    """Encode inter-event time gaps as learnable log-compressed positional bias."""

    def __init__(self, embed_dim: int = EMBED_DIM) -> None:
        super().__init__()
        self.W_t = nn.Linear(1, embed_dim, bias=True)

    def forward(self, time_gaps: torch.Tensor) -> torch.Tensor:
        """Args:
            time_gaps: (batch, seq_len) float tensor of days between events.
        Returns:
            (batch, seq_len, embed_dim) positional bias.
        """
        log_gaps = torch.log1p(time_gaps).unsqueeze(-1)  # (B, L, 1)
        return self.W_t(log_gaps)  # (B, L, embed_dim)


class BahdanauAttention(nn.Module):
    """Additive (Bahdanau) single-head attention over GRU hidden states."""

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.query = nn.Linear(hidden_dim * 2, hidden_dim, bias=False)
        self.key = nn.Linear(hidden_dim * 2, hidden_dim, bias=False)
        self.v = nn.Linear(hidden_dim, 1, bias=False)

    def forward(
        self, hidden: torch.Tensor, mask: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Compute context vector and attention weights.

        Args:
            hidden: (batch, seq_len, hidden_dim*2) BiGRU output.
            mask: (batch, seq_len) boolean; True = PAD position to ignore.

        Returns:
            context: (batch, hidden_dim*2)
            weights: (batch, seq_len) normalised attention scores.
        """
        scores = self.v(torch.tanh(self.query(hidden) + self.key(hidden)))  # (B, L, 1)
        scores = scores.squeeze(-1)  # (B, L)

        if mask is not None:
            scores = scores.masked_fill(mask, float("-inf"))

        weights = torch.softmax(scores, dim=-1)  # (B, L)
        context = torch.bmm(weights.unsqueeze(1), hidden).squeeze(1)  # (B, H*2)
        return context, weights


class TAREEncoder(nn.Module):
    """Full TARE model: embedding → time encoding → BiGRU → attention → classifier."""

    def __init__(
        self,
        vocab_size: int = VOCAB_SIZE,
        embed_dim: int = EMBED_DIM,
        gru_hidden: int = GRU_HIDDEN,
        gru_layers: int = GRU_LAYERS,
        gru_dropout: float = GRU_DROPOUT,
        dense_hidden: int = DENSE_HIDDEN,
        classifier_dropout: float = CLASSIFIER_DROPOUT,
        pad_idx: int = 0,
    ) -> None:
        super().__init__()
        self.pad_idx = pad_idx
        self.gru_hidden = gru_hidden

        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=pad_idx)
        self.time_encoding = TimeGapEncoding(embed_dim)
        self.gru = nn.GRU(
            embed_dim,
            gru_hidden,
            num_layers=gru_layers,
            batch_first=True,
            bidirectional=True,
            dropout=gru_dropout if gru_layers > 1 else 0.0,
        )
        self.attention = BahdanauAttention(gru_hidden)
        context_dim = gru_hidden * 2

        self.classifier = nn.Sequential(
            nn.Linear(context_dim, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(classifier_dropout),
            nn.Linear(256, dense_hidden),
            nn.LayerNorm(dense_hidden),
            nn.ReLU(),
            nn.Dropout(classifier_dropout),
            nn.Linear(dense_hidden, 1),
            nn.Sigmoid(),
        )

    def forward(
        self, token_ids: torch.Tensor, time_gaps: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Forward pass.

        Args:
            token_ids: (batch, seq_len) int64 token indices.
            time_gaps: (batch, seq_len) float32 inter-event gaps in days.

        Returns:
            churn_prob: (batch,) predicted churn probability.
            attention_weights: (batch, seq_len) attention distribution.
        """
        pad_mask = token_ids.eq(self.pad_idx)  # (B, L)

        embed = self.embedding(token_ids)  # (B, L, E)
        time_bias = self.time_encoding(time_gaps)  # (B, L, E)
        x = embed + time_bias  # (B, L, E)

        gru_out, _ = self.gru(x)  # (B, L, H*2)
        context, attn_weights = self.attention(gru_out, mask=pad_mask)  # (B, H*2), (B, L)

        churn_prob = self.classifier(context).squeeze(-1)  # (B,)
        return churn_prob, attn_weights

    def get_context_vector(
        self, token_ids: torch.Tensor, time_gaps: torch.Tensor
    ) -> torch.Tensor:
        """Return the 256-dim context vector (for CAUSAL-NET backbone).

        Args:
            token_ids: (batch, seq_len)
            time_gaps: (batch, seq_len)

        Returns:
            context: (batch, gru_hidden * 2)
        """
        pad_mask = token_ids.eq(self.pad_idx)
        embed = self.embedding(token_ids) + self.time_encoding(time_gaps)
        gru_out, _ = self.gru(embed)
        context, _ = self.attention(gru_out, mask=pad_mask)
        return context

    def parameter_count(self) -> int:
        """Return total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    @classmethod
    def from_pretrained(cls, checkpoint_path: str | Path, **kwargs: Any) -> "TAREEncoder":
        """Load model weights from a checkpoint file.

        Args:
            checkpoint_path: Path to .pt checkpoint produced by training scripts.

        Returns:
            Instantiated TAREEncoder with loaded weights.
        """
        ckpt = torch.load(checkpoint_path, map_location="cpu")
        model_kwargs = {**kwargs}
        if "model_config" in ckpt:
            model_kwargs = {**ckpt["model_config"], **model_kwargs}

        model = cls(**model_kwargs)

        state_dict = ckpt["model_state_dict"]
        # Handle pretraining checkpoints with extra MASK embedding
        if "embedding.weight" in state_dict:
            ckpt_embed = state_dict["embedding.weight"]
            model_embed = model.embedding.weight

            if ckpt_embed.shape[0] != model_embed.shape[0]:
                logger.warning(
                    "Adjusting embedding size from %d -> %d",
                    ckpt_embed.shape[0],
                    model_embed.shape[0],
                )

                state_dict["embedding.weight"] = ckpt_embed[
                    : model_embed.shape[0]
                ]

        model.load_state_dict(state_dict)
        logger.info(
            "Loaded TARE checkpoint from %s (params=%d)", checkpoint_path, model.parameter_count()
        )
        return model


class TAREPretrainHead(nn.Module):
    """Masked action prediction head for TARE self-supervised pre-training."""

    def __init__(self, hidden_dim: int = GRU_HIDDEN * 2, vocab_size: int = VOCAB_SIZE) -> None:
        super().__init__()
        self.proj = nn.Linear(hidden_dim, vocab_size)

    def forward(self, gru_out: torch.Tensor) -> torch.Tensor:
        """Predict masked token at each position.

        Args:
            gru_out: (batch, seq_len, hidden_dim*2) BiGRU output.

        Returns:
            logits: (batch, seq_len, vocab_size)
        """
        return self.proj(gru_out)
