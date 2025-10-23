# app/api/dto.py
from __future__ import annotations
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

AwardName = Literal["MVP", "OPOY", "DPOY", "ROY", "COY", "GMOY"]

class AwardItem(BaseModel):
    rank: int
    player_id: Optional[int] = None
    team_id: Optional[int] = None
    player_name: Optional[str] = None
    team_abbr: Optional[str] = None
    position: Optional[str] = None
    score: float
    tiebreaker: str

class AwardResponse(BaseModel):
    season: int
    award: AwardName
    top: List[AwardItem] = Field(default_factory=list)

class AwardsAllResponse(BaseModel):
    season: int
    awards: List[AwardResponse] = Field(default_factory=list)

class TeamSeasonStatsRead(BaseModel):
    team_id: int
    season: int
    games: int
    points_for: int
    points_against: int
    plays_offense: int
    pass_attempts: int
    rush_attempts: int
    pass_yards: int
    rush_yards: int
    turnovers: int
    sacks_allowed: int
    penalties: int
    penalty_yards: int
    wins: int
    losses: int
    ties: int
    ppg: float
    plays_per_game: float
    pass_rate: float

class PlayerSeasonStatsRead(BaseModel):
    player_id: int
    team_id: Optional[int]
    season: int
    games: int
    snaps: int
    pass_attempts: int
    completions: int
    pass_yards: int
    pass_tds: int
    interceptions: int
    rush_attempts: int
    rush_yards: int
    rush_tds: int
    targets: int
    receptions: int
    recv_yards: int
    recv_tds: int
    fumbles: int
    tackles: int
    sacks: float
    tfl: int
    qb_hits: int
    interceptions_def: int
    passes_defended: int
    forced_fumbles: int
    fumble_recoveries: int
    defensive_tds: int
    returns: int
    return_yards: int
    return_tds: int

class LeagueSummary(BaseModel):
    season: int
    teams: int
    games_counted: int
    league_ppg: float
    plays_per_game: float
    pass_rate: float
