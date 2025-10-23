"""
Player models for roster management.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class Player(SQLModel, table=False):  # <-- make DTO-only to avoid table registration
    """
    Legacy Player DTO (non-table).
    Deprecated: Use app.models.core_min.Player for DB operations.
    This class exists only to facilitate parsing and the compatibility layer.
    """
    # Keep legacy field names so the compat copier can map them.
    id: Optional[int] = Field(default=None)                # legacy may have used 'id'
    name: str                                              # legacy full name
    position: str                                          # legacy position code
    team_id: Optional[int] = None
    age: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # If the legacy model exposed any convenience properties, you may keep them;
    # they won't affect metadata because this class is not mapped to a table.
    @property
    def pos(self) -> str:
        return self.position
    @pos.setter
    def pos(self, v: str) -> None:
        self.position = v

    @property
    def full_name(self) -> str:
        return self.name
    @full_name.setter
    def full_name(self, v: str) -> None:
        self.name = v


class DepthChart(SQLModel, table=True):
    """Depth chart model."""
    __tablename__ = "depth_charts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    position: str
    depth: int
    player_id: int = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlayerInjury(SQLModel, table=True):
    """Player injury model."""
    __tablename__ = "player_injuries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    injury_type: str
    severity: str
    weeks_out: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
