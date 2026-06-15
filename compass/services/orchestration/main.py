import asyncio
import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .kafka.consumer import CompassConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="COMPASS Orchestration Engine",
    description="PCOP Layer 4 — Next-Best-Action Agentic Orchestration",
    version="1.0.0",
)

_consumer_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup():
    global _consumer_task
    demo_mode = os.environ.get("COMPASS_DEMO_MODE", "true").lower() == "true"
    consumer = CompassConsumer(demo_mode=demo_mode)
    _consumer_task = asyncio.create_task(consumer.run())
    logger.info(f"COMPASS consumer started (demo_mode={demo_mode})")


@app.on_event("shutdown")
async def shutdown():
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    logger.info("COMPASS consumer stopped")


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "service": "compass-layer4"})


if __name__ == "__main__":
    uvicorn.run(
        "services.orchestration.main:app",
        host="0.0.0.0",
        port=8004,
        reload=False,
    )
