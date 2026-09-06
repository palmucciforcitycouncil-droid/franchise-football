# app/models/season_stats.py
from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint

class TeamSeasonStats(SQLModel, table=True):
    __tablename__ = "team_season_stats"
    __table_args__ = (UniqueConstraint("team_id", "season", name="uq_team_season"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    games: int = 0

    points_for: int = 0
    points_against: int = 0

    plays_offense: int = 0
    pass_attempts: int = 0
    rush_attempts: int = 0
    pass_yards: int = 0
    rush_yards: int = 0
    turnovers: int = 0
    sacks_allowed: int = 0
    penalties: int = 0
    penalty_yards: int = 0

    wins: int = 0
    losses: int = 0
    ties: int = 0

    @property
    def ppg(self) -> float:
        return self.points_for / self.games if self.games else 0.0

    @property
    def plays_per_game(self) -> float:
        return self.plays_offense / self.games if self.games else 0.0

    @property
    def pass_rate(self) -> float:
        total = self.pass_attempts + self.rush_attempts
        return (self.pass_attempts / total) if total else 0.0


class PlayerSeasonStats(SQLModel, table=True):
    __tablename__ = "player_season_stats"
    __table_args__ = (UniqueConstraint("player_id", "season", name="uq_player_season"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    team_id: Optional[int] = Field(default=None, index=True)
    season: int = Field(index=True)
    games: int = 0
    snaps: int = 0

    # Core offensive line:
    pass_attempts: int = 0
    completions: int = 0
    pass_yards: int = 0
    pass_tds: int = 0
    interceptions: int = 0

    rush_attempts: int = 0
    rush_yards: int = 0
    rush_tds: int = 0

    targets: int = 0
    receptions: int = 0
    recv_yards: int = 0
    recv_tds: int = 0

    fumbles: int = 0

    # Defense:
    tackles: int = 0
    sacks: float = 0.0  # allow half sacks
    tfl: int = 0
    qb_hits: int = 0
    interceptions_def: int = 0
    passes_defended: int = 0
    forced_fumbles: int = 0
    fumble_recoveries: int = 0
    defensive_tds: int = 0

    # Special Teams (subset):
    returns: int = 0
    return_yards: int = 0
    return_tds: int = 0
