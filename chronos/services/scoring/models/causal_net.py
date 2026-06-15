"""CAUSAL-NET — Two-tower uplift model for treatability scoring."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

DEFAULT_TREATABILITY = 0.5  # used before CAUSAL-NET is trained (pre-week-12)
TABULAR_DIM = 14  # number of Pass 1 tabular features


class ActionTier(Enum):
    PRIORITY = "priority"      # churn > 0.8, treatable > 0.6
    ESCALATE = "escalate"      # churn > 0.6, treatable > 0.5
    STANDARD = "standard"      # churn > 0.4, treatable > 0.4
    MONITOR = "monitor"        # churn > 0.2
    NONE = "none"              # low risk


def _action_tier(p_churn: float, p_treatable: float) -> ActionTier:
    if p_churn > 0.8 and p_treatable > 0.6:
        return ActionTier.PRIORITY
    if p_churn > 0.6 and p_treatable > 0.5:
        return ActionTier.ESCALATE
    if p_churn > 0.4 and p_treatable > 0.4:
        return ActionTier.STANDARD
    if p_churn > 0.2:
        return ActionTier.MONITOR
    return ActionTier.NONE


class TreatabilityHead(nn.Module):
    """Treatability prediction head using TARE context + tabular features + treatment flag."""

    def __init__(self, context_dim: int = 256, tabular_dim: int = TABULAR_DIM) -> None:
        super().__init__()
        input_dim = context_dim + tabular_dim + 1  # +1 for treatment_flag
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        context: torch.Tensor,
        tabular: torch.Tensor,
        treatment_flag: torch.Tensor,
    ) -> torch.Tensor:
        """Predict treatability probability.

        Args:
            context: (batch, 256) TARE context vector.
            tabular: (batch, tabular_dim) Pass 1 features.
            treatment_flag: (batch, 1) float indicator (1 = treated, 0 = control).

        Returns:
            (batch,) treatability probability.
        """
        x = torch.cat([context, tabular, treatment_flag], dim=-1)
        return self.net(x).squeeze(-1)


class CausalNet(nn.Module):
    """Two-tower uplift model sharing frozen TARE GRU backbone."""

    def __init__(
        self,
        tare_checkpoint: str | Path | None = None,
        tabular_dim: int = TABULAR_DIM,
        default_treatability: float = DEFAULT_TREATABILITY,
    ) -> None:
        super().__init__()
        from services.scoring.models.tare_encoder import TAREEncoder

        if tare_checkpoint is not None:
            self.tare = TAREEncoder.from_pretrained(tare_checkpoint)
        else:
            self.tare = TAREEncoder()

        # Freeze TARE backbone
        for param in self.tare.parameters():
            param.requires_grad = False

        self.treatability_head = TreatabilityHead(context_dim=self.tare.gru_hidden * 2, tabular_dim=tabular_dim)
        self.default_treatability = default_treatability
        self._use_default_treatability = tare_checkpoint is None

    def forward(
        self,
        token_ids: torch.Tensor,
        time_gaps: torch.Tensor,
        tabular_features: torch.Tensor,
        treatment_flag: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Compute churn prob, treatability prob, and action score.

        Args:
            token_ids: (batch, seq_len) int64.
            time_gaps: (batch, seq_len) float32.
            tabular_features: (batch, tabular_dim) float32 Pass 1 features.
            treatment_flag: (batch, 1) float32 (1=treated, 0=control).

        Returns:
            p_churn: (batch,) churn probability from TARE.
            p_treatable: (batch,) treatability probability.
            action_score: (batch,) = p_churn × p_treatable.
        """
        with torch.no_grad():
            p_churn, _ = self.tare(token_ids, time_gaps)
            context = self.tare.get_context_vector(token_ids, time_gaps)

        if self._use_default_treatability:
            p_treatable = torch.full_like(p_churn, self.default_treatability)
        else:
            p_treatable = self.treatability_head(context, tabular_features, treatment_flag)

        action_score = p_churn * p_treatable
        return p_churn, p_treatable, action_score

    def get_action_tier(self, p_churn: float, p_treatable: float) -> ActionTier:
        """Map probability pair to intervention tier."""
        return _action_tier(p_churn, p_treatable)
