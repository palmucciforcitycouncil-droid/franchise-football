from __future__ import annotations
from typing import Optional

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer
from pydantic import field_validator
from pydantic import field_validator, model_validator
from pydantic import field_validator
from pydantic import model_validator
from pydantic import field_validator

# Note: keep FK target singular: "team.id"
class Player(SQLModel, table=True):
    __tablename__ = "player"

    # Identity
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", nullable=False)
    first_name: Optional[str] = None
    last_name: str = "Player"
    position: str = "QB"
    # Make jersey always an int for DTOs
    jersey_number: int = Field(default=0, sa_column=Column("jersey", Integer, nullable=False, server_default="0"))

    # Core ratings (0–99) with hard bounds so validation raises on construct
    speed: int = 50
    strength: int = 50
    agility: int = 50
    throw_power: int = 50
    throw_accuracy: int = 50
    catching: int = 50
    tackling: int = 50
    awareness: int = 50
    potential: int = 50
    # Age must be between 18 and 55 — fails fast
    age: int = 22
    stamina: int = 50
    injury_proneness: int = 50
    morale: int = 50
    # Ensure tests see a plain ValueError on bad age at construction time
    @model_validator(mode="after")
    def _age_check_after(self):
        a = getattr(self, "age", None)
        if a is None:
            return self
        if a < 18:
            raise ValueError("age must be at least 18")
        if a > 55:
            raise ValueError("age unrealistic (>55)")
        return self
    # --- Pre-validators: raise ValueError at construction time (no session state involved) ---
    _rating_fields = (
        "speed","strength","agility","throw_power","throw_accuracy",
        "catching","tackling","awareness","potential",
        "stamina","injury_proneness","morale"
    )

    @classmethod
    @field_validator("age", mode="before")
    def _age_pre(cls, v):
        if v is None:
            return v
        if v < 18:
            raise ValueError("age must be at least 18")
        if v > 55:
            raise ValueError("age unrealistic (>55)")
        return v

    @classmethod
    @field_validator(*_rating_fields, mode="before")
    def _ratings_pre(cls, v):
        if v is None:
            return v
        if not isinstance(v, int):
            raise ValueError("rating must be an int")
        if v < 0 or v > 100:
            raise ValueError("rating out of bounds (0..100)")
        return v
    # ---- Constructor pre-guard so tests get a plain ValueError immediately ----
    def __init__(self, *args, **kwargs):
        age = kwargs.get("age", None)
        if age is not None and age < 18:
            raise ValueError("age must be at least 18")
        if age is not None and age > 55:
            raise ValueError("age unrealistic (>55)")
        super().__init__(*args, **kwargs)
    # ---- Assignment guard so post-construct overrides also raise ValueError ----
    def __setattr__(self, name, value):
        rating_fields = {
            "speed","strength","agility","throw_power","throw_accuracy",
            "catching","tackling","awareness","potential",
            "stamina","injury_proneness","morale"
        }
        if name == "age" and value is not None:
            if value < 18:
                raise ValueError("age must be at least 18")
            if value > 55:
                raise ValueError("age unrealistic (>55)")
        elif name in rating_fields and value is not None:
            if not isinstance(value, int):
                raise ValueError(f"{name} must be an int")
            if value < 0 or value > 100:  # 0..100 inclusive; 101 should fail
                raise ValueError(f"{name} out of bounds (0..100)")
        super().__setattr__(name, value)
    # DTO convenience properties (read-only)
    @property
    def jersey(self) -> int:
        return self.jersey_number

    @property
    def salary(self) -> int:
        # MVP: yearly salary only; 0 by default (GDD §5.1).
        return 0

    @property
    def contract_years(self) -> int:
        # MVP prior = 2 years; satisfies DTO field presence.
        return 2

# --- SQLAlchemy session-level guard so tests get a plain ValueError ---



def _validate_player_age(session: SASession, flush_context, instances):
    for obj in session.new.union(session.dirty):
        if isinstance(obj, Player):
            a = getattr(obj, "age", None)
            if a is not None and a < 18:
                raise ValueError("age must be at least 18")
            if a is not None and a > 55:
                raise ValueError("age unrealistic (>55)")
# --- SQLAlchemy session-level guards (raise ValueError and expunge offenders) ---


def _rating_fields():
    return ("speed","strength","agility","throw_power","throw_accuracy",
            "catching","tackling","awareness","potential",
            "stamina","injury_proneness","morale")


def _validate_player_constraints(session: SASession, flush_context, instances):
    for obj in session.new.union(session.dirty):
        if isinstance(obj, Player):
            # Age bounds
            a = getattr(obj, "age", None)
            if a is not None and a < 18:
                session.expunge(obj)
                raise ValueError("age must be at least 18")
            if a is not None and a > 55:
                session.expunge(obj)
                raise ValueError("age unrealistic (>55)")

            # Ratings 0..100 (allow 100; reject 101+ / negatives)
            for fname in _rating_fields():
                v = getattr(obj, fname, None)
                if v is None:
                    continue
                if not isinstance(v, int):
                    session.expunge(obj)
                    raise ValueError(f"{fname} must be an int")
                if v < 0 or v > 100:
                    session.expunge(obj)
                    raise ValueError(f"{fname} out of bounds (0..100)")




