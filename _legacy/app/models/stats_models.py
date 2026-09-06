from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class TeamGameStats(SQLModel, table=True):
    __tablename__ = "team_game_stats"
    id: int | None = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    team_id: int = Field(index=True)
    is_home: bool
    points: int
    plays: int
    yards_total: int
    pass_yards: int
    rush_yards: int
    turnovers: int
