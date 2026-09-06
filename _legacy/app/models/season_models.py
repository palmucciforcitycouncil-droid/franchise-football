from __future__ import annotations
from sqlmodel import SQLModel, Field
from typing import Literal

class Season(SQLModel, table=True):
    __tablename__ = "season"
    season: int = Field(primary_key=True)
    current_week: int = 1
    phase: str = "regular"  # preseason, regular, playoffs, offseason
    seed: int = 2025
