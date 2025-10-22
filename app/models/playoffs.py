from __future__ import annotations
from pydantic import BaseModel, Field, conint
from typing import List, Literal, Optional

Side = Literal["AFC","NFC"]

class TeamSeed(BaseModel):
    team_id: conint(gt=0)
    seed: conint(ge=1, le=7)
    wins: int = 0
    losses: int = 0
    power_rating: int = 1500  # UI "Power Ranking" baseline
    team_name: str
    team_abbr: str
    logo_url: str | None = None

class Matchup(BaseModel):
    game_id: conint(gt=0)
    round_name: Literal["WC","DIV","CONF","SB"]
    side: Optional[Side] = None  # None for SB
    higher_seed_team: TeamSeed
    lower_seed_team: TeamSeed
    home_team_id: int
    away_team_id: int
    winner_team_id: Optional[int] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None

class Round(BaseModel):
    round_name: Literal["WC","DIV","CONF","SB"]
    side: Optional[Side] = None
    matchups: List[Matchup]

class InHuntCard(BaseModel):
    side: Side
    team_id: int
    seed_if_made: conint(ge=6, le=7)
    gb: float  # games back from 7-seed

class PlayoffBracket(BaseModel):
    season_year: int
    rounds: List[Round]
    in_the_hunt: List[InHuntCard] = Field(default_factory=list)