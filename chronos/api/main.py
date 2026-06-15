"""FastAPI application entry point for CHRONOS scoring service."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import model_health, risk_scores

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CHRONOS Scoring Service",
    description="Neural Risk Intelligence Engine — Layer 3 ML Scoring API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(risk_scores.router)
app.include_router(model_health.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "chronos-scoring"}


@app.on_event("startup")
async def startup_event() -> None:
    from services.scoring.scheduler import create_scheduler

    scheduler = create_scheduler()
    scheduler.start()
    logger.info("CHRONOS scoring service started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    from services.scoring.scheduler import _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    logger.info("CHRONOS scoring service shut down")
