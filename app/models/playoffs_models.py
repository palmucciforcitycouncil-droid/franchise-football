from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class PlayoffRound(SQLModel, table=True):
    __tablename__ = "playoff_round"
    id: int | None = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    round_name: str  # 'WC' | 'DIV' | 'CONF' | 'SB'
    side: Optional[str] = None  # None for SB, "AFC" or "NFC"

class PlayoffMatchup(SQLModel, table=True):
    __tablename__ = "playoff_matchup"
    id: int | None = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    round_name: str
    side: Optional[str] = None
    higher_seed_team: int
    lower_seed_team: int
    higher_seed_score: Optional[int] = None
    lower_seed_score: Optional[int] = None
    is_complete: bool = False
    winner_team_id: Optional[int] = None
