from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.ui.api import app
from app.models.database import Base, get_session
from app.models import Team, Player, DepthChart, GameResult, Conference, Division


@pytest.fixture(scope="function")
def client():
    # Single in-memory DB shared across threads
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    # Seed data using a one-off session in the main thread
    with SessionLocal() as s:
        t1 = Team(location_name="Testville", nickname="Generics",
                  conference=Conference.AFC, division=Division.EAST,
                  power_rating=55, cap_space=1_000_000)
        t2 = Team(location_name="Other", nickname="Guys",
                  conference=Conference.NFC, division=Division.WEST,
                  power_rating=50, cap_space=0)
        s.add_all([t1, t2]); s.commit(); s.refresh(t1); s.refresh(t2)

        p1 = Player(team_id=t1.id, first_name="Alice", last_name="QB",
                    position="QB", jersey=1, age=24, salary=500_000, contract_years=1)
        p2 = Player(team_id=t1.id, first_name="Bob", last_name="WR",
                    position="WR", jersey=11, age=25, salary=400_000, contract_years=1)
        s.add_all([p1, p2]); s.commit(); s.refresh(p1); s.refresh(p2)

        dc = DepthChart(team_id=t1.id, position="QB", starter_player_id=p1.id, backup_player_id=None)
        s.add(dc); s.commit()

        g = GameResult(week=1, season=2025, home_team_id=t1.id, away_team_id=t2.id,
                       home_score=0, away_score=0)
        s.add(g); s.commit()

    # Override dependency to yield a *new* session per request/thread
    def _override_get_session():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = _override_get_session
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert isinstance(data.get("version"), str)


def test_list_teams_and_get_team(client: TestClient):
    r = client.get("/teams")
    assert r.status_code == 200
    teams = r.json()
    assert len(teams) == 2
    tid = teams[0]["id"]
    r2 = client.get(f"/teams/{tid}")
    assert r2.status_code == 200
    assert "location_name" in r2.json()


def test_list_players_filter_by_team(client: TestClient):
    # find a team id via API to avoid direct DB access from test thread
    teams = client.get("/teams").json()
    tid = teams[0]["id"]
    r = client.get(f"/players?team_id={tid}")
    assert r.status_code == 200
    players = r.json()
    assert players and all(p["team_id"] == tid for p in players)
    # get one player by id
    pid = players[0]["id"]
    r2 = client.get(f"/players/{pid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == pid


def test_depth_chart_by_team(client: TestClient):
    teams = client.get("/teams").json()
    tid = teams[0]["id"]
    r = client.get(f"/depth-chart/{tid}")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    assert rows[0]["team_id"] == tid


def test_games_list(client: TestClient):
    r = client.get("/games?season=2025")
    assert r.status_code == 200
    games = r.json()
    assert len(games) >= 1
    assert games[0]["season"] == 2025
