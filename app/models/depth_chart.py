from __future__ import annotations

from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from .database import Base


class DepthChart(Base):
    __tablename__ = "depth_charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(4), nullable=False, index=True)

    starter_player_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True
    )
    backup_player_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True
    )

    team: Mapped["Team"] = relationship(back_populates="depth_charts")
    starter_player: Mapped[Optional["Player"]] = relationship(foreign_keys=[starter_player_id])
    backup_player: Mapped[Optional["Player"]] = relationship(foreign_keys=[backup_player_id])

    __table_args__ = (
        UniqueConstraint("team_id", "position", name="uq_team_position"),
        CheckConstraint(
            "starter_player_id IS NULL OR starter_player_id != backup_player_id",
            name="chk_distinct_starter_backup",
        ),
    )

    def __repr__(self) -> str:
        return f"<DepthChart team={self.team_id} pos={self.position} starter={self.starter_player_id} backup={self.backup_player_id}>"


def _validate_depth_chart(dc: DepthChart, session: Session) -> None:
    """Enforce that starter/backup belong to the same team as this DepthChart row."""
    if dc.starter_player_id is None and dc.backup_player_id is None:
        return

    if dc.starter_player_id and dc.backup_player_id and dc.starter_player_id == dc.backup_player_id:
        raise ValueError("starter and backup cannot be the same player")

    from .player import Player

    if dc.starter_player_id is not None:
        starter = session.get(Player, dc.starter_player_id)
        if starter is None or starter.team_id != dc.team_id:
            raise ValueError("starter_player must belong to the same team as the depth chart row")

    if dc.backup_player_id is not None:
        backup = session.get(Player, dc.backup_player_id)
        if backup is None or backup.team_id != dc.team_id:
            raise ValueError("backup_player must belong to the same team as the depth chart row")


@event.listens_for(Session, "before_flush")
def _depth_chart_before_flush(session: Session, flush_context, instances):
    for obj in list(session.new) + list(session.dirty):
        if isinstance(obj, DepthChart):
            _validate_depth_chart(obj, session)
