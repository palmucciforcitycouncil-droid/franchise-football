from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class TeamGameStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    points: int = 0
    yards_offense: int = 0
    pass_yds: int = 0
    rush_yds: int = 0
    takeaways: int = 0
    giveaways: int = 0
    sacks: int = 0
    third_down_pct: float = 0.0
    red_zone_td_pct: float = 0.0
    time_of_possession_sec: int = 0
    # Special-teams / misc you can fill later

class PlayerBox(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    team_id: int = Field(index=True)
    opponent_id: int = Field(index=True)
    player_id: int = Field(index=True)
    pos: str = ""
    # Offense
    pass_att: int = 0
    pass_cmp: int = 0
    pass_yds: int = 0
    pass_td: int = 0
    pass_int: int = 0
    rush_att: int = 0
    rush_yds: int = 0
    rush_td: int = 0
    rec_tgt: int = 0
    rec_rec: int = 0
    rec_yds: int = 0
    rec_td: int = 0
    # Defense
    tkl: int = 0
    tfl: int = 0
    sack: float = 0.0
    pdef: int = 0
    ints: int = 0
    ff: int = 0
    fr: int = 0
    # ST / Kicking (minimal)
    fgm: int = 0
    fga: int = 0
    xpm: int = 0
    xpa: int = 0
    kr_yds: int = 0
    pr_yds: int = 0
    # Participation
    snap_pct: float = 0.0
