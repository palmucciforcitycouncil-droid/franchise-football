from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class GameplanTrace(SQLModel, table=True):
    """
    Stores the applied gameplan configuration for each team in a game.
    Contains raw components and final applied config for debugging.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    team_id: int = Field(index=True)
    opponent_team_id: int = Field(index=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Raw components (serialized compact JSON strings for debug)
    hc: str = ""          # json of HC influence inputs/outputs
    focus: str = ""       # json of CoachFocus bundle
    user: str = ""        # json of User Gameplan deltas
    # Final applied config snapshot
    final_cfg: str = ""   # json of the final EngineConfig after application

