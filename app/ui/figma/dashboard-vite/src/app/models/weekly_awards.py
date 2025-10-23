"""
Weekly Awards Models and Service.
"""

from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field
from enum import Enum


class WeeklyAwardType(str, Enum):
    WPOY_OFF = "WPOY_OFF"
    WPOY_DEF = "WPOY_DEF"
    WPOY_ST = "WPOY_ST"


class WeeklyAward(SQLModel, table=True):
    __tablename__ = "weekly_awards"
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    award: WeeklyAwardType = Field(index=True)
    player_id: Optional[int] = Field(default=None, index=True)
    team_id: Optional[int] = Field(default=None, index=True)
    game_id: Optional[int] = Field(default=None, index=True)
    notes: Optional[str] = Field(default=None)
