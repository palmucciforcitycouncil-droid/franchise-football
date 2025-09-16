from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List

from sqlalchemy import CheckConstraint, Enum as SAEnum, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Conference(str, Enum):
    AFC = "AFC"
    NFC = "NFC"


class Division(str, Enum):
    EAST = "East"
    NORTH = "North"
    SOUTH = "South"
    WEST = "West"


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_name: Mapped[str] = mapped_column(String(64), nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False, default="Generics")
    conference: Mapped[Conference] = mapped_column(SAEnum(Conference, validate_strings=True), nullable=False)
    division: Mapped[Division] = mapped_column(SAEnum(Division, validate_strings=True), nullable=False)

    power_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    cap_space: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    players: Mapped[List["Player"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    depth_charts: Mapped[List["DepthChart"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("location_name", "nickname", name="uq_team_name"),
        CheckConstraint("power_rating BETWEEN 0 AND 100", name="chk_team_power_rating"),
    )

    def __repr__(self) -> str:
        return f"<Team id={self.id} {self.location_name} {self.nickname} {self.conference}-{self.division}>"
