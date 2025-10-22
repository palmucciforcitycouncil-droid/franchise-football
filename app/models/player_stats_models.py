from __future__ import annotations
from sqlmodel import SQLModel, Field
from typing import Optional

class PlayerGameStats(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    game_id: int = Field(index=True)
    team_id: int = Field(index=True)
    player_id: int = Field(index=True)
    pos: str = Field(index=True)

    # QB
    pass_cmp: int = 0
    pass_att: int = 0
    pass_yds: int = 0
    pass_td: int = 0
    pass_int: int = 0

    # Rushing
    rush_att: int = 0
    rush_yds: int = 0
    rush_td: int = 0

    # Receiving
    rec_tgt: int = 0
    rec_rec: int = 0
    rec_yds: int = 0
    rec_td: int = 0

    # Kicking / Punting
    fg_m: int = 0
    fg_a: int = 0
    xp_m: int = 0
    xp_a: int = 0
    punts: int = 0
    punt_yds: int = 0

