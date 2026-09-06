from __future__ import annotations
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from app.core.db import get_session
from app.models.awards import AwardsWeekly, AwardsAnnual
from app.models.hof import HallOfFameInductee
from app.services.awards_service import compute_weekly_awards, compute_annual_awards
from app.services.hof_service import induct_hof

router = APIRouter(prefix="/api/v1", tags=["awards-hof"])

# ---- Read endpoints
class WeeklyDTO(BaseModel):
    season: int; week: int; award_type: str; player_id: int; team_id: int; game_id: int; score: float

@router.get("/awards/weekly", response_model=List[WeeklyDTO])
def api_weekly(season: int, week: int, sess: Session = Depends(get_session)):
    rows = list(sess.exec(select(AwardsWeekly).where(AwardsWeekly.season==season, AwardsWeekly.week==week)))
    return [WeeklyDTO(season=r.season, week=r.week, award_type=r.award_type.value, player_id=r.player_id, team_id=r.team_id, game_id=r.game_id, score=r.score) for r in rows]

class AnnualDTO(BaseModel):
    season: int; award_type: str; player_id: int | None; coach_id: int | None; team_id: int | None; score: float

@router.get("/awards/annual", response_model=List[AnnualDTO])
def api_annual(season: int, sess: Session = Depends(get_session)):
    rows = list(sess.exec(select(AwardsAnnual).where(AwardsAnnual.season==season)))
    return [AnnualDTO(season=r.season, award_type=r.award_type.value, player_id=r.player_id, coach_id=r.coach_id, team_id=r.team_id, score=r.score) for r in rows]

class HofDTO(BaseModel):
    season: int; entity_type: str; player_id: int | None; coach_id: int | None; summary: str; score: float

@router.get("/hof", response_model=List[HofDTO])
def api_hof(season: int, sess: Session = Depends(get_session)):
    rows = list(sess.exec(select(HallOfFameInductee).where(HallOfFameInductee.season==season)))
    return [HofDTO(season=r.season, entity_type=r.entity_type.value, player_id=r.player_id, coach_id=r.coach_id, summary=r.summary, score=r.score) for r in rows]

# ---- Triggers (admin/commissioner actions)
@router.post("/awards/recompute_week")
def api_recompute_week(season: int, week: int, sess: Session = Depends(get_session)):
    return compute_weekly_awards(sess, season=season, week=week)

@router.post("/awards/compute_annual")
def api_compute_annual(season: int, sess: Session = Depends(get_session)):
    return compute_annual_awards(sess, season=season)

@router.post("/hof/induct")
def api_hof_induct(season: int, sess: Session = Depends(get_session)):
    return induct_hof(sess, season=season)
