import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, create_engine, SQLModel
from app.core.db import get_session
from app.models.event_log import EventLog
from app.models.sim_models import Game, Team
from app.services.event_log_service import emit_event, feed_since
from app.services.season_orchestrator import sim_week, _fallback_sim
from app.main import app
from datetime import datetime
import random

# --- Fixtures ---
@pytest.fixture(name="seeded_db")
def seeded_db_fixture():
    """Fresh in-memory SQLite database for each test, seeded with basic data."""
    test_engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)  # Create all tables

    with Session(test_engine) as session:
        # Seed some teams for standings/power rating
        teams_data = [
            Team(id=1, abbr="BUF", city="Buffalo", name="Bills", conference="AFC", division="East"),
            Team(id=2, abbr="MIA", city="Miami", name="Dolphins", conference="AFC", division="East"),
            Team(id=3, abbr="NE", city="New England", name="Patriots", conference="AFC", division="East"),
            Team(id=4, abbr="NYJ", city="New York", name="Jets", conference="AFC", division="East"),
        ]
        session.add_all(teams_data)
        session.commit()
        
        yield session  # Provide the session for tests

    SQLModel.metadata.drop_all(test_engine)  # Clean up after test

@pytest.fixture(name="client")
def client_fixture(seeded_db: Session):
    """Test client that uses the seeded_db session."""
    def override_get_session():
        yield seeded_db
    
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()  # Clean up overrides

# --- Test Cases ---

def test_emit_event(seeded_db: Session):
    """Test that events can be emitted and retrieved."""
    event = emit_event(
        seeded_db, 
        season=2025, 
        week=1, 
        event_type="TEST_EVENT",
        team_id=1,
        payload={"test": "data"}
    )
    
    assert event.id is not None
    assert event.season == 2025
    assert event.week == 1
    assert event.event_type == "TEST_EVENT"
    assert event.team_id == 1
    assert event.payload_json == '{"test": "data"}'

def test_feed_since(seeded_db: Session):
    """Test event feed retrieval with pagination."""
    # Emit some test events
    emit_event(seeded_db, season=2025, week=1, event_type="EVENT_1", team_id=1)
    emit_event(seeded_db, season=2025, week=1, event_type="EVENT_2", team_id=2)
    emit_event(seeded_db, season=2025, week=2, event_type="EVENT_3", team_id=3)
    
    # Get all events
    all_events = feed_since(seeded_db)
    assert len(all_events) == 3
    assert all_events[0]["event_type"] == "EVENT_3"  # Most recent first
    
    # Get events since a specific ID
    since_id = all_events[1]["id"]
    recent_events = feed_since(seeded_db, since_id=since_id)
    assert len(recent_events) == 1
    assert recent_events[0]["event_type"] == "EVENT_3"

def test_fallback_sim_deterministic(seeded_db: Session):
    """Test that fallback simulation is deterministic with same seed."""
    # Run simulation twice with same seed
    result1 = _fallback_sim(seeded_db, 2025, 1, 1, 1, 2, 12345)
    result2 = _fallback_sim(seeded_db, 2025, 1, 1, 1, 2, 12345)
    
    # Results should be identical
    assert result1["home_score"] == result2["home_score"]
    assert result1["away_score"] == result2["away_score"]
    assert result1["home_team_line"]["yards_offense"] == result2["home_team_line"]["yards_offense"]

def test_fallback_sim_different_with_different_seed(seeded_db: Session):
    """Test that fallback simulation produces different results with different seeds."""
    # Run simulation with different seeds
    result1 = _fallback_sim(seeded_db, 2025, 1, 1, 1, 2, 12345)
    result2 = _fallback_sim(seeded_db, 2025, 1, 1, 1, 2, 54321)
    
    # Results should be different (very high probability)
    assert result1["home_score"] != result2["home_score"] or result1["away_score"] != result2["away_score"]

def test_event_log_model_fields(seeded_db: Session):
    """Test that EventLog model has all required fields."""
    event = EventLog(
        season=2025,
        week=1,
        event_type="TEST",
        team_id=1,
        player_id=2,
        coach_id=3,
        game_id=4,
        payload_json='{"test": "data"}'
    )
    
    seeded_db.add(event)
    seeded_db.commit()
    seeded_db.refresh(event)
    
    assert event.id is not None
    assert event.ts is not None
    assert event.season == 2025
    assert event.week == 1
    assert event.event_type == "TEST"
    assert event.team_id == 1
    assert event.player_id == 2
    assert event.coach_id == 3
    assert event.game_id == 4
    assert event.payload_json == '{"test": "data"}'

def test_sim_week_creates_results_and_events(client: TestClient, seeded_db: Session):
    """Test that sim_week creates game results and emits events."""
    s, w = 2035, 1
    
    # Seed 2 games
    g1 = Game(season=s, week=w, home_team_id=1, away_team_id=2)
    g2 = Game(season=s, week=w, home_team_id=3, away_team_id=4)
    seeded_db.add(g1)
    seeded_db.add(g2)
    seeded_db.commit()
    seeded_db.refresh(g1)
    seeded_db.refresh(g2)
    
    # Sim the week
    r = client.post(f"/api/v1/season/sim_week?season={s}&week={w}&seed=999")
    assert r.status_code == 200
    out = r.json()
    assert out["ok"] and len(out["games"]) == 2
    
    # Feed should have GAME_FINAL events
    fr = client.get("/api/v1/feed")
    assert fr.status_code == 200
    items = fr.json()
    game_final_events = [ev for ev in items if ev["event_type"] == "GAME_FINAL"]
    assert len(game_final_events) >= 2  # Could be more if other tests ran
    assert any(ev["game_id"] == g1.id for ev in game_final_events)
    assert any(ev["game_id"] == g2.id for ev in game_final_events)

def test_feed_since_paginates(client: TestClient, seeded_db: Session):
    """Test that feed pagination works correctly."""
    # Clear existing events to ensure predictable pagination
    seeded_db.exec(select(EventLog).where(EventLog.id > 0)).delete()
    seeded_db.commit()
    
    # Emit more events than the limit
    for i in range(250):
        emit_event(seeded_db, season=2025, week=1, event_type=f"PAGINATION_EVENT_{i}")
    
    # Get first page (limit 200)
    r1 = client.get("/api/v1/feed")
    assert r1.status_code == 200
    items1 = r1.json()
    assert len(items1) == 200
    
    # Get next page using since_id
    since_id = items1[-1]["id"]  # Oldest event on first page
    r2 = client.get(f"/api/v1/feed?since_id={since_id}")
    assert r2.status_code == 200
    items2 = r2.json()
    assert len(items2) == 50  # Remaining 50 events

def test_sim_week_empty_week(client: TestClient, seeded_db: Session):
    """Test sim_week with no games scheduled."""
    # Ensure no games for this season/week
    seeded_db.exec(select(Game).where(Game.season == 2025, Game.week == 99)).delete()
    seeded_db.commit()
    
    r = client.post("/api/v1/season/sim_week?season=2025&week=99")
    assert r.status_code == 200
    out = r.json()
    assert out["ok"] is True
    assert out["games"] == []

def test_api_endpoints_exist(seeded_db: Session):
    """Test that API endpoints are reachable."""
    # Create a test client that uses the seeded_db session
    def override_get_session():
        yield seeded_db
    
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        # Test sim_week endpoint
        response = client.post("/api/v1/season/sim_week?season=2025&week=1")
        assert response.status_code == 200
        assert "games" in response.json()
        
        # Test feed endpoint
        response = client.get("/api/v1/feed")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    app.dependency_overrides.clear()
