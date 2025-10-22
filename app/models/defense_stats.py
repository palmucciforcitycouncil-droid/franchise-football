from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class TeamDefenseStatsWeekly(SQLModel, table=True):
    __tablename__ = "team_defense_stats_weekly"
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int
    week: int
    team_id: int

    tackles_solo: int = Field(default=0)
    tackles_ast: int = Field(default=0)
    tfl: int = Field(default=0)

    sacks: int = Field(default=0)
    qb_hits: int = Field(default=0)
    pressures: int = Field(default=0)
    blitzes: int = Field(default=0)

    interceptions: int = Field(default=0)
    int_yards: int = Field(default=0)
    int_td: int = Field(default=0)

    pbus: int = Field(default=0)  # pass breakups (PD)
    targets: int = Field(default=0)
    completions_allowed: int = Field(default=0)
    yards_allowed: int = Field(default=0)
    yac_allowed: int = Field(default=0)
    td_allowed: int = Field(default=0)

    forced_fumbles: int = Field(default=0)
    fumble_recoveries: int = Field(default=0)
    fr_yards: int = Field(default=0)
    fr_td: int = Field(default=0)

    penalties: int = Field(default=0)
    penalty_yards: int = Field(default=0)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

class PlayerDefenseStatsWeekly(SQLModel, table=True):
    __tablename__ = "player_defense_stats_weekly"
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int
    week: int
    team_id: int
    player_id: int  # allow synthetic or real

    role: str = Field(default="DB")  # DB/LB/DL (optional tag)

    tackles_solo: int = Field(default=0)
    tackles_ast: int = Field(default=0)
    tfl: int = Field(default=0)

    sacks: int = Field(default=0)
    qb_hits: int = Field(default=0)
    pressures: int = Field(default=0)
    blitzes: int = Field(default=0)

    interceptions: int = Field(default=0)
    int_yards: int = Field(default=0)
    int_td: int = Field(default=0)

    pbus: int = Field(default=0)
    targets: int = Field(default=0)
    completions_allowed: int = Field(default=0)
    yards_allowed: int = Field(default=0)
    yac_allowed: int = Field(default=0)
    td_allowed: int = Field(default=0)

    forced_fumbles: int = Field(default=0)
    fumble_recoveries: int = Field(default=0)
    fr_yards: int = Field(default=0)
    fr_td: int = Field(default=0)

    penalties: int = Field(default=0)
    penalty_yards: int = Field(default=0)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
