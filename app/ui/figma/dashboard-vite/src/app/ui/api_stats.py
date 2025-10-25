# app/ui/api_stats.py
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db import get_session
from app.models.stats import PlayerSeasonStats, PlayerCareerStats, TeamSeasonStats, RecordEntry, RecordType

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])

class PlayerSeasonDTO(BaseModel):
    player_id: int
    season: int
    team_id: int
    pass_yds: int
    rush_yds: int
    rec_yds: int
    sacks: float
    ints: int
    tackles: int

@router.get("/player/season/{player_id}", response_model=List[PlayerSeasonDTO])
def player_season(player_id: int, sess: Session = Depends(get_session)):
    """Get all season stats for a player."""
    rows = list(sess.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == player_id)))
    out = []
    for r in rows:
        out.append(PlayerSeasonDTO(
            player_id=r.player_id, 
            season=r.season, 
            team_id=r.team_id,
            pass_yds=r.pass_yds, 
            rush_yds=r.rush_yds, 
            rec_yds=r.rec_yds, 
            sacks=float(r.sacks), 
            ints=r.ints, 
            tackles=r.tackles
        ))
    return out

class PlayerCareerDTO(BaseModel):
    player_id: int
    seasons: int
    pass_yds: int
    rush_yds: int
    rec_yds: int
    sacks: float
    ints: int
    tackles: int

@router.get("/player/career/{player_id}", response_model=Optional[PlayerCareerDTO])
def player_career(player_id: int, sess: Session = Depends(get_session)):
    """Get career stats for a player."""
    row = sess.exec(select(PlayerCareerStats).where(PlayerCareerStats.player_id == player_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Player career stats not found")
    
    return PlayerCareerDTO(
        player_id=row.player_id,
        seasons=row.seasons,
        pass_yds=row.pass_yds,
        rush_yds=row.rush_yds,
        rec_yds=row.rec_yds,
        sacks=float(row.sacks),
        ints=row.ints,
        tackles=row.tackles
    )

class TeamSeasonDTO(BaseModel):
    season: int
    team_id: int
    wins: int
    losses: int
    ties: int
    points_for: int
    points_against: int
    total_yds: int
    pass_yds: int
    rush_yds: int

@router.get("/team/season/{team_id}", response_model=List[TeamSeasonDTO])
def team_season(team_id: int, sess: Session = Depends(get_session)):
    """Get all season stats for a team."""
    rows = list(sess.exec(select(TeamSeasonStats).where(TeamSeasonStats.team_id == team_id)))
    out = []
    for r in rows:
        out.append(TeamSeasonDTO(
            season=r.season,
            team_id=r.team_id,
            wins=r.wins,
            losses=r.losses,
            ties=r.ties,
            points_for=r.points_for,
            points_against=r.points_against,
            total_yds=r.total_yds,
            pass_yds=r.pass_yds,
            rush_yds=r.rush_yds
        ))
    return out

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

@router.get("/records/single-season", response_model=List[RecordDTO])
def single_season_records(sess: Session = Depends(get_session)):
    """Get single-season records only."""
    rows = list(sess.exec(select(RecordEntry).where(RecordEntry.record_type == RecordType.SINGLE_SEASON)))
    return [RecordDTO(
        record_type=r.record_type, 
        category=r.category, 
        season=r.season, 
        player_id=r.player_id, 
        value=r.value
    ) for r in rows]

@router.get("/records/career", response_model=List[RecordDTO])
def career_records(sess: Session = Depends(get_session)):
    """Get career records only."""
    rows = list(sess.exec(select(RecordEntry).where(RecordEntry.record_type == RecordType.CAREER)))
    return [RecordDTO(
        record_type=r.record_type, 
        category=r.category, 
        season=r.season, 
        player_id=r.player_id, 
        value=r.value
    ) for r in rows]