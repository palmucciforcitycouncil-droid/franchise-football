from __future__ import annotations
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field

class OffAgg(str, Enum):
    VERY_CONSERVATIVE = "Very Conservative"
    CONSERVATIVE = "Conservative"
    BALANCED = "Balanced"
    AGGRESSIVE = "Aggressive"
    VERY_AGGRESSIVE = "Very Aggressive"

class DefAgg(str, Enum):
    VERY_CONSERVATIVE = "Very Conservative"
    CONSERVATIVE = "Conservative"
    BALANCED = "Balanced"
    AGGRESSIVE = "Aggressive"
    VERY_AGGRESSIVE = "Very Aggressive"

class Coverage(str, Enum):
    MAN_HEAVY = "Man-Heavy"
    HYBRID = "Hybrid"
    ZONE_HEAVY = "Zone-Heavy"

class BlitzStrategy(str, Enum):
    SELECTIVE = "Selective"
    STANDARD = "Standard"
    BLITZ_HEAVY = "Blitz Heavy"

class RZOff(str, Enum):
    POWER_RUN = "Power Run"
    BALANCED = "Balanced"
    PLAY_ACTION_HEAVY = "Play-Action Heavy"
    SPREAD_SHOT = "Spread/Shot"

class RZDef(str, Enum):
    BEND = "Bend-Don't-Break"
    BALANCED = "Balanced"
    RUN_SELLOUT = "Run-Sellout"
    PRESSURE_QB = "Pressure QB"

class GameplanSelection(SQLModel, table=True):
    """
    One row per matchup, user team perspective.
    Only Head Coaches (HC) can set gameplans.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    team_id: int = Field(index=True)
    opponent_team_id: int = Field(index=True)
    coach_id: int = Field(index=True)  # Must be HC role
    coach_role: str = Field(default="HC")  # Always "HC" for gameplans

    off_agg: OffAgg = OffAgg.BALANCED
    def_agg: DefAgg = DefAgg.BALANCED
    coverage: Coverage = Coverage.HYBRID
    blitz_strategy: BlitzStrategy = BlitzStrategy.STANDARD
    rz_off: RZOff = RZOff.BALANCED
    rz_def: RZDef = RZDef.BALANCED
