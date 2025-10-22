"""
Season models for league management.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class Season(SQLModel, table=True):
    """Season model."""
    __tablename__ = "seasons"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    year: int = Field(index=True, unique=True)
    status: str = Field(default="active")  # active, completed, upcoming
    created_at: datetime = Field(default_factory=datetime.utcnow)
