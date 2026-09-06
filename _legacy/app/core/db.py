from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator

from sqlmodel import SQLModel, Session, create_engine
from fastapi import Depends

DATABASE_URL = "sqlite:///./franchise.db"
engine = create_engine(DATABASE_URL, echo=False)

def create_db_and_tables() -> None:
    from app.models.sim_models import Team, Game, GameEvent  # noqa: F401
    from app.models.stats import PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats, PlayerCareerStats  # noqa: F401
    from app.models.defense_stats import TeamDefenseStatsWeekly, PlayerDefenseStatsWeekly  # noqa: F401
    from app.models.results import TeamGameStats, PlayerBox  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session() -> Iterator[Session]:
    with Session(engine) as s:
        yield s

@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as s:
        yield s
