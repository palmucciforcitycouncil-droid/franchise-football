from __future__ import annotations
from pydantic import BaseModel, Field, conint, validator
from typing import List, Literal, Optional

Side = Literal["AFC", "NFC"]
RoundCode = Literal["WC", "DIV", "CONF", "SB"]

class TeamSeedDTO(BaseModel):
    team_id: conint(gt=0)
    seed: conint(ge=1, le=7)
    wins: int
    losses: int
    ties: int = 0
    power_rank: int = Field(1500, description="UI name; backed by power_rating (1000-2000)")
    team_name: str
    team_abbr: str
    logo_url: str | None = None

    @validator("power_rank")
    def _clamp_power_rank(cls, v: int) -> int:
        return max(1000, min(2000, v))

class MatchupDTO(BaseModel):
    game_id: conint(gt=0)
    round_name: RoundCode
    side: Optional[Side] = None  # None for SB
    higher_seed_team: TeamSeedDTO
    lower_seed_team: TeamSeedDTO
    home_team_id: int
    away_team_id: int
    winner_team_id: Optional[int] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None

class RoundDTO(BaseModel):
    round_name: RoundCode
    side: Optional[Side] = None
    matchups: List[MatchupDTO]

class InHuntCardDTO(BaseModel):
    side: Side
    team_id: int
    seed_if_made: conint(ge=6, le=7)
    gb: float  # games back from 7-seed
    team_name: str
    team_abbr: str
    logo_url: str | None = None

class PlayoffBracketDTO(BaseModel):
    season_year: int
    rounds: List[RoundDTO]
    in_the_hunt: List[InHuntCardDTO] = Field(default_factory=list)

