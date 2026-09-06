from __future__ import annotations
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field

class PlayerOfferStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RESCINDED = "RESCINDED"
    CONSUMMATED = "CONSUMMATED"  # accepted -> signed

class PlayerOffer(SQLModel, table=True):
    """Player offer model for tracking contract offers to free agents."""
    offer_id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    from_team_id: int = Field(index=True)
    to_player_id: int = Field(index=True)
    years: int
    aav: int
    status: PlayerOfferStatus = PlayerOfferStatus.ACTIVE

