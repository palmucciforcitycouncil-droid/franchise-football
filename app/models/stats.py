from __future__ import annotations

from typing import Optional

from sqlmodel import SQLModel, Field


class PlayerSeasonStats(SQLModel, table=True):
    """
    Minimal per-season player stats table used by tests/importers.
    Kept broad but simple to avoid over-coupling.
    """
    __tablename__ = "player_season_stats"

    id: Optional[int] = Field(default=None, primary_key=True)

    # keys
    player_id: int = Field(foreign_key="player.id", index=True)
    season: int = Field(index=True)
    team_id: Optional[int] = Field(default=None, foreign_key="team.id", index=True)

    # participation
    games: int = Field(default=0)
    starts: int = Field(default=0)

    # passing
    passing_yards: int = Field(default=0)
    passing_tds: int = Field(default=0)
    interceptions_thrown: int = Field(default=0)

    # rushing
    rushing_yards: int = Field(default=0)
    rushing_tds: int = Field(default=0)

    # receiving
    receptions: int = Field(default=0)
    receiving_yards: int = Field(default=0)
    receiving_tds: int = Field(default=0)

    # defense
    tackles: int = Field(default=0)
    sacks: int = Field(default=0)
    interceptions: int = Field(default=0)

    # misc
    fumbles: int = Field(default=0)
    fumbles_lost: int = Field(default=0)

    # kicking
    field_goals_made: int = Field(default=0)
    field_goals_att: int = Field(default=0)
    extra_points_made: int = Field(default=0)
    extra_points_att: int = Field(default=0)

    # aggregate
    points: int = Field(default=0)

