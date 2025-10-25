from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class Standings(SQLModel, table=True):
    """Standings model for tracking team records and power ratings."""
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    team_id: int = Field(index=True)
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: int = 0
    points_against: int = 0
    division_wins: int = 0
    division_losses: int = 0
    conference_wins: int = 0
    conference_losses: int = 0
    sos: float = 0.0  # strength of schedule (MVP: rolling avg opp PR)
    power_rating: float = 1500.0  # our "Power Ranking" number

