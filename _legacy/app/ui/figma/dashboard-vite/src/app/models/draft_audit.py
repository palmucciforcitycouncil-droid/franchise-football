# app/models/draft_audit.py
from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint

class ProspectProgressAudit(SQLModel, table=True):
    """
    Minimal per-season snapshot for sparkline/history.
    Idempotent: one row per (season, prospect_id).
    """
    __tablename__ = "prospect_progress_audit"
    __table_args__ = (UniqueConstraint("season", "prospect_id", name="uq_pprogress_season_prospect"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)          # the rollover target season (e.g., advancing into this season)
    prospect_id: int = Field(index=True)
    pos: str = Field(default="", index=True)
    class_year: str = Field(default="FR", index=True)
    age: int = 0
    ovr_before: int = 0
    ovr_after: int = 0


