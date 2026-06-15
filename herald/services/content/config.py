import os


class Config:
    database_url: str = os.environ.get("DATABASE_URL", "postgresql+asyncpg://localhost/pcop")
    kafka_bootstrap_servers: str = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    nvidia_endpoint: str = os.environ.get("NVIDIA_ENDPOINT", "")
    nvidia_api_key: str = os.environ.get("NVIDIA_API_KEY", "")
    scribe_model: str = os.environ.get("SCRIBE_MODEL", "kimi-k2-5")
    herald_demo_mode: bool = os.environ.get("HERALD_DEMO_MODE", "true").lower() == "true"
    herald_max_compliance_retries: int = int(os.environ.get("HERALD_MAX_COMPLIANCE_RETRIES", "2"))


config = Config()
