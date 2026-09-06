"""
Playoff models for postseason management.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class PlayoffRound(SQLModel, table=True):
    """Playoff round model."""
    __tablename__ = "playoff_rounds"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    round_name: str
    round_number: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlayoffMatchup(SQLModel, table=True):
    """Playoff matchup model."""
    __tablename__ = "playoff_matchups"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    round_id: int = Field(index=True)
    home_team_id: int = Field(index=True)
    away_team_id: int = Field(index=True)
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
