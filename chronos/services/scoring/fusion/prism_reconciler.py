"""PRISM — Probabilistic Reason Integration & Signal Merging."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from ml.features.sequence_builder import VOCAB
from ml.features.tabular_features import PASS1_FEATURE_NAMES

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

TAXONOMY = [
    "transaction_decline",
    "engagement_drop",
    "complaint_escalation",
    "financial_stress",
    "income_change",
    "competitor_risk",
    "location_change",
    "product_disengagement",
    "inactivity",
]

# Token → taxonomy category mapping
TOKEN_TAXONOMY: dict[str, str] = {
    "DECLINE_INSUFFICIENT": "transaction_decline",
    "DECLINE_FRAUD": "transaction_decline",
    "DECLINE_OTHER": "transaction_decline",
    "COMPLAINT_RAISED": "complaint_escalation",
    "COMPLAINT_RESOLVED": "complaint_escalation",
    "SUPPORT_CONTACT": "complaint_escalation",
    "INACTIVITY_7D": "inactivity",
    "INACTIVITY_14D": "inactivity",
    "INACTIVITY_30D": "inactivity",
    "MOBILE_LOGIN": "engagement_drop",
    "WEB_LOGIN": "engagement_drop",
    "NOTIFICATION_OPEN": "engagement_drop",
    "OFFER_CLICK": "engagement_drop",
    "OFFER_REDEEM": "engagement_drop",
    "FOREX_BUY": "competitor_risk",
    "FOREX_SELL": "competitor_risk",
    "LOAN_OVERDUE": "financial_stress",
    "ATM_WITHDRAW": "financial_stress",
    "FD_CLOSE": "financial_stress",
    "ADDRESS_CHANGE": "location_change",
    "NOMINEE_UPDATE": "location_change",
    "CARD_BLOCK": "product_disengagement",
    "LIMIT_DECREASE": "product_disengagement",
    "ACCOUNT_CLOSURE_REQUEST": "product_disengagement",
    "SALARY_CREDIT": "income_change",
    "PROFILE_UPDATE": "income_change",
}

# HABITAT feature → taxonomy category mapping
FEATURE_TAXONOMY: dict[str, str] = {
    "decline_rate_30d": "transaction_decline",
    "complaint_open_count": "complaint_escalation",
    "support_contacts_90d": "complaint_escalation",
    "inactivity_streak_days": "inactivity",
    "recency_days": "inactivity",
    "frequency_30d": "engagement_drop",
    "frequency_90d": "engagement_drop",
    "digital_ratio": "engagement_drop",
    "channel_diversity": "engagement_drop",
    "avg_utilization": "financial_stress",
    "monetary_avg": "financial_stress",
    "monetary_total": "financial_stress",
    "product_count": "product_disengagement",
    "tenure_days": "engagement_drop",
    "life_event_income_change": "income_change",
    "life_event_address_change": "location_change",
    "life_event_employer_change": "income_change",
    "life_event_competitor_app": "competitor_risk",
    "life_event_large_withdrawal": "financial_stress",
    "life_event_fd_break": "financial_stress",
}

_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "transaction_decline": "Recent card or payment declines detected",
    "engagement_drop": "Declining digital activity and channel usage",
    "complaint_escalation": "Elevated support contacts or unresolved complaints",
    "financial_stress": "Signs of financial pressure — high utilisation or withdrawals",
    "income_change": "Potential income or employment change detected",
    "competitor_risk": "Signals suggesting competitor product consideration",
    "location_change": "Recent address or lifestyle change event",
    "product_disengagement": "Reduced product usage or cancellation signals",
    "inactivity": "Extended periods of account inactivity",
}


@dataclass
class ReasonCode:
    category: str
    description: str
    importance: float
    source: Literal["sequence", "tabular", "both"]


class PRISMReconciler:
    """Reconcile TARE attention codes and HABITAT SHAP codes into unified reason codes."""

    def reconcile(
        self,
        attention_token_ids: list[int],
        shap_codes: list[dict],
        fusion_weights: dict[str, float],
        top_k: int = 3,
    ) -> list[ReasonCode]:
        """Produce top-k unified reason codes from both model outputs.

        Args:
            attention_token_ids: Top attention token IDs from TARE (non-PAD).
            shap_codes: List of SHAP reason code dicts from HABITATScorer.shap_reason_codes().
            fusion_weights: Dict with 'tare' and 'habitat' weight floats.
            top_k: Number of reason codes to return.

        Returns:
            List of ReasonCode objects ordered by importance.
        """
        id_to_token = {v: k for k, v in VOCAB.items()}
        w_tare = fusion_weights.get("tare", 0.55)
        w_hab = fusion_weights.get("habitat", 0.45)

        category_scores: dict[str, dict] = {}

        # Accumulate TARE contributions
        for rank, token_id in enumerate(attention_token_ids):
            token_name = id_to_token.get(token_id, "UNK")
            category = TOKEN_TAXONOMY.get(token_name)
            if not category:
                continue
            importance = w_tare * (1.0 / (rank + 1))  # rank-weighted
            _accumulate(category_scores, category, importance, "sequence")

        # Accumulate HABITAT contributions
        for code in shap_codes:
            feature = code["feature"]
            category = FEATURE_TAXONOMY.get(feature)
            if not category:
                continue
            importance = w_hab * abs(code.get("shap_value", 0.0))
            _accumulate(category_scores, category, importance, "tabular")

        # Normalize and sort
        if not category_scores:
            return []

        max_imp = max(v["importance"] for v in category_scores.values())
        if max_imp == 0:
            return []

        for cat in category_scores:
            category_scores[cat]["importance"] /= max_imp

        sorted_cats = sorted(category_scores.items(), key=lambda x: x[1]["importance"], reverse=True)

        result = []
        for category, info in sorted_cats[:top_k]:
            result.append(ReasonCode(
                category=category,
                description=_CATEGORY_DESCRIPTIONS.get(category, category),
                importance=round(info["importance"], 4),
                source=info["source"],
            ))
        return result


def _accumulate(
    store: dict[str, dict],
    category: str,
    importance: float,
    source: Literal["sequence", "tabular"],
) -> None:
    if category not in store:
        store[category] = {"importance": 0.0, "source": source}
    else:
        existing = store[category]["source"]
        if existing != source:
            store[category]["source"] = "both"
    store[category]["importance"] += importance
