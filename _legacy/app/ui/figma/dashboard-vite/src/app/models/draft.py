from __future__ import annotations
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field

class ProspectPosition(str, Enum):
    QB="QB"; RB="RB"; WR="WR"; TE="TE"; LT="LT"; G="G"; C="C"; RT="RT"
    EDGE="EDGE"; DL="DL"; LB="LB"; CB="CB"; S="S"; K="K"; P="P"

class Prospect(SQLModel, table=True):
    prospect_id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    name: str
    pos: ProspectPosition = Field(index=True)
    age: int = 21
    overall: int = 60
    ceiling: int = 80
    floor: int = 55
    archetype: str = ""
    college: str = ""
    # combine-ish
    speed: int = 60
    strength: int = 60
    agility: int = 60
    iq: int = 60
    volatility: int = 5
    drafted_by_team_id: Optional[int] = Field(default=None, index=True)
    drafted_round: Optional[int] = None
    drafted_slot: Optional[int] = None

class ScoutingReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    team_id: int = Field(index=True)
    prospect_id: int = Field(index=True)
    bias_overall: int = 0              # team-specific +/- to "scouted_overall"
    confidence: int = 70               # % certainty (affects variance shown)
    notes: str = ""

class DraftBoard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    team_id: int = Field(index=True)
    rank: int = Field(index=True)      # 1 = highest
    prospect_id: int = Field(index=True)

class DraftPickInventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    round: int = Field(index=True)
    slot: int = Field(index=True)      # 1..32 per round
    owning_team_id: int = Field(index=True)
    original_team_id: int = Field(index=True)

class DraftState(SQLModel, table=True):
    season: int = Field(primary_key=True)
    current_round: int = 1
    current_pick_slot: int = 1
    is_active: bool = False
    seed: int = 4242