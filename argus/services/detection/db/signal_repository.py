"""Signal repository — DB read/write interface for signal_results table.

Writes ARGUS outputs; CHRONOS (Layer 3) reads from this table.
Interface is intentionally minimal — statistical logic lives in agents.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SignalRepository:
    """Thin adapter over SQLAlchemy for signal_results writes.

    Falls back to in-memory dict when database is unavailable (e.g. tests).
    """

    def __init__(self, database_url: str | None = None) -> None:
        self._engine: Any = None
        self._session_factory: Any = None
        self._in_memory: list[dict] = []

        if database_url:
            try:
                from sqlalchemy import create_engine, text  # type: ignore[import]
                from sqlalchemy.orm import sessionmaker
                self._engine = create_engine(database_url, pool_pre_ping=True)
                self._session_factory = sessionmaker(bind=self._engine)
                logger.info("SignalRepository: connected to %s", database_url)
            except Exception as exc:
                logger.warning("SignalRepository: DB unavailable, using in-memory (%s)", exc)

    def upsert_signal_result(self, row: dict[str, Any]) -> None:
        """Write or update a signal result row.

        Expected keys (subset of signal_results table):
            customer_id, signal_type, detected, confidence, evidence,
            cusum_value, alarm_threshold, method_used, evaluated_at,
            p_value, fdr_adjusted_p, onset_estimate, direction,
            baseline_mean, baseline_std, expires_at, alarm_severity,
            method_version.
        """
        row.setdefault("evaluated_at", datetime.now(tz=timezone.utc).isoformat())
        row.setdefault("method_version", "argus-v1")

        if self._session_factory is None:
            self._in_memory.append(row)
            return

        try:
            with self._session_factory() as session:
                from sqlalchemy import text
                session.execute(
                    text("""
                        INSERT INTO signal_results (
                            customer_id, signal_type, detected, confidence, evidence,
                            cusum_value, alarm_threshold, method_used, evaluated_at,
                            p_value, fdr_adjusted_p, onset_estimate, direction,
                            baseline_mean, baseline_std, expires_at, alarm_severity,
                            method_version
                        ) VALUES (
                            :customer_id, :signal_type, :detected, :confidence, :evidence,
                            :cusum_value, :alarm_threshold, :method_used, :evaluated_at,
                            :p_value, :fdr_adjusted_p, :onset_estimate, :direction,
                            :baseline_mean, :baseline_std, :expires_at, :alarm_severity,
                            :method_version
                        )
                        ON CONFLICT (customer_id, signal_type) DO UPDATE SET
                            detected = EXCLUDED.detected,
                            confidence = EXCLUDED.confidence,
                            evidence = EXCLUDED.evidence,
                            cusum_value = EXCLUDED.cusum_value,
                            alarm_threshold = EXCLUDED.alarm_threshold,
                            evaluated_at = EXCLUDED.evaluated_at,
                            p_value = EXCLUDED.p_value,
                            fdr_adjusted_p = EXCLUDED.fdr_adjusted_p,
                            onset_estimate = EXCLUDED.onset_estimate,
                            direction = EXCLUDED.direction,
                            baseline_mean = EXCLUDED.baseline_mean,
                            baseline_std = EXCLUDED.baseline_std,
                            expires_at = EXCLUDED.expires_at,
                            alarm_severity = EXCLUDED.alarm_severity,
                            method_version = EXCLUDED.method_version
                    """),
                    row,
                )
                session.commit()
        except Exception as exc:
            logger.error("SignalRepository: write failed: %s", exc)

    def get_active_signal_count(self, customer_id: str) -> int:
        """Return count of non-expired active signals for a customer."""
        if self._session_factory is None:
            return sum(1 for r in self._in_memory if r.get("customer_id") == customer_id and r.get("detected"))

        try:
            with self._session_factory() as session:
                from sqlalchemy import text
                result = session.execute(
                    text("""
                        SELECT COUNT(*) FROM signal_results
                        WHERE customer_id = :cid
                          AND detected = TRUE
                          AND (expires_at IS NULL OR expires_at > NOW())
                    """),
                    {"cid": customer_id},
                )
                return int(result.scalar() or 0)
        except Exception as exc:
            logger.error("SignalRepository: count query failed: %s", exc)
            return 0
