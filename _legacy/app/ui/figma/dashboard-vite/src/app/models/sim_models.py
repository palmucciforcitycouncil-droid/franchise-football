"""
Simulation models for games, teams, and basic entities.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class SimTeam(SQLModel, table=True):
    """Team model for simulation."""
    __tablename__ = "sim_teams"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    city: str
    conference: str
    division: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SimGame(SQLModel, table=True):
    """Game model for simulation."""
    __tablename__ = "sim_games"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int
    game_type: str = Field(default="regular")  # regular, playoffs, super_bowl
    home_team_id: int = Field(index=True)
    away_team_id: int = Field(index=True)
    home_score: int = Field(default=0)
    away_score: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SimGameEvent(SQLModel, table=True):
    """Game event model for simulation."""
    __tablename__ = "sim_game_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    event_type: str
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
