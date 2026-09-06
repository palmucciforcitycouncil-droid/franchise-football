from __future__ import annotations
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field

class CoachRole(str, Enum):
    HC = "HC"
    OC = "OC"
    DC = "DC"
    AC = "AC"   # generic assistant (you may have AC1/AC2 visually; role is AC)

class Coach(SQLModel, table=True):
    coach_id: Optional[int] = Field(default=None, primary_key=True)
    team_id: Optional[int] = Field(default=None, index=True)  # None => FA
    name: str = ""
    role: CoachRole = CoachRole.AC
    overall: int = 60
    age: int = 42

    # Optional ratings used elsewhere (keep if you have them)
    run_pass_tendency: float = 0.0
    offensive_aggression: float = 0.5
    defensive_aggression: float = 0.5
    blitz_rate: float = 0.12
    coverage_mix: float = 0.5
    red_zone_offense: float = 0.0
    red_zone_defense: float = 0.0

class CoachContract(SQLModel, table=True):
    contract_id: Optional[int] = Field(default=None, primary_key=True)
    coach_id: int = Field(index=True)
    team_id: int = Field(index=True)
    start_season: int
    end_season: int
    aav: int
    is_active: bool = Field(default=True, index=True)

class CoachAsk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    coach_id: int = Field(index=True)
    desired_years: int = 3
    desired_aav: int = 2_000_000
    updated_season: int = 0

class CoachJobType(str, Enum):
    HC = "HC"
    OC = "OC"
    DC = "DC"
    AC = "AC"

class CoachOffer(SQLModel, table=True):
    offer_id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    from_team_id: int = Field(index=True)
    to_coach_id: int = Field(index=True)
    job_type: CoachJobType
    years: int
    aav: int
    is_active: bool = Field(default=True, index=True)