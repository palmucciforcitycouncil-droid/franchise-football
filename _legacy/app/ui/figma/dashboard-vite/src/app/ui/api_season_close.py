from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from app.core.db import get_session
from app.services.awards_service import compute_annual_awards
from app.services.hof_service import induct_hof

router = APIRouter(prefix="/api/v1/season", tags=["season-close"])

@router.post("/close")
def season_close(season: int = Query(...), sess: Session = Depends(get_session)):
    a = compute_annual_awards(sess, season=season)
    h = induct_hof(sess, season=season)
    return {"ok": True, "annual_awards": a, "hof": h}
