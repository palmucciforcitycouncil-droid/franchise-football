from __future__ import annotations
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field

class TradeBlockItemType(str, Enum):
    PLAYER = "PLAYER"
    PICK = "PICK"

class TeamTradeBlock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    team_id: int = Field(index=True)
    item_type: TradeBlockItemType = Field(default=TradeBlockItemType.PLAYER, index=True)
    player_id: Optional[int] = Field(default=None, index=True)
    round: Optional[int] = Field(default=None, index=True)
    slot: Optional[int] = Field(default=None, index=True)
    note: str = ""
