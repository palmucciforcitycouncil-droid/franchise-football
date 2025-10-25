from __future__ import annotations
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session
from app.core.db import get_session
from app.services.season_orchestrator import sim_week
from app.services.event_log_service import feed_since

router = APIRouter(prefix="/api/v1/season", tags=["season"])

class SimRes(BaseModel):
    ok: bool
    games: List[Dict[str, Any]]

@router.post("/sim_week", response_model=SimRes)
def api_sim_week(season: int = Query(...), week: int = Query(...), seed: int = Query(12345),
                 sess: Session = Depends(get_session)):
    out = sim_week(sess, season=season, week=week, seed=seed)
    return SimRes(**out)

# ---- Event feed (global) ----
from app.models.event_log import EventLog
feed_router = APIRouter(prefix="/api/v1", tags=["feed"])

@feed_router.get("/feed")
def api_feed(since_id: Optional[int] = None, sess: Session = Depends(get_session)):
    return feed_since(sess, since_id=since_id or None, limit=200)
