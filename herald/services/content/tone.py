def derive_tone_modifiers(signals: list[dict]) -> list[str]:
    modifiers = []
    detected_types = {s["signal_type"] for s in signals if s.get("detected")}

    if "beta_cusum_sentiment" in detected_types:
        modifiers.append("empathetic")
    if "cfsi_stress" in detected_types:
        modifiers.extend(["supportive", "non_promotional"])
    if "lifecycle_mcc_bereavement" in detected_types:
        modifiers.extend(["sensitive", "non_promotional"])
    if any(t in detected_types for t in ["lifecycle_mcc_marriage", "lifecycle_mcc_baby"]):
        modifiers.append("celebratory")
    if "nexus_correlation" in detected_types or "oracle_multivariate" in detected_types:
        if "urgent" not in modifiers:
            modifiers.append("urgent")
    if "ewma_engagement" in detected_types and not modifiers:
        modifiers.append("warm_reengagement")
    if not modifiers:
        modifiers.append("professional")

    return list(set(modifiers))


def derive_content_strategy(treatability: float, final_score: float, risk_tier: str) -> str:
    if risk_tier in ["watch", "low"]:
        return "proactive"
    if treatability >= 0.5 and final_score >= 0.65:
        return "full_retention"
    if treatability < 0.5 and final_score >= 0.65:
        return "graceful_retention"
    if treatability >= 0.5 and final_score >= 0.40:
        return "proactive"
    return "monitor"
