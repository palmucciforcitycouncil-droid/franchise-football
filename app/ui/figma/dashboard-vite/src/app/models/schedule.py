from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class Game(SQLModel, table=True):
    """Game model for tracking scheduled games."""
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    home_team_id: int = Field(index=True)
    away_team_id: int = Field(index=True)

class GameResult(SQLModel, table=True):
    """Game result model for tracking game outcomes."""
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True, unique=True)
    home_score: int
    away_score: int

