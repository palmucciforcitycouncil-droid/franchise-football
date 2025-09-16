from __future__ import annotations

from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, event
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from .database import Base


class GameResult(Base):
    __tablename__ = "game_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)

    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    winner_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )

    home_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])
    winner_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[winner_team_id])

    __table_args__ = (
        CheckConstraint("week >= 1", name="chk_week"),
        CheckConstraint("season >= 1900", name="chk_season"),
        CheckConstraint("home_team_id != away_team_id", name="chk_teams_distinct"),
        CheckConstraint("home_score >= 0 AND away_score >= 0", name="chk_nonnegative_scores"),
    )

    def __repr__(self) -> str:
        return f"<GameResult {self.season}-W{self.week} {self.home_team_id} vs {self.away_team_id} winner={self.winner_team_id}>"


def _validate_winner(gr: GameResult) -> None:
    if gr.winner_team_id is None:
        return
    if gr.winner_team_id not in (gr.home_team_id, gr.away_team_id):
        raise ValueError("winner_team_id must be either home_team_id or away_team_id (or NULL)")


@event.listens_for(Session, "before_flush")
def _game_result_before_flush(session: Session, flush_context, instances):
    for obj in list(session.new) + list(session.dirty):
        if isinstance(obj, GameResult):
            _validate_winner(obj)
