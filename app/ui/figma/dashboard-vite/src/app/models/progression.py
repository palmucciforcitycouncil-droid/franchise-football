# app/models/progression.py
from __future__ import annotations
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, UniqueConstraint
import json

class PlayerProgression(SQLModel, table=True):
    __tablename__ = "player_progression"
    __table_args__ = (UniqueConstraint("player_id", "season", name="uq_player_season_progression"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    season: int = Field(index=True)

    # snapshots
    before_json: str  # JSON of core skill ratings before
    after_json: str   # JSON of core skill ratings after

    # components for auditability (age curve, potential factor, usage factor, awards, injury)
    components_json: str  # JSON dict of weights/inputs used

    # deterministic bookkeeping
    applied_at_ts: Optional[int] = Field(default=None, index=True)  # epoch seconds
    seed_used: Optional[int] = Field(default=None)

    @staticmethod
    def as_json(data: Dict[str, Any]) -> str:
        return json.dumps(data, separators=(",", ":"), sort_keys=True)
