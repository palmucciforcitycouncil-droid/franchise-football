"""
Coach models for coaching staff management.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class Coach(SQLModel, table=True):
    """Coach model."""
    __tablename__ = "coaches"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    team_id: Optional[int] = Field(default=None, index=True)
    position: str  # HC, OC, DC, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
