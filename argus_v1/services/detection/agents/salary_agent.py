"""
Salary Agent.

Consumes:    pcop.salary_credits.v1  (one event per monthly salary credit)
Method:      CUSUM (two-sided, relative units) on amount  + SQL rule on payment_ref
Confidence:  union of (CUSUM ratio, ref-change boost)

Detects:
  * Income increase / decrease / employer switch.
"""
from datetime import datetime
from typing import Optional

from ..common.base_agent import BaseAgent
from ..common.schemas import CanonicalEvent, SignalResult
from ..methods.cusum import Cusum, CusumState


class SalaryAgent(BaseAgent):
    signal_type = "salary"
    method_used = "cusum"

    # Track the last N employer refs to detect changes
    REF_HISTORY = 6

    def process_event(self, event: CanonicalEvent) -> Optional[SignalResult]:
        if event.payload.get("category") != "salary_credit":
            return None

        customer_id = event.customer_id
        amount = float(event.payload["amount"])
        payment_ref = (event.payload.get("payment_ref") or "").strip().upper()
        txn_date = event.payload.get("txn_date")

        baseline = self.baselines.get(customer_id, "salary_amount")
        if baseline is None:
            return None

        # --- CUSUM on amount, in relative units (Doc spec: k = 0.10, H = 0.30) ---
        relative_x = (amount - baseline.mu_0) / max(baseline.mu_0, 1.0)
        cusum = Cusum(mu_0=0.0, sigma=1.0, k_sigma=0.10, H_sigma=0.30)

        state_dict = self.state_store.get("cusum", customer_id, "salary") or {}
        state = CusumState(
            s_plus=state_dict.get("s_plus", 0.0),
            s_minus=state_dict.get("s_minus", 0.0),
        )
        ref_history = state_dict.get("ref_history", [])
        cresult = cusum.update(relative_x, state)

        # --- Employer reference change ---
        ref_changed = False
        prior_ref = next((r for r in reversed(ref_history) if r), "")
        if payment_ref and prior_ref and payment_ref != prior_ref:
            ref_changed = True
        ref_history.append(payment_ref)
        ref_history = ref_history[-self.REF_HISTORY:]

        # --- Compute detected (cooldown check follows) ---
        last_alarm_ref = state_dict.get("last_alarm_ref")

        # --- Build evidence ---
        evidence: list[str] = []
        pct = relative_x * 100.0
        if cresult.alarm:
            direction = "increased" if cresult.direction == "up" else "decreased"
            evidence.append(
                f"Salary amount {direction} {abs(pct):+.1f}% vs 6-month baseline "
                f"({baseline.mu_0:.0f} -> {amount:.0f})"
            )
        if ref_changed:
            evidence.append(
                f"Salary credit ref changed: {prior_ref} -> {payment_ref} ({txn_date})"
            )
            same_count = sum(1 for r in ref_history if r == payment_ref)
            if same_count >= 2:
                evidence.append(
                    f"New employer reference stable across {same_count} consecutive months"
                )

        detected = cresult.alarm or ref_changed

        # Always persist updated state so CUSUM and ref_history survive across events.
        self.state_store.set("cusum", customer_id, "salary", {
            "s_plus": cresult.s_plus,
            "s_minus": cresult.s_minus,
            "ref_history": ref_history,
            "last_amount": amount,
            "last_alarm_ref": payment_ref if detected else last_alarm_ref,
            "last_update": event.event_timestamp.isoformat(),
        })

        # Cooldown: once we've alarmed on employer=X, suppress further
        # alarms for X unless a fresh ref change occurs.
        if detected and last_alarm_ref == payment_ref and not ref_changed:
            return None

        # Confidence: combine CUSUM ratio + ref-change bump (capped at 1)
        conf = cresult.confidence
        if ref_changed:
            conf = min(1.0, max(conf, 0.55) + 0.20)

        if not detected and not self.publish_only_alarms:
            # Still emit a "no detection" probe so downstream can see the score history.
            return self._make_result(
                customer_id=customer_id, detected=False, confidence=0.0,
                evidence=[], raw_data={"relative_change": relative_x},
                cusum_value=max(cresult.s_plus, cresult.s_minus),
                alarm_threshold=cresult.threshold,
                evaluated_at=event.event_timestamp,
            )
        if not detected:
            return None

        raw = {
            "baseline_amount": baseline.mu_0,
            "latest_amount": amount,
            "pct_change": round(relative_x, 4),
            "employer_refs_last_5": ref_history[-5:],
            "baseline_window": baseline.computed_from,
            "ref_changed": ref_changed,
        }
        return self._make_result(
            customer_id=customer_id, detected=True, confidence=conf,
            evidence=evidence, raw_data=raw,
            cusum_value=round(max(cresult.s_plus, cresult.s_minus), 4),
            alarm_threshold=round(cresult.threshold, 4),
            evaluated_at=event.event_timestamp,
        )
