from __future__ import annotations

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _zero() -> int:
    return 0


class PlayerSeasonStats(Base):
    __tablename__ = "player_season_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic counters (default 0)
    games: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    snaps: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)

    # Passing
    pass_att: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    pass_cmp: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    pass_yds: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    pass_td: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    pass_int: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)

    # Rushing
    rush_att: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    rush_yds: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    rush_td: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)

    # Receiving
    rec_tgt: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    rec_rec: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    rec_yds: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    rec_td: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)

    # Defense
    def_tkl: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    def_sack: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)
    def_int: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)

    # Special Teams
    st_tkl: Mapped[int] = mapped_column(Integer, nullable=False, default=_zero)

    team: Mapped["Team"] = relationship()
    player: Mapped["Player"] = relationship()
