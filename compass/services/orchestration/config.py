import os
from dataclasses import dataclass


@dataclass
class CompassConfig:
    nvidia_endpoint: str = os.environ.get("NVIDIA_ENDPOINT", "")
    nvidia_api_key: str = os.environ.get("NVIDIA_API_KEY", "")
    cognition_model: str = os.environ.get("COGNITION_MODEL", "kimi-k2-6-thinking")
    compass_model: str = os.environ.get("COMPASS_MODEL", "kimi-k2-5")

    demo_mode: bool = os.environ.get("COMPASS_DEMO_MODE", "true").lower() == "true"
    max_tool_rounds_cognition: int = int(os.environ.get("COMPASS_MAX_TOOL_ROUNDS_COGNITION", "5"))
    max_tool_rounds_nba: int = int(os.environ.get("COMPASS_MAX_TOOL_ROUNDS_NBA", "3"))
    rescue_threshold: float = float(os.environ.get("COMPASS_RESCUE_THRESHOLD", "0.92"))
    fatigue_limit_30d: int = int(os.environ.get("COMPASS_FATIGUE_LIMIT_30D", "4"))

    kafka_bootstrap: str = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    database_url: str = os.environ.get("DATABASE_URL", "")
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


config = CompassConfig()
