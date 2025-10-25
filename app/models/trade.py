from __future__ import annotations
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field, Column, JSON

class TradeStatus(str, Enum):
    PENDING = "PENDING"
    COUNTER = "COUNTER"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class TradeProposal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    from_team_id: int = Field(index=True)   # initiator
    to_team_id: int = Field(index=True)     # counterparty
    # Assets as JSON arrays: {"players":[ids...], "picks":[{"round":1,"slot":3}]}
    from_assets: dict = Field(sa_column=Column(JSON))
    to_assets: dict = Field(sa_column=Column(JSON))
    # Cached valuation for transparency
    from_value: float = 0.0   # value leaving from_team
    to_value: float = 0.0     # value leaving to_team
    # Decision state
    status: TradeStatus = Field(default=TradeStatus.PENDING, index=True)
    message: str = ""         # reason/notes
