from __future__ import annotations
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional

class Coach(SQLModel, table=True):
    __tablename__ = "coach"
    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    name: str
    run_bias: float = 0.5     # 0..1 (0 pass-heavy, 1 run-heavy)
    aggression: float = 0.5   # 0..1
    pace: float = 0.5         # 0..1
