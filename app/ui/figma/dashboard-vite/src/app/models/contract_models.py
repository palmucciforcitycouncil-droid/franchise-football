"""
Contract models for salary cap management.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class PlayerContract(SQLModel, table=True):
    """Player contract model."""
    __tablename__ = "player_contracts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    salary: int
    years: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CapSummary(SQLModel, table=True):
    """Salary cap summary model."""
    __tablename__ = "cap_summaries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    total_cap: int
    used_cap: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
