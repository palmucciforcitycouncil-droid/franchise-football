# app/api/routes/dashboard.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session
from app.db import get_engine
from app.services.analytics import league_summary_for, trend_summary, awards_recap, progression_risers_fallers

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def _session() -> Session:
    return Session(get_engine())

@router.get("/trends")
def get_trends(start: int, end: int):
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")
    with _session() as s:
        data = trend_summary(s, start, end)
        if not data["seasons"]:
            raise HTTPException(status_code=404, detail="No trend data in range")
        return data

@router.get("/{season}")
def get_dashboard_tiles(season: int, top_n: int = Query(5, ge=1, le=25)):
    with _session() as s:
        summary = league_summary_for(s, season)
        if not summary:
            raise HTTPException(status_code=404, detail="No league summary for season")
        awards = awards_recap(s, season)
        prog = progression_risers_fallers(s, season, top_n=top_n)
        return {"season": season, "summary": summary, "awards": awards, "progression": prog}
