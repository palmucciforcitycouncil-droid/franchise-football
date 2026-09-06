from __future__ import annotations
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field

class WeeklyAwardType(str, Enum):
    OFF_POW = "OFF_POW"
    DEF_POW = "DEF_POW"
    ST_POW  = "ST_POW"

class AnnualAwardType(str, Enum):
    MVP  = "MVP"
    OPOY = "OPOY"
    DPOY = "DPOY"
    ROY  = "ROY"
    COY  = "COY"   # Coach of the Year
    GMOY = "GMOY"  # GM of the Year (proxy: team improvement + cap health; MVP rules simplified)

class AwardsWeekly(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    award_type: WeeklyAwardType = Field(index=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    game_id: int = Field(index=True)
    score: float = 0.0  # leaderboard score used to pick

class AwardsAnnual(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    award_type: AnnualAwardType = Field(index=True)
    player_id: Optional[int] = Field(default=None, index=True)
    coach_id: Optional[int] = Field(default=None, index=True)
    team_id: Optional[int] = Field(default=None, index=True)
    score: float = 0.0