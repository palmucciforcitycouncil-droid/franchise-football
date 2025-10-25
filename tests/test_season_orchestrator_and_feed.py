import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, create_engine, SQLModel
from app.core.db import engine, get_session, create_db_and_tables
from app.models.event_log import EventLog
from app.models.sim_models import Game
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
        # Seed some basic data for testing
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

def test_feed_endpoint_exists(client: TestClient):
    """Test that feed endpoint is reachable."""
    response = client.get("/api/v1/feed")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
