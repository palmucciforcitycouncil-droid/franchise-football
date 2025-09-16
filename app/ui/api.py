from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.database import get_session, create_db_and_tables
from app.models import Team, Player, DepthChart, GameResult
from app.models.dtos import TeamDTO, PlayerDTO, DepthChartDTO, GameResultDTO

# Create the FastAPI app FIRST, then use it in route decorators
app = FastAPI(title="Franchise Football API", version="0.1.0")

@app.get("/health")
def health():
    # tests expect a "version" key
    return {"status": "ok", "version": app.version}

SessionDep = Annotated[Session, Depends(get_session)]

# --- Teams ---
@app.get("/teams", response_model=List[TeamDTO])
def list_teams(session: SessionDep) -> List[TeamDTO]:
    rows = session.query(Team).all()
    return [TeamDTO.model_validate(r) for r in rows]

@app.get("/teams/{team_id}", response_model=TeamDTO)
def get_team(team_id: int, session: SessionDep) -> TeamDTO:
    row = session.get(Team, team_id)
    if not row:
        raise HTTPException(status_code=404, detail="team not found")
    return TeamDTO.model_validate(row)

# --- Players ---
@app.get("/players", response_model=List[PlayerDTO])
def list_players(session: SessionDep, team_id: Optional[int] = Query(default=None)) -> List[PlayerDTO]:
    q = session.query(Player)
    if team_id is not None:
        q = q.filter(Player.team_id == team_id)
    rows = q.all()
    return [PlayerDTO.model_validate(r) for r in rows]

@app.get("/players/{player_id}", response_model=PlayerDTO)
def get_player(player_id: int, session: SessionDep) -> PlayerDTO:
    row = session.get(Player, player_id)
    if not row:
        raise HTTPException(status_code=404, detail="player not found")
    return PlayerDTO.model_validate(row)

# --- Depth Chart ---
@app.get("/depth-chart/{team_id}", response_model=List[DepthChartDTO])
def get_depth_chart(team_id: int, session: SessionDep) -> List[DepthChartDTO]:
    rows = session.query(DepthChart).filter(DepthChart.team_id == team_id).all()
    return [DepthChartDTO.model_validate(r) for r in rows]

# --- Games ---
@app.get("/games", response_model=List[GameResultDTO])
def list_games(session: SessionDep, season: Optional[int] = Query(default=None)) -> List[GameResultDTO]:
    q = session.query(GameResult)
    if season is not None:
        q = q.filter(GameResult.season == season)
    rows = q.all()
    return [GameResultDTO.model_validate(r) for r in rows]

# Best-effort: create tables for local sqlite if missing
def _ensure_db():
    try:
        create_db_and_tables()
    except Exception:
        pass

_ensure_db()
