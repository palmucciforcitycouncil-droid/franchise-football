from __future__ import annotations

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.database import Base, create_db_and_tables
from app.models import (
    Team, Conference, Division, Player, DepthChart, GameResult, PlayerSeasonStats, UserProfile
)


@pytest.fixture
def memory_session() -> Session:
    """
    Fresh in-memory SQLite database per test function.
    """
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    return SessionLocal()


def make_team(session: Session, loc: str, nick: str, conf=Conference.AFC, div=Division.EAST) -> Team:
    t = Team(location_name=loc, nickname=nick, conference=conf, division=div, power_rating=60, cap_space=10_000_000)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def make_player(session: Session, team: Team, pos="QB", jersey=12, age=24, overrides=None) -> Player:
    data = dict(
        team_id=team.id,
        first_name="Test",
        last_name="Player",
        position=pos,
        jersey=jersey,
        age=age,
        salary=1_000_000,
        contract_years=1,
    )
    if overrides:
        data.update(overrides)
    p = Player(**data)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def test_create_db_and_tables_runs_without_error(tmp_path):
    """
    Ensure create_db_and_tables() can initialize a file-based SQLite DB with all tables.
    """
    db_path = tmp_path / "ff.db"
    url = f"sqlite:///{db_path}"
    create_db_and_tables(url)
    assert db_path.exists()


def test_team_player_insert_and_select(memory_session: Session):
    s = memory_session
    t = make_team(s, "Metro City", "Hawks", conf=Conference.NFC, div=Division.NORTH)
    p1 = make_player(s, t, pos="QB", jersey=7)
    p2 = make_player(s, t, pos="WR", jersey=11)

    players = s.query(Player).filter(Player.team_id == t.id).all()
    assert {p1.id, p2.id} == {p.id for p in players}


def test_player_attribute_validations(memory_session: Session):
    s = memory_session
    t = make_team(s, "Coast", "Sailors")
    # Age < 18 should fail fast via Python-side validator
    with pytest.raises(ValueError):
        make_player(s, t, age=17)
    # Out-of-range rating should fail fast
    with pytest.raises(ValueError):
        make_player(s, t, overrides={"speed": 101})
    # Boundary values should be accepted
    p = make_player(s, t, overrides={"morale": 0, "speed": 100})
    assert p.morale == 0 and p.speed == 100


def test_depth_chart_same_team_ok(memory_session: Session):
    s = memory_session
    t = make_team(s, "River", "Kings")
    qb1 = make_player(s, t, pos="QB", jersey=1)
    qb2 = make_player(s, t, pos="QB", jersey=2)

    dc = DepthChart(team_id=t.id, position="QB", starter_player_id=qb1.id, backup_player_id=qb2.id)
    s.add(dc)
    s.commit()  # should not raise
    assert s.query(DepthChart).count() == 1


def test_depth_chart_cross_team_rejected(memory_session: Session):
    s = memory_session
    t1 = make_team(s, "North", "Bears")
    t2 = make_team(s, "South", "Sharks")
    qb1 = make_player(s, t1, pos="QB", jersey=3)
    qb_other = make_player(s, t2, pos="QB", jersey=9)

    dc = DepthChart(team_id=t1.id, position="QB", starter_player_id=qb1.id, backup_player_id=qb_other.id)
    s.add(dc)
    with pytest.raises(ValueError, match="backup_player must belong to the same team"):
        s.commit()
    s.rollback()


def test_game_result_fk_and_winner_behavior(memory_session: Session):
    s = memory_session
    home = make_team(s, "Alpha", "Wolves")
    away = make_team(s, "Beta", "Eagles")

    gr = GameResult(week=1, season=2025, home_team_id=home.id, away_team_id=away.id, home_score=0, away_score=0)
    s.add(gr)
    s.commit()
    s.refresh(gr)
    assert gr.winner_team_id is None  # initially unset

    # Set a valid winner later
    gr.winner_team_id = home.id
    s.add(gr)
    s.commit()
    s.refresh(gr)
    assert gr.winner_team_id == home.id

    # Invalid winner (neither home nor away) shoul
