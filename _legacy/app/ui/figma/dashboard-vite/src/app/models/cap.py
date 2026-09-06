# app/models/cap.py
from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint

class TeamCap(SQLModel, table=True):
    __tablename__ = "team_cap"
    __table_args__ = (UniqueConstraint("team_id","season", name="uq_team_cap"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    cap_limit: int = 2000
    cap_used: int = 0


