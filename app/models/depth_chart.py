from __future__ import annotations
from typing import Optional

from sqlmodel import SQLModel, Field
from sqlalchemy import event
from sqlalchemy.orm import Session as SASession

from app.models.player import Player

class DepthChart(SQLModel, table=True):
    __tablename__ = "depth_chart"

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", nullable=False)
    position: str = Field(nullable=False)

    starter_player_id: int = Field(foreign_key="player.id", nullable=False)
    backup_player_id: Optional[int] = Field(default=None, foreign_key="player.id")

@event.listens_for(SASession, "before_flush")
def _validate_depth_chart_teams(session: SASession, flush_context, instances):
    for obj in session.new.union(session.dirty):
        if isinstance(obj, DepthChart):
            starter = session.get(Player, obj.starter_player_id) if obj.starter_player_id else None
            backup  = session.get(Player, obj.backup_player_id)  if obj.backup_player_id  else None
            if starter and starter.team_id != obj.team_id:
                raise ValueError("starter_player must belong to the same team")
            if backup and backup.team_id != obj.team_id:
                raise ValueError("backup_player must belong to the same team")
