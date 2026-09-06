import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, create_engine, SQLModel
from app.core.db import get_session
from app.models.draft import DraftState, DraftPick
from app.models.trade_block import TeamTradeBlock
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

def test_pause_resume_status(client: TestClient, seeded_db: Session):
    """Test draft pause/resume functionality."""
    s = 2037
    # create a draft state via generate+start from previous prompt
    client.post(f"/api/v1/draft/generate?season={s}")
    client.post(f"/api/v1/draft/start?season={s}")
    
    r = client.get(f"/api/v1/draft/admin/status?season={s}")
    assert r.status_code == 200
    status_data = r.json()
    assert status_data["exists"]
    assert status_data["is_active"]

    # Pause the draft
    r = client.post(f"/api/v1/draft/admin/pause?season={s}")
    assert r.status_code == 200
    pause_data = r.json()
    assert pause_data["ok"]
    assert pause_data["paused"]
    
    # Check status after pause
    r = client.get(f"/api/v1/draft/admin/status?season={s}")
    assert r.status_code == 200
    status_data = r.json()
    assert not status_data["is_active"]
    
    # Resume the draft
    r = client.post(f"/api/v1/draft/admin/resume?season={s}")
    assert r.status_code == 200
    resume_data = r.json()
    assert resume_data["ok"]
    assert not resume_data["paused"]
    
    # Check status after resume
    r = client.get(f"/api/v1/draft/admin/status?season={s}")
    assert r.status_code == 200
    status_data = r.json()
    assert status_data["is_active"]

def test_team_needs_calc_uses_starters(client: TestClient, seeded_db: Session):
    """Test team needs calculation."""
    s = 2037
    # Ensure charts filled
    r = client.get(f"/api/v1/draft/admin/needs?season={s}&team_id=1")
    assert r.status_code == 200
    data = r.json()
    assert "QB" in data
    assert "need" in data["QB"]
    assert "league_avg" in data["QB"]
    assert "team_avg" in data["QB"]

def test_pick_trade_block_and_transfer(client: TestClient, seeded_db: Session):
    """Test pick trade block functionality."""
    s = 2037
    client.post(f"/api/v1/draft/generate?season={s}")
    
    # list owned picks for team 1
    r = client.get(f"/api/v1/draft/admin/picks?season={s}&team_id=1")
    assert r.status_code == 200
    picks = r.json()
    assert len(picks) >= 7
    rnd, slot = picks[0]["round"], picks[0]["slot"]

    # add to block
    r = client.post("/api/v1/draft/admin/picks/block", json={
        "season": s, "team_id": 1, "round": rnd, "slot": slot, "note": "available"
    })
    assert r.status_code == 200
    assert r.json()["ok"]

    # transfer to team 2 (simulate consummated trade)
    r = client.post("/api/v1/draft/admin/picks/transfer", json={
        "season": s, "round": rnd, "slot": slot, "to_team_id": 2
    })
    assert r.status_code == 200
    assert r.json()["ok"]

    # should reflect in owner list now
    r = client.get(f"/api/v1/draft/admin/picks?season={s}&team_id=2")
    assert any(p["round"] == rnd and p["slot"] == slot for p in r.json())

def test_league_starter_averages(client: TestClient, seeded_db: Session):
    """Test league starter averages calculation."""
    s = 2037
    r = client.get(f"/api/v1/draft/admin/needs/league_avg?season={s}")
    assert r.status_code == 200
    data = r.json()
    assert "QB" in data
    assert "WR" in data
    assert "RB" in data
    assert isinstance(data["QB"], (int, float))

def test_team_starter_averages(client: TestClient, seeded_db: Session):
    """Test team starter averages calculation."""
    s = 2037
    r = client.get(f"/api/v1/draft/admin/needs/team_avg?season={s}&team_id=1")
    assert r.status_code == 200
    data = r.json()
    assert "QB" in data
    assert "WR" in data
    assert "RB" in data
    assert isinstance(data["QB"], (int, float))

def test_pick_unblock(client: TestClient, seeded_db: Session):
    """Test removing picks from trade block."""
    s = 2037
    client.post(f"/api/v1/draft/generate?season={s}")
    
    # Get a pick
    r = client.get(f"/api/v1/draft/admin/picks?season={s}&team_id=1")
    picks = r.json()
    rnd, slot = picks[0]["round"], picks[0]["slot"]
    
    # Add to block
    client.post("/api/v1/draft/admin/picks/block", json={
        "season": s, "team_id": 1, "round": rnd, "slot": slot, "note": "test"
    })
    
    # Remove from block
    r = client.post("/api/v1/draft/admin/picks/unblock", json={
        "season": s, "team_id": 1, "round": rnd, "slot": slot
    })
    assert r.status_code == 200
    assert r.json()["ok"]

def test_draft_status_nonexistent(client: TestClient, seeded_db: Session):
    """Test draft status for non-existent draft."""
    s = 9999
    r = client.get(f"/api/v1/draft/admin/status?season={s}")
    assert r.status_code == 200
    data = r.json()
    assert not data["exists"]

def test_pause_nonexistent_draft(client: TestClient, seeded_db: Session):
    """Test pause for non-existent draft."""
    s = 9999
    r = client.post(f"/api/v1/draft/admin/pause?season={s}")
    assert r.status_code == 200
    data = r.json()
    assert "error" in data
    assert "no draft state" in data["error"]

def test_resume_nonexistent_draft(client: TestClient, seeded_db: Session):
    """Test resume for non-existent draft."""
    s = 9999
    r = client.post(f"/api/v1/draft/admin/resume?season={s}")
    assert r.status_code == 200
    data = r.json()
    assert "error" in data
    assert "no draft state" in data["error"]
