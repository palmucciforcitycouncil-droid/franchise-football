# app/ui/api_awards.py
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db import get_session
from app.models.awards import WeeklyAward, AnnualAward, AnnualAwardProjection, WeeklyAwardType, AnnualAwardType
from app.models.stats import RecordEntry

router = APIRouter(prefix="/api/v1/awards", tags=["awards"])

class WeeklyAwardDTO(BaseModel):
    award: str
    season: int
    week: int
    winner_player_id: Optional[int]
    winner_team_id: Optional[int]
    score: float
    stats_blob: str

@router.get("/weekly", response_model=List[WeeklyAwardDTO])
def weekly(season: int, week: int, sess: Session = Depends(get_session)):
    """Get weekly awards for a specific season and week."""
    rows = list(sess.exec(select(WeeklyAward).where(WeeklyAward.season==season, WeeklyAward.week==week)))
    return [WeeklyAwardDTO(
        award=r.award, 
        season=r.season, 
        week=r.week, 
        winner_player_id=r.winner_player_id,
        winner_team_id=r.winner_team_id, 
        score=r.score, 
        stats_blob=r.stats_blob
    ) for r in rows]

class AnnualProjDTO(BaseModel):
    award: str
    rank: int
    candidate_type: str
    candidate_id: int
    team_id: Optional[int]
    score: float
    stats_blob: str

@router.get("/annual/projections", response_model=List[AnnualProjDTO])
def annual_projections(season: int, sess: Session = Depends(get_session)):
    """Get annual award projections for a specific season."""
    rows = list(sess.exec(select(AnnualAwardProjection).where(AnnualAwardProjection.season==season).order_by(AnnualAwardProjection.award, AnnualAwardProjection.rank)))
    return [AnnualProjDTO(
        award=r.award, 
        rank=r.rank, 
        candidate_type=r.candidate_type, 
        candidate_id=r.candidate_id,
        team_id=r.team_id, 
        score=r.score, 
        stats_blob=r.stats_blob
    ) for r in rows]

class AnnualFinalDTO(BaseModel):
    award: str
    season: int
    finalized: bool
    winner_player_id: Optional[int]
    winner_team_id: Optional[int]
    winner_coach_id: Optional[int]
    winner_gm_id: Optional[int]
    score: float

@router.get("/annual/final", response_model=List[AnnualFinalDTO])
def annual_final(season: int, sess: Session = Depends(get_session)):
    """Get finalized annual awards for a specific season."""
    rows = list(sess.exec(select(AnnualAward).where(AnnualAward.season==season)))
    return [AnnualFinalDTO(
        award=r.award, 
        season=r.season, 
        finalized=r.finalized, 
        winner_player_id=r.winner_player_id,
        winner_team_id=r.winner_team_id, 
        winner_coach_id=r.winner_coach_id, 
        winner_gm_id=r.winner_gm_id, 
        score=r.score
    ) for r in rows]

class RecordDTO(BaseModel):
    record_type: str
    category: str
    season: Optional[int]
    player_id: int
    value: float

@router.get("/records", response_model=List[RecordDTO])
def records(sess: Session = Depends(get_session)):
    """Get all records (single-season and career)."""
    rows = list(sess.exec(select(RecordEntry)))
    return [RecordDTO(
        record_type=r.record_type, 
        category=r.category, 
        season=r.season, 
        player_id=r.player_id, 
        value=r.value
    ) for r in rows]


