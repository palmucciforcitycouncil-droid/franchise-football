from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class PlayoffBracket(SQLModel, table=True):
    """Playoff bracket model for storing playoff seeds."""
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True, unique=True)
    afc_seeds_csv: str = ""  # "1,2,3,4,5,6,7" team_ids in seed order
    nfc_seeds_csv: str = ""

