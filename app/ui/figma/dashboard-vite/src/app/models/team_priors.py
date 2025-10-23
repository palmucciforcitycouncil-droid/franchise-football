from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class TeamPriors(SQLModel, table=True):
    __tablename__ = "team_priors"
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    team_id: int = Field(index=True)
    off_epa_mod: float = 0.0
    def_stop_mod: float = 0.0
    third_down_mod: float = 0.0
    red_zone_td_mod: float = 0.0
    pressure_mod: float = 0.0
    fg_make_mod: float = 0.0
    punt_net_mod: float = 0.0
    turnover_mod: float = 0.0
