"""
Complaint Sentiment Agent.

Consumes:    pcop.crm_notes.v1   (complaints, enquiries, feedback)
Method:      CUSUM (two-sided) on the LLM-derived sentiment_score field.

Pre-filter:  Only complaints and notes whose text contains a churn-intent
             keyword bypass the cool-down; everything else just updates
             the running CUSUM stats.

Extra evidence: detected competitor mentions, unresolved-issue counts.
"""
import re
from typing import Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import CanonicalEvent, SignalResult
from ..methods.cusum import Cusum, CusumState

CHURN_INTENT_PATTERNS = [
    r"\bswitching to\b",
    r"\bmoving to\b",
    r"\bclose\b\s+(my|the)\b\s+account\b",
    r"\bclose\s+account\b",
    r"\bcancel\s+my\s+account\b",
    r"\btransfer\s+my\s+account\b",
    r"\bbetter\s+offer\b",
    r"\bconsidering\s+(switching|moving|leaving)\b",
]
COMPETITOR_PATTERNS = [
    r"\bHDFC\b", r"\bICICI\b", r"\bKotak(?:\s+Mahindra)?\b",
    r"\bAxis\b", r"\bSBI\b", r"\bYes\s+Bank\b", r"\bIDFC\b",
]


class ComplaintSentimentAgent(BaseAgent):
    signal_type = "complaint_sentiment"
    method_used = "cusum"

    def __init__(self, *args, history_size: int = 8, **kwargs):
        super().__init__(*args, **kwargs)
        self.history_size = history_size

    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        payload = event.payload
        # Only consider complaints / negative interactions
        note_type = payload.get("note_type")
        sentiment = payload.get("sentiment_score")
        if sentiment is None:
            return None

        customer_id = event.customer_id
        text = payload.get("note_text") or ""
        ts = event.event_timestamp

        baseline = self.baselines.get(customer_id, "complaint_sentiment")
        if baseline is None:
            return None

        # CUSUM with k = 0.5 sigma, H = 3.0 (per doc default for sentiment)
        cusum = Cusum(mu_0=baseline.mu_0, sigma=baseline.sigma,
                      k_sigma=0.5, H_sigma=3.0)
        state_dict = self.state_store.get("cusum", customer_id, "complaint_sentiment") or {}
        state = CusumState(s_plus=state_dict.get("s_plus", 0.0),
                           s_minus=state_dict.get("s_minus", 0.0))
        history = state_dict.get("history", [])
        history.append({
            "ts": ts.isoformat(),
            "score": float(sentiment),
            "note_type": note_type,
            "issue_category": payload.get("issue_category"),
            "resolved": payload.get("resolved", False),
        })
        history = history[-self.history_size:]

        cresult = cusum.update(float(sentiment), state)

        # --- text-pattern signals ---
        churn_intent = any(re.search(p, text, flags=re.IGNORECASE) for p in CHURN_INTENT_PATTERNS)
        competitor_hit = None
        for p in COMPETITOR_PATTERNS:
            m = re.search(p, text, flags=re.IGNORECASE)
            if m:
                competitor_hit = m.group(0)
                break

        unresolved = sum(1 for h in history
                         if h.get("note_type") == "complaint" and not h.get("resolved"))

        # Persist
        self.state_store.set("cusum", customer_id, "complaint_sentiment", {
            "s_plus": cresult.s_plus,
            "s_minus": cresult.s_minus,
            "history": history,
            "last_update": ts.isoformat(),
        })

        # Alarm conditions: CUSUM downside alarm OR explicit churn-intent in note
        detected = (cresult.alarm and cresult.direction == "down") or churn_intent
        if not detected:
            return None

        recent_scores = [h["score"] for h in history[-3:]]
        evidence: list[str] = []
        if cresult.alarm and cresult.direction == "down":
            evidence.append(
                f"Sentiment trending negative: {' -> '.join(f'{s:+.2f}' for s in recent_scores)} "
                f"over last {len(recent_scores)} interactions"
            )
        issue_cats = {h.get("issue_category") for h in history if h.get("issue_category")}
        if len(issue_cats) == 1 and unresolved >= 2:
            evidence.append(f"Same unresolved issue category: {next(iter(issue_cats))}")
        if churn_intent:
            evidence.append(f"Explicit churn-intent keyword detected in note: '{text[:120]}'")
        if competitor_hit:
            evidence.append(f"Competitor mentioned: {competitor_hit}")

        confidence = max(cresult.confidence, 0.65 if churn_intent else 0.0)
        if competitor_hit:
            confidence = min(1.0, confidence + 0.10)

        raw = {
            "sentiment_baseline": baseline.mu_0,
            "recent_scores": recent_scores,
            "issue_categories": list(issue_cats),
            "unresolved_count": unresolved,
            "churn_intent_keyword_hit": churn_intent,
            "competitor_mentioned": competitor_hit,
        }
        return self._make_result(
            customer_id=customer_id, detected=True, confidence=confidence,
            evidence=evidence, raw_data=raw,
            cusum_value=round(cresult.s_minus, 4),
            alarm_threshold=round(cresult.threshold, 4),
            evaluated_at=ts,
        )
