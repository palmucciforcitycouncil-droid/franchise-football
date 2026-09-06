from __future__ import annotations
from sqlmodel import SQLModel, Field

class DepthChart(SQLModel, table=True):
    __tablename__ = "depth_chart"
    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    position: str  # QB, RB, WR, etc.
    starter_player_id: int | None = Field(default=None, index=True)
    backup_player_id: int | None = Field(default=None, index=True)