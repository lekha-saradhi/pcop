"""ARGUS engine configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ARGUSConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://pcop:pcop@localhost:5432/pcop"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_alarm_topic: str = "pcop.alarms.v1"

    # Statistical control parameters
    arl0: int = 500          # target average run length under H0
    fdr_level: float = 0.05  # BH-FDR target level q

    # TEMPO Kalman process noise
    tempo_q_slow: float = 0.001   # normal drift noise (fraction of sigma^2)
    tempo_q_fast: float = 0.100   # fast-update noise after life event
    tempo_resume_days: int = 7    # days after alarm clear before baseline resumes

    log_level: str = "INFO"


settings = ARGUSConfig()
