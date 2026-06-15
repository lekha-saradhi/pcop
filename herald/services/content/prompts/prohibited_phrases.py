PROHIBITED_PHRASES = [
    # Future rate guarantees
    "guaranteed rate",
    "rate will be",
    "rate is guaranteed",
    "fixed at this rate forever",

    # Superlative claims
    "best bank in india",
    "lowest fees",
    "highest interest",
    "number one bank",
    "unbeatable",
    "no one offers",

    # Competitor comparisons without attribution
    "better than hdfc",
    "better than icici",
    "better than kotak",
    "unlike other banks",
    "compared to competitors",

    # Pressure language
    "limited time only",
    "act now or",
    "expires today",
    "last chance",
    "don't miss out",
    "you will lose",
    "final notice",
    "urgent action required",

    # Discriminatory language
    "as a woman",
    "as a man",
    "because of your religion",
    "based on your caste",
]

PROHIBITED_PATTERNS = [
    # Future rate guarantee pattern
    (r"\d+(\.\d+)?%\s+(guaranteed|assured|fixed forever)", "Future rate guarantee"),
    # ALL CAPS (more than 3 consecutive capital words)
    (r"[A-Z]{4,}\s+[A-Z]{4,}\s+[A-Z]{4,}", "Excessive all-caps"),
    # Specific percentage claims without source
    (r"save up to \d+%", "Unsubstantiated savings claim"),
]
