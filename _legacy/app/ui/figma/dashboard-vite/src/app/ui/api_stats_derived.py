# app/ui/api_stats_derived.py
from __future__ import annotations
from typing import Dict
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db import get_session
from app.models.stats import PlayerSeasonStats
from app.services.stats_derived import derive_all

router = APIRouter(prefix="/api/v1/stats/derived", tags=["stats-derived"])

@router.get("/player/season/{player_id}")
def player_season_derived(player_id: int, season: int, sess: Session = Depends(get_session)) -> Dict[str, float]:
    """Get derived metrics for a player's season stats."""
    r = sess.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.player_id==player_id, PlayerSeasonStats.season==season)).first()
    if not r:
        return {}
    stats = r.model_dump()
    touches = stats.get("rush_att",0) + stats.get("rec",0) + stats.get("pass_att",0)  # simple proxy
    return derive_all(stats, touches)


