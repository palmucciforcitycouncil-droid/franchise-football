# app/models/awards.py
from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint

class AwardResult(SQLModel, table=True):
    """
    Persisted, ranked award results. Idempotent for (season, award).
    If player_id is set, it's a player award. If team_id is set, it's a team award.
    """
    __tablename__ = "award_results"
    __table_args__ = (UniqueConstraint("season", "award", "rank", name="uq_award_rank"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    award: str = Field(index=True)  # MVP, OPOY, DPOY, ROY, COY, GMOY
    rank: int = Field(index=True)  # 1..N (we store top 5)

    player_id: Optional[int] = Field(default=None, index=True)
    team_id: Optional[int] = Field(default=None, index=True)

    # Snapshot values (for fast UI; avoid joins in simple views)
    player_name: Optional[str] = None
    team_abbr: Optional[str] = None
    position: Optional[str] = None

    # Deterministic score used for ranking
    score: float = 0.0

    # Tie-breaker snapshot for auditability
    tiebreaker: str = ""  # e.g., "games,team_wins,player_id"

    def is_player_award(self) -> bool:
        return self.player_id is not None