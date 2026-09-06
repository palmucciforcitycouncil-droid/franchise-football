from __future__ import annotations
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from app.core.db import get_session
from app.services.results_service import week_scoreboard, team_schedule, game_box

router = APIRouter(prefix="/api/v1", tags=["schedule-results"])

class ScoreboardRow(BaseModel):
    game_id: int
    home_team_id: int
    away_team_id: int
    home_score: int | None
    away_score: int | None

@router.get("/schedule/week", response_model=List[ScoreboardRow])
def api_week(season: int, week: int, sess: Session = Depends(get_session)):
    """Get the scoreboard for a specific week."""
    data = week_scoreboard(sess, season, week)
    return [ScoreboardRow(**d) for d in data]

class TeamGameRow(BaseModel):
    game_id: int
    week: int
    home_team_id: int
    away_team_id: int
    home_score: int | None
    away_score: int | None

@router.get("/schedule/team", response_model=List[TeamGameRow])
def api_team(season: int, team_id: int, sess: Session = Depends(get_session)):
    """Get the full schedule for a specific team."""
    data = team_schedule(sess, season, team_id)
    return [TeamGameRow(**d) for d in data]

@router.get("/results/box")
def api_box(game_id: int, sess: Session = Depends(get_session)):
    """Get the complete box score for a specific game."""
    return game_box(sess, game_id)

