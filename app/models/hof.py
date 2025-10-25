from __future__ import annotations
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field

class HoFType(str, Enum):
    PLAYER = "PLAYER"
    COACH  = "COACH"

class HallOfFameInductee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)          # induction season
    entity_type: HoFType = Field(index=True)
    player_id: Optional[int] = Field(default=None, index=True)
    coach_id: Optional[int] = Field(default=None, index=True)
    summary: str = ""                        # short human-readable justification
    score: float = 0.0