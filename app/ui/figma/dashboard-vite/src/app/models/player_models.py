"""
Player models for roster management.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class Player(SQLModel, table=True):
    """Player model."""
    __tablename__ = "players"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    position: str
    team_id: Optional[int] = Field(default=None, index=True)
    age: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
