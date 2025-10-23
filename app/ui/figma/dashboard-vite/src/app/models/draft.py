# app/models/draft.py
from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint

class DraftClass(SQLModel, table=True):
    __tablename__ = "draft_classes"
    __table_args__ = (UniqueConstraint("season", name="uq_draft_class_season"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    seed_used: int = 0
    prospects: int = 0

class Prospect(SQLModel, table=True):
    __tablename__ = "prospects"
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    name: str
    pos: str
    overall: int
    speed: int
    strength: int
    agility: int
    awareness: int
    potential: int
    drafted_by_team_id: Optional[int] = Field(default=None, index=True)
    drafted_overall_pick: Optional[int] = Field(default=None, index=True)

class DraftPick(SQLModel, table=True):
    __tablename__ = "draft_picks"
    __table_args__ = (UniqueConstraint("season","overall_pick", name="uq_pick"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    round: int = Field(index=True)
    pick_in_round: int = Field(index=True)
    overall_pick: int = Field(index=True)
    team_id: int = Field(index=True)
    prospect_id: Optional[int] = Field(default=None, index=True)
