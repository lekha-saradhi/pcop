"""
PCOP Demo Data Generator
Produces scores_v2.json, action_plans.json, herald_content.json
for all 20 demo customers using:
  - Deterministic formulas for ML scores (GraphSAGE, DeepHit, FusionXV2)
  - DeepSeek LLM for HERALD email/SMS content
"""
from __future__ import annotations
import json, math, os, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
BANK_DATA = ROOT.parent / "bank" / "data"
OUT_DIR   = ROOT / "data"
OUT_DIR.mkdir(exist_ok=True)

# â”€â”€ NVIDIA DeepSeek credentials â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
NVIDIA_ENDPOINT = os.environ.get("NVIDIA_ENDPOINT", "https://integrate.api.nvidia.com/v1/chat/completions")
NVIDIA_KEY      = os.environ.get("NVIDIA_API_KEY", "")
MODEL_NAME      = os.environ.get("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-pro")

# â”€â”€ Load customer data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
customers  = json.loads((BANK_DATA / "customers.json").read_text())
life_evts  = json.loads((BANK_DATA / "life_events.json").read_text()) if (BANK_DATA / "life_events.json").exists() else []
crm_notes  = json.loads((BANK_DATA / "crm_notes.json").read_text())  if (BANK_DATA / "crm_notes.json").exists() else []

# Inline signal data (mirrors dataStore.js)
SIGNALS = {
    "C-00000001": [{"type":"location_city","confidence":0.92,"method":"CUSUM","evidence":"City shift Mumbai->Bangalore"},
                   {"type":"transaction_frequency","confidence":0.85,"method":"CUSUM","evidence":"Frequency dropped 35%"}],
    "C-00000002": [{"type":"digital_engagement","confidence":0.78,"method":"CUSUM","evidence":"App logins down 40%"}],
    "C-00000004": [{"type":"stress_overdraft","confidence":0.72,"method":"BOCPD","evidence":"3 overdraft events in 30 days"}],
    "C-00000006": [{"type":"lifecycle_mcc","confidence":0.95,"method":"BOCPD","evidence":"MCC 7261 funeral service"},
                   {"type":"transaction_frequency","confidence":0.88,"method":"CUSUM","evidence":"Volume collapsed 90%"}],
    "C-00000007": [{"type":"digital_engagement","confidence":0.81,"method":"CUSUM","evidence":"Feature views down 50%"}],
    "C-00000008": [{"type":"salary_amount","confidence":0.90,"method":"CUSUM","evidence":"Salary dropped 18%"}],
    "C-00000009": [{"type":"complaint_sentiment","confidence":0.76,"method":"CUSUM","evidence":"Negative sentiment in CRM"}],
    "C-00000011": [{"type":"digital_engagement","confidence":0.74,"method":"CUSUM","evidence":"App engagement down 45%"}],
    "C-00000012": [{"type":"salary_amount","confidence":0.88,"method":"CUSUM","evidence":"Employer reference changed"},
                   {"type":"digital_engagement","confidence":0.92,"method":"BOCPD","evidence":"All engagement signals firing"}],
    "C-00000013": [{"type":"salary_amount","confidence":0.68,"method":"CUSUM","evidence":"Mild salary drift detected"}],
    "C-00000014": [{"type":"location_city","confidence":0.91,"method":"CUSUM","evidence":"City shift Hyderabad->Pune"}],
    "C-00000016": [{"type":"digital_engagement","confidence":0.89,"method":"SPRT","evidence":"Engagement signals active"}],
    "C-00000018": [{"type":"digital_engagement","confidence":0.77,"method":"CUSUM","evidence":"Decay across all channels"}],
    "C-00000019": [{"type":"stress_overdraft","confidence":0.73,"method":"BOCPD","evidence":"Overdraft + repayment issues"}],
    "C-00000020": [{"type":"lifecycle_mcc","confidence":0.82,"method":"rule_ml","evidence":"Jewellery + hotel MCCs (wedding)"}],
}
LIFE_EVENTS = {
    "C-00000001": "job_change / relocation",
    "C-00000006": "bereavement",
    "C-00000008": "salary_change",
    "C-00000012": "job_change",
    "C-00000013": "retirement",
    "C-00000014": "relocation",
    "C-00000019": "financial_stress",
    "C-00000020": "marriage",
}
OFFERS = {
    "HNW":           {"code":"HNW_FEE_WAIVER_12M","desc":"12-month fee waiver","value":"INR 25,000"},
    "Mass Affluent":  {"code":"MA_FEE_WAIVER_6M","desc":"6-month fee waiver","value":"INR 8,000"},
    "Mass Market":    {"code":"MM_CASHBACK_3M","desc":"3-month cashback 2%","value":"INR 2,000"},
    "Digital Native": {"code":"DN_APP_REWARD","desc":"In-app reward points 5x","value":"5x points"},
}

def sigmoid(x): return 1 / (1 + math.exp(-x))

def compute_v2_score(c):
    base  = c["churn_score"]
    cid   = c["customer_id"]

    # Component scores with realistic spread
    seed  = int(cid.split("-")[1])
    noise = lambda s: ((seed * s * 7) % 11 - 5.5) / 100  # deterministic Â±5.5%

    habitat_score = min(0.99, max(0.01, base + noise(3)))
    graph_score   = min(0.99, max(0.01, base + noise(7)))
    tare_score    = min(0.99, max(0.01, base + noise(11)))

    # DeepHit: map churn_score to survival probabilities
    # high churn_score -> high near-term probability
    survival_7d  = sigmoid(6  * (base - 0.72)) if base > 0.65 else base * 0.25
    survival_30d = sigmoid(4  * (base - 0.55))
    survival_90d = sigmoid(2.5 * (base - 0.40))

    # Cap at realistic values
    survival_7d  = round(min(0.92, max(0.005, survival_7d)),  3)
    survival_30d = round(min(0.95, max(0.01,  survival_30d)), 3)
    survival_90d = round(min(0.97, max(0.02,  survival_90d)), 3)

    # Ensure monotone: 7d â‰¤ 30d â‰¤ 90d
    survival_30d = max(survival_30d, survival_7d)
    survival_90d = max(survival_90d, survival_30d)

    # Urgency horizon
    if survival_7d  >= 0.40: urgency = "7d"
    elif survival_30d >= 0.45: urgency = "30d"
    elif survival_90d >= 0.50: urgency = "90d"
    else:                       urgency = None

    # FusionXV2 ensemble (TARE 35%, HABITAT 30%, GraphSAGE 20%, DeepHit 15%)
    final = 0.35*tare_score + 0.30*habitat_score + 0.20*graph_score + 0.15*survival_30d
    final = round(min(0.99, max(0.01, final)), 4)

    # Ensemble disagreement
    scores = [tare_score, habitat_score, graph_score, survival_30d]
    disagree = round(max(scores) - min(scores), 4)

    # Conformal prediction CI (Â±disagreement/2 roughly)
    ci_half = round(disagree * 0.6 + 0.03, 3)
    ci_lower = round(max(0.01, final - ci_half), 3)
    ci_upper = round(min(0.99, final + ci_half), 3)

    # Risk tier
    if final >= 0.80: tier = "critical"
    elif final >= 0.60: tier = "high"
    elif final >= 0.40: tier = "medium"
    elif final >= 0.25: tier = "watch"
    else:               tier = "low"

    return {
        "customer_id": cid,
        "final_score": final,
        "risk_tier": tier,
        "tare_score": round(tare_score, 4),
        "habitat_score": round(habitat_score, 4),
        "graph_score": round(graph_score, 4),
        "survival_7d": survival_7d,
        "survival_30d": survival_30d,
        "survival_90d": survival_90d,
        "urgency_horizon": urgency,
        "ensemble_disagreement": disagree,
        "conformal_lower": ci_lower,
        "conformal_upper": ci_upper,
        "model_version": "chronos-v2-fusionx",
        "scored_at": "2026-05-27T03:24:00Z",
    }

def make_action_plan(c, score):
    cid  = c["customer_id"]
    tier = score["risk_tier"]
    seg  = c["segment"]
    chan_pref = c.get("preferred_channel", "email")
    offer = OFFERS.get(seg, OFFERS["Mass Market"])
    sigs  = SIGNALS.get(cid, [])
    life  = LIFE_EVENTS.get(cid, "")

    urgency_h = score["urgency_horizon"]
    priority  = 1 if tier == "critical" else (2 if tier == "high" else 3)

    # Channel selection
    if tier in ("critical","high") and c.get("call_opt_in") and seg == "HNW":
        channel = "rm_visit"
    elif tier == "critical" and c.get("email_opt_in"):
        channel = "email"
    elif chan_pref in ("app","sms") and c.get("sms_opt_in"):
        channel = "sms" if chan_pref == "sms" else "app"
    elif c.get("email_opt_in"):
        channel = "email"
    else:
        channel = "sms"

    # Timing
    if urgency_h == "7d":  timing = "within_24h"
    elif urgency_h == "30d": timing = "within_48h"
    else:                    timing = "within_7d"

    # Rationale
    sig_text = f"{len(sigs)} active signals ({', '.join(s['type'] for s in sigs[:2])})" if sigs else "pattern-based risk"
    life_text = f"life event: {life}. " if life else ""
    surv_text = f"P(churn 7d)={score['survival_7d']*100:.0f}%. " if urgency_h == "7d" else ""
    rationale = (
        f"{surv_text}{life_text.capitalize()}"
        f"{seg} customer with tenure {c['tenure_years']}yr and {sig_text}. "
        f"Graph network shows peer-group churn contagion risk. "
        f"Conformal CI [{score['conformal_lower']:.2f}â€“{score['conformal_upper']:.2f}]. "
        f"Recommend {channel} with {offer['desc']} before competitor acquisition window."
    )

    return {
        "customer_id": cid,
        "channel": channel,
        "offer_code": offer["code"],
        "offer_description": offer["desc"],
        "offer_value": offer["value"],
        "timing": timing,
        "priority": priority,
        "rationale": rationale,
        "suppressed": False,
        "content_strategy": "full_retention" if urgency_h == "7d" else ("proactive" if tier in ("medium","watch") else "graceful_retention"),
        "urgency_horizon": urgency_h,
        "tone_modifiers": (["urgent","professional"] if urgency_h == "7d" else
                           (["empathetic"] if "bereavement" in life else ["professional"])),
        "generated_at": "2026-05-27T03:25:00Z",
    }

def llm_call(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {NVIDIA_KEY}", "Content-Type": "application/json"}
    body = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 600,
    }
    try:
        r = requests.post(NVIDIA_ENDPOINT, json=body, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"    LLM error: {e}")
        return ""

def make_herald_content(c, plan, score):
    cid  = c["customer_id"]
    name = c["full_name"].split()[0]
    chan = plan["channel"]
    offer_desc = plan["offer_description"]
    offer_val  = plan["offer_value"]
    tenure     = c["tenure_years"]
    seg        = c["segment"]
    life       = LIFE_EVENTS.get(cid, "")
    urgency_h  = score["urgency_horizon"]
    strategy   = plan["content_strategy"]

    # Build prompt
    tone_map = {"urgent":"time-sensitive and warm","empathetic":"empathetic and supportive",
                "professional":"professional and appreciative","celebratory":"warm and celebratory"}
    tone_str = tone_map.get(plan["tone_modifiers"][0] if plan["tone_modifiers"] else "professional", "professional")

    if chan == "email":
        prompt = f"""You are a bank retention specialist writing a personalized outreach email.

Customer: {c['full_name']}, {seg} segment, {tenure} year customer of PCOP
Life context: {life if life else 'no specific life event'}
Offer: {offer_desc} worth {offer_val}
Tone: {tone_str}
Strategy: {strategy}

Write a concise email with:
1. Subject line (max 60 chars, compelling, personalized)
2. Preview text (max 90 chars, continues from subject)
3. Email body (120-180 words, mention their tenure, the specific offer, warm sign-off from their Relationship Manager)

Format as JSON:
{{"subject_line": "...", "preview_text": "...", "body": "..."}}

Only return the JSON, no explanation."""

    elif chan == "sms":
        prompt = f"""Write a personalized bank retention SMS for:
Customer: {name}, {seg}, {tenure} year customer of PCOP
Offer: {offer_desc} worth {offer_val}
Tone: {tone_str}

Write a single SMS under 155 characters that feels personal, mentions the offer, and includes a reply instruction.
Return only the SMS text, no explanation."""

    elif chan == "app":
        prompt = f"""Write a personalized push notification for a bank retention campaign.
Customer: {name}, {seg}, {tenure} year customer
Offer: {offer_desc}
Tone: {tone_str}

Write:
Title (max 45 chars) + Body (max 90 chars) + CTA (max 20 chars)
Format as JSON: {{"title": "...", "body": "...", "cta": "..."}}
Only return the JSON."""

    else:  # rm_visit / call
        prompt = f"""Write a relationship manager call briefing note for a bank retention visit.
Customer: {c['full_name']}, {seg} segment, {tenure} year customer
Life context: {life if life else 'high churn risk detected'}
Offer to present: {offer_desc} worth {offer_val}

Write 3 talking points and 1 opening line. Keep it brief.
Format as JSON: {{"opening": "...", "talking_points": ["...", "...", "..."]}}
Only return the JSON."""

    raw = llm_call(prompt)

    # Parse JSON or use raw
    try:
        parsed = json.loads(raw)
    except Exception:
        # Try to extract JSON from markdown
        import re
        m = re.search(r'\{[\s\S]+\}', raw)
        try:
            parsed = json.loads(m.group()) if m else {}
        except Exception:
            parsed = {}

    result = {
        "customer_id": cid,
        "channel": chan,
        "compliance_status": "approved",
        "content_strategy": strategy,
        "urgency_horizon": urgency_h,
        "tone_modifiers": plan["tone_modifiers"],
        "offer_code": plan["offer_code"],
        "generated_at": "2026-05-27T03:26:00Z",
    }

    if chan == "email":
        result["subject_line"] = parsed.get("subject_line", f"An exclusive offer from PCOP, {name}")
        result["preview_text"] = parsed.get("preview_text", f"Your {tenure}-year relationship means everything to us.")
        result["body"]         = parsed.get("body", f"Dear {name}, as a valued {tenure}-year customer, we have a special offer for you: {offer_desc} worth {offer_val}.")
        result["ab_variant"]   = {
            "subject_line": f"{name}, your PCOP loyalty reward awaits",
            "preview_text": f"Exclusive for {seg} members like you",
        }
    elif chan == "sms":
        result["body"] = raw if raw and len(raw) <= 160 else f"Hi {name}! PCOP exclusive: {offer_desc} worth {offer_val}. Reply YES for details or STOP to opt out."
    elif chan == "app":
        result["title"] = parsed.get("title", f"Exclusive for you, {name}")
        result["body"]  = parsed.get("body", f"{offer_desc} â€” activated for your account")
        result["cta"]   = parsed.get("cta", "Claim Now")
    else:
        result["opening"]       = parsed.get("opening", f"Good morning, this is your Relationship Manager from PCOP calling regarding your account.")
        result["talking_points"] = parsed.get("talking_points", [
            f"Acknowledge {tenure}-year relationship and express genuine appreciation",
            f"Present {offer_desc} worth {offer_val} â€” personalised based on their profile",
            "Ask about recent experience and if they have any concerns or questions"
        ])

    return result

def main():
    print(f"\n{'-'*60}")
    print("  PCOP Demo Data Generator")
    print(f"{'-'*60}")

    # Step 1: Compute v2 scores
    print("\n[1/3] Computing CHRONOS v2 scores...")
    scores_list = []
    scores_map  = {}
    for c in customers:
        s = compute_v2_score(c)
        scores_list.append(s)
        scores_map[c["customer_id"]] = s
    (OUT_DIR / "scores_v2.json").write_text(json.dumps(scores_list, indent=2))
    print(f"  OK {len(scores_list)} customers scored -> data/scores_v2.json")

    # Step 2: Generate action plans
    print("\n[2/3] Generating COMPASS action plans...")
    plans_list = []
    plans_map  = {}
    for c in customers:
        p = make_action_plan(c, scores_map[c["customer_id"]])
        plans_list.append(p)
        plans_map[c["customer_id"]] = p
    (OUT_DIR / "action_plans.json").write_text(json.dumps(plans_list, indent=2))
    print(f"  OK {len(plans_list)} action plans -> data/action_plans.json")

    # Step 3: Generate HERALD content via LLM
    print("\n[3/3] Generating HERALD content via DeepSeek LLM...")
    content_list = []
    for i, c in enumerate(customers):
        cid = c["customer_id"]
        plan = plans_map[cid]
        score = scores_map[cid]
        print(f"  [{i+1:02d}/20] {cid} {c['full_name'][:20]:<20} channel={plan['channel']}", end="", flush=True)
        ct = make_herald_content(c, plan, score)
        content_list.append(ct)
        print(" OK")
        time.sleep(0.3)  # be gentle with the API

    (OUT_DIR / "herald_content.json").write_text(json.dumps(content_list, indent=2))
    print(f"\n  OK {len(content_list)} content pieces -> data/herald_content.json")

    print(f"\n{'-'*60}")
    print("  All demo data generated successfully")
    print(f"{'-'*60}\n")

if __name__ == "__main__":
    main()

