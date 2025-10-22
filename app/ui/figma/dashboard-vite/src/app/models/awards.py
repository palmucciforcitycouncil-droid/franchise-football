"""
Award models and DTOs for season awards and leaderboards.
"""

from __future__ import annotations
from typing import Optional, List
from sqlmodel import SQLModel, Field
from enum import Enum


class AwardType(str, Enum):
    MVP = "MVP"
    OPOY_AFC = "OPOY_AFC"
    OPOY_NFC = "OPOY_NFC"
    DPOY_AFC = "DPOY_AFC"
    DPOY_NFC = "DPOY_NFC"
    OROY = "OROY"
    DROY = "DROY"
    COY = "COY"
    GMY = "GMY"
    SBMVP = "SBMVP"


class AwardWinner(SQLModel, table=True):
    __tablename__ = "award_winners"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    award: AwardType = Field(index=True)
    player_id: Optional[int] = Field(default=None, index=True)
    coach_id: Optional[int] = Field(default=None, index=True)
    gm_id: Optional[int] = Field(default=None, index=True)
    team_id: Optional[int] = Field(default=None, index=True)
    game_id: Optional[int] = Field(default=None, index=True)  # for SBMVP
    notes: Optional[str] = Field(default=None)


class LeaderRow(SQLModel):
    name: str
    player_id: int
    team_id: int
    value: float
    extra: Optional[str] = None


class Leaderboard(SQLModel):
    title: str
    leaders: List[LeaderRow]
