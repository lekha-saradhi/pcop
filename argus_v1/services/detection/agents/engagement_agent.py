"""
Digital Engagement Agent.

Consumes:    pcop.app_events.v1
Method:      EWMA (lambda = 0.3, L = 3) on a daily engagement score
             computed as logins * weight_login + sessions weighted by duration.

This agent maintains a SHORT in-memory buffer for the *current day*; when
the day rolls over, the day's aggregated score is fed to EWMA. The first
two months of EWMA values widen the control limits dynamically.
"""
import math
from datetime import datetime
from typing import Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import CanonicalEvent, SignalResult
from ..methods.ewma import Ewma, EwmaState


class EngagementAgent(BaseAgent):
    signal_type = "engagement"
    method_used = "ewma"

    LOGIN_WEIGHT = 0.5
    DURATION_FULL_SECONDS = 600  # 10 min session = score 1.0 contribution

    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        if event.event_type != "app_event":
            return None

        payload = event.payload
        evtype = payload.get("event_type")
        customer_id = event.customer_id
        ts = event.event_timestamp
        day_key = ts.date().isoformat()

        baseline = self.baselines.get(customer_id, "engagement_score")
        if baseline is None:
            return None

        state_dict = self.state_store.get("ewma", customer_id, "engagement") or {}
        current_day = state_dict.get("current_day")
        day_logins = state_dict.get("day_logins", 0)
        day_session_score = state_dict.get("day_session_score", 0.0)
        z_prev = state_dict.get("z_prev", baseline.mu_0)
        t = state_dict.get("t", 0)
        recent_sessions = state_dict.get("recent_session_durations_s", [])

        # If day rolled, flush previous day into EWMA
        result_to_emit: Optional[SignalResult] = None
        if current_day and current_day != day_key:
            score = self._daily_score(day_logins, day_session_score)
            ewma = Ewma(mu_0=baseline.mu_0, sigma=baseline.sigma, lam=0.3, L=3.0)
            estate = EwmaState(z_prev=z_prev, t=t)
            eres = ewma.update(score, estate)
            z_prev, t = eres.z_t, t + 1

            if eres.alarm:
                direction_word = "above" if eres.direction == "up" else "below"
                evidence = [
                    f"EWMA Z_t = {eres.z_t:.2f} {direction_word} "
                    f"{'UCL' if eres.direction == 'up' else 'LCL'} = "
                    f"{(eres.UCL if eres.direction == 'up' else eres.LCL):.2f}",
                    f"Sessions trend (last 3 days, sec): {recent_sessions[-3:]}",
                ]
                raw = {
                    "baseline_mu": baseline.mu_0,
                    "baseline_sigma": baseline.sigma,
                    "lambda": 0.3, "L": 3.0,
                    "Z_t": round(eres.z_t, 4),
                    "UCL": round(eres.UCL, 4),
                    "LCL": round(eres.LCL, 4),
                    "recent_session_durations_s": recent_sessions[-5:],
                    "daily_score": round(score, 4),
                }
                result_to_emit = self._make_result(
                    customer_id=customer_id, detected=True, confidence=eres.confidence,
                    evidence=evidence, raw_data=raw,
                    evaluated_at=ts,
                )

            # Reset day buckets
            day_logins, day_session_score = 0, 0.0

        # Update current-day buckets from this event
        current_day = day_key
        if evtype == "login":
            day_logins += 1
        dur = payload.get("session_duration_s") or 0
        if dur:
            day_session_score += min(dur, self.DURATION_FULL_SECONDS) / self.DURATION_FULL_SECONDS
            recent_sessions = (recent_sessions + [int(dur)])[-10:]

        # Persist
        self.state_store.set("ewma", customer_id, "engagement", {
            "current_day": current_day,
            "day_logins": day_logins,
            "day_session_score": day_session_score,
            "z_prev": z_prev,
            "t": t,
            "recent_session_durations_s": recent_sessions,
            "last_update": ts.isoformat(),
        })
        return result_to_emit

    @staticmethod
    def _daily_score(logins: int, session_score: float) -> float:
        """Bounded daily engagement metric in [0, ~1.5]."""
        return min(0.5 * min(logins, 4) / 4.0 + session_score, 1.5)
