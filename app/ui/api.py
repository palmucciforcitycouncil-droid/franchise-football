from __future__ import annotations
import logging
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("api")

app = FastAPI(title="Franchise Football API", version=settings.gdd_version)

@app.get("/health")
def health():
    logger.debug("Health check requested.")
    return {"status": "ok", "version": settings.gdd_version}
