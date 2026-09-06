# app/models/records.py
from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint

class SingleSeasonRecord(SQLModel, table=True):
    __tablename__ = "single_season_records"
    __table_args__ = (UniqueConstraint("season","stat","rank", name="uq_single_season_stat_rank"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    stat: str = Field(index=True)
    rank: int = Field(index=True)
    player_id: int = Field(index=True)
    player_name: Optional[str] = None
    team_id: Optional[int] = Field(default=None, index=True)
    value: float = 0.0

class CareerRecord(SQLModel, table=True):
    __tablename__ = "career_records"
    __table_args__ = (UniqueConstraint("stat","rank", name="uq_career_stat_rank"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    stat: str = Field(index=True)
    rank: int = Field(index=True)
    player_id: int = Field(index=True)
    player_name: Optional[str] = None
    value: float = 0.0
