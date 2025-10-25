from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class PlayerContract(SQLModel, table=True):
    """Player contract model for tracking contract details."""
    contract_id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    start_season: int
    end_season: int
    aav: int
    guaranteed: int = 0
    is_active: bool = Field(default=True, index=True)

class PlayerContractAsk(SQLModel, table=True):
    """Player contract ask model for tracking desired contract terms."""
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True, unique=True)
    updated_season: int = 0
    desired_years: int = 3
    desired_aav: int = 3_000_000

class TeamTradeBlock(SQLModel, table=True):
    """Trade block model for tracking players available for trade."""
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    team_id: int = Field(index=True)
    player_id: int = Field(index=True)
    reason: str = "Expiring/Not re-signing"