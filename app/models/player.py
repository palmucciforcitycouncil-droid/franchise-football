from __future__ import annotations

from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    first_name: Mapped[str] = mapped_column(String(32), nullable=False, default="John")
    last_name: Mapped[str] = mapped_column(String(32), nullable=False, default="Doe")
    position: Mapped[str] = mapped_column(String(4), nullable=False, index=True)  # e.g., QB, RB, WR, TE, LB …
    jersey: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    age: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    salary: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contract_years: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Ratings 0-100
    speed: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    strength: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    agility: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    throw_power: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    throw_accuracy: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    catching: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    tackling: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    awareness: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    potential: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    stamina: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    injury_proneness: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    morale: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    team: Mapped[Optional["Team"]] = relationship(back_populates="players")

    __table_args__ = (
        CheckConstraint("age >= 18", name="chk_player_age"),
        CheckConstraint("speed BETWEEN 0 AND 100", name="chk_speed"),
        CheckConstraint("strength BETWEEN 0 AND 100", name="chk_strength"),
        CheckConstraint("agility BETWEEN 0 AND 100", name="chk_agility"),
        CheckConstraint("throw_power BETWEEN 0 AND 100", name="chk_throw_power"),
        CheckConstraint("throw_accuracy BETWEEN 0 AND 100", name="chk_throw_accuracy"),
        CheckConstraint("catching BETWEEN 0 AND 100", name="chk_catching"),
        CheckConstraint("tackling BETWEEN 0 AND 100", name="chk_tackling"),
        CheckConstraint("awareness BETWEEN 0 AND 100", name="chk_awareness"),
        CheckConstraint("potential BETWEEN 0 AND 100", name="chk_potential"),
        CheckConstraint("stamina BETWEEN 0 AND 100", name="chk_stamina"),
        CheckConstraint("injury_proneness BETWEEN 0 AND 100", name="chk_injury_proneness"),
        CheckConstraint("morale BETWEEN 0 AND 100", name="chk_morale"),
    )

    # Python-side validations (fail fast before DB)
    @validates(
        "speed", "strength", "agility", "throw_power", "throw_accuracy",
        "catching", "tackling", "awareness", "potential", "stamina",
        "injury_proneness", "morale"
    )
    def _validate_rating(self, key: str, value: int) -> int:
        if not (0 <= int(value) <= 100):
            raise ValueError(f"{key} must be 0..100 (got {value})")
        return int(value)

    @validates("age")
    def _validate_age(self, key: str, value: int) -> int:
        if int(value) < 18:
            raise ValueError("age must be >= 18")
        return int(value)
