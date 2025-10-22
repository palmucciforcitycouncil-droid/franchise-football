from __future__ import annotations
from sqlmodel import SQLModel, Field
from typing import Optional

class PlayerContract(SQLModel, table=True):
    __tablename__ = "player_contract"
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    years: int = 1
    aav: int = 1000000  # avg annual value
    is_active: bool = True

class CapSummary(SQLModel, table=True):
    __tablename__ = "cap_summary"
    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(index=True, unique=True)
    cap_limit: int = 240_000_000
    committed: int = 0
