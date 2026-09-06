from __future__ import annotations
from typing import Optional
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field

class InjuryStatus(str, Enum):
    OUT = "OUT"
    DOUBTFUL = "DOUBTFUL"
    QUESTIONABLE = "QUESTIONABLE"
    PROBABLE = "PROBABLE"
    ACTIVE = "ACTIVE"

class InjuryType(str, Enum):
    # MVP catalog (expand later)
    HAMSTRING = "HAMSTRING"
    ANKLE_SPR = "ANKLE_SPR"
    ACL_TEAR = "ACL_TEAR"
    MCL_SPR = "MCL_SPR"
    SHOULDER = "SHOULDER"
    CONCUSSION = "CONCUSSION"
    HAND = "HAND"
    GROIN = "GROIN"
    BACK = "BACK"
    FOOT = "FOOT"

class Injury(SQLModel, table=True):
    """Injury tracking model with comprehensive injury data."""
    injury_id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int = Field(index=True)     # week when injury occurred
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    injury_type: InjuryType
    severity: int = 1                 # 1-10 scale
    weeks_out_total: int = 0          # total prognosis
    weeks_out_remaining: int = 0      # decremented on week advance
    rtp_penalty_overall: float = 0.0  # temporary OV penalty on return
    rtp_penalty_pos: float = 0.0      # additional positional penalty
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = Field(default=False, index=True)
    placed_on_ir: bool = False
    status: InjuryStatus = InjuryStatus.OUT

