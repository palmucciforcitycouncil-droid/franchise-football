from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class PlayerSeasonStats(SQLModel, table=True):
    __tablename__ = "player_season_stats"

    id: Optional[int] = Field(default=None, primary_key=True)

    season: int = Field(index=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    player_id: int = Field(foreign_key="player.id", index=True)

    # Simple catch-all counters (safe defaults)
    games_played: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0
    receiving_yards: int = 0
    tackles: int = 0
    sacks: int = 0
    interceptions: int = 0
    touchdowns: int = 0
