from __future__ import annotations
from typing import Optional, Literal
from sqlmodel import SQLModel, Field

# Depth chart slots we support (MVP NFL-ish)
# Offense: QB, RB, WR1-3, TE, LT, LG, C, RG, RT
# Defense: EDGE1-2, DL1-2, LB1-2, CB1-2, S1-2
# Special: K, P, LS, KR, PR

class DepthChart(SQLModel, table=True):
    """Depth chart model for tracking team lineups and depth."""
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    slot: str = Field(index=True)          # e.g., "QB", "WR2", "CB1", "KR"
    order_index: int = 0                   # 0 = starter, 1 = backup, 2 ...
    player_id: Optional[int] = Field(default=None, index=True)

