from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class EventLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    event_type: str = Field(index=True)     # e.g., "GAME_FINAL", "SIGNING", "RELEASE", "AWARD_WEEKLY"
    team_id: Optional[int] = Field(default=None, index=True)     # primary subject team
    player_id: Optional[int] = Field(default=None, index=True)
    coach_id: Optional[int] = Field(default=None, index=True)
    game_id: Optional[int] = Field(default=None, index=True)
    payload_json: str = "{}"   # small JSON blob stringified
