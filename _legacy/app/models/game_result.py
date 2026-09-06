from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class GameResult(SQLModel, table=True):
    __tablename__ = "game_result"

    id: Optional[int] = Field(default=None, primary_key=True)

    season: int = Field(index=True)
    week: int = Field(index=True)

    home_team_id: int = Field(foreign_key="team.id", index=True)
    away_team_id: int = Field(foreign_key="team.id", index=True)

    home_score: int = Field(default=0)
    away_score: int = Field(default=0)

    # Winner can be derived, but keep a nullable column if other code wants to persist it
    winner_team_id: Optional[int] = Field(default=None, foreign_key="team.id", index=True)

    model_config = {"arbitrary_types_allowed": True}

    @property
    def winner(self) -> Optional[int]:
        if self.home_score == self.away_score:
            return None
        return self.home_team_id if self.home_score > self.away_score else self.away_team_id
