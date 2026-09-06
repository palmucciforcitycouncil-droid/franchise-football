from __future__ import annotations
from typing import Optional, Literal
from enum import Enum
from sqlmodel import SQLModel, Field
from datetime import datetime

class TradeItemType(str, Enum):
    PLAYER = "PLAYER"
    PICK = "PICK"

class TradeStatus(str, Enum):
    OPEN = "OPEN"
    COUNTERED = "COUNTERED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"

class DraftPick(SQLModel, table=True):
    """Draft pick model for trade system."""
    pick_id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    round: int = Field(index=True)
    overall_slot_hint: Optional[int] = None  # optional for future

class TradeProposal(SQLModel, table=True):
    """Trade proposal model tracking the overall trade."""
    trade_id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    from_team_id: int = Field(index=True)
    to_team_id: int = Field(index=True)

    status: TradeStatus = TradeStatus.OPEN
    round_num: int = 0  # how many back-and-forths so far (AI caps at 2)
    from_value_total: int = 0
    to_value_total: int = 0
    fair_margin: int = 0  # signed diff (from_team gives - receives)

class TradeItem(SQLModel, table=True):
    """Individual items in a trade (players or picks)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    trade_id: int = Field(index=True)
    side: Literal["FROM","TO"]  # items offered by from_team ("FROM") or by to_team ("TO")
    item_type: TradeItemType
    player_id: Optional[int] = None
    pick_id: Optional[int] = None

