# app/models/rollover.py
from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint

class RolloverAudit(SQLModel, table=True):
    __tablename__ = "rollover_audit"
    __table_args__ = (UniqueConstraint("from_season", "to_season", name="uq_rollover_from_to"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    from_season: int = Field(index=True)
    to_season: int = Field(index=True)
    seed_used: int = 0
    players_before: int = 0
    players_after: int = 0
    retired_count: int = 0
    snapshot_path_before: Optional[str] = None
    snapshot_path_after: Optional[str] = None
    notes: Optional[str] = None
