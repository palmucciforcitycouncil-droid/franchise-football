from __future__ import annotations
from typing import Optional
from sqlmodel import Session, select

def get_team(session: Session, team_model: type, team_id: int):
    """Get a team by ID."""
    return session.exec(select(team_model).where(team_model.id==team_id)).first()

def get_or_create_team_game(session: Session, team_game_model: type, game_id: int, team_id: int):
    """Get or create a TeamGame row for a specific game and team."""
    row = session.exec(
        select(team_game_model).where(
            team_game_model.game_id==game_id, team_game_model.team_id==team_id
        )
    ).first()
    if row: 
        return row
    row = team_game_model(game_id=game_id, team_id=team_id)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row

def safe_inc(obj, field: str, val: int|float):
    """Safely increment a field on an object."""
    try:
        cur = getattr(obj, field, 0) or 0
        setattr(obj, field, cur + val)
    except Exception:
        pass
