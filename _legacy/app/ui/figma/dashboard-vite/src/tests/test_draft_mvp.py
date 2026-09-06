import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, create_engine, SQLModel
from app.core.db import get_session
from app.models.draft import Prospect, DraftState, DraftPick
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

def test_generate_and_list_prospects(client: TestClient, seeded_db: Session):
    """Test that draft class generation works and prospects can be listed."""
    s = 2036
    r = client.post(f"/api/v1/draft/generate?season={s}&seed=888")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["prospects"] >= 200
    
    r = client.get(f"/api/v1/draft/prospects?season={s}")
    assert r.status_code == 200
    pros = r.json()
    assert len(pros) >= 200
    assert any(p["pos"] == "QB" for p in pros)
    assert any(p["pos"] == "WR" for p in pros)
    assert any(p["pos"] == "RB" for p in pros)

def test_scout_board_and_pick_flow(client: TestClient, seeded_db: Session):
    """Test the complete flow from scouting to drafting."""
    s = 2036
    client.post(f"/api/v1/draft/generate?season={s}&seed=999")
    
    # grab first 10 prospects for board
    pros = client.get(f"/api/v1/draft/prospects?season={s}").json()[:10]
    pids = [p["prospect_id"] for p in pros]
    
    # upsert a scouting view
    sv = client.get(f"/api/v1/draft/scout_view?season={s}&team_id=1&prospect_id={pids[0]}")
    assert sv.status_code == 200
    assert "prospect_id" in sv.json()
    
    client.post("/api/v1/draft/scout", json={
        "season": s, "team_id": 1, "prospect_id": pids[0], 
        "bias_overall": 5, "confidence": 80, "notes": "Great prospect"
    })
    
    # set board
    client.post("/api/v1/draft/board", json={
        "season": s, "team_id": 1, "ordered_prospect_ids": pids
    })
    
    # verify board was set
    board_resp = client.get(f"/api/v1/draft/board?season={s}&team_id=1")
    assert board_resp.status_code == 200
    assert board_resp.json()["ordered_prospect_ids"] == pids
    
    # start draft and make pick #1
    client.post(f"/api/v1/draft/start?season={s}&seed=777")
    res = client.post("/api/v1/draft/pick", json={
        "season": s, "team_id": 1, "prospect_id": pids[0]
    })
    assert res.status_code == 200
    assert res.json().get("ok", False)

def test_cpu_runs_draft_to_end(client: TestClient, seeded_db: Session):
    """Test that CPU can run the entire draft."""
    s = 2036
    client.post(f"/api/v1/draft/generate?season={s}&seed=555")
    client.post(f"/api/v1/draft/start?season={s}")
    r = client.post(f"/api/v1/draft/run_to_end?season={s}")
    assert r.status_code == 200
    assert r.json().get("ok", False)
    assert r.json().get("completed", False)

def test_draft_state_management(client: TestClient, seeded_db: Session):
    """Test draft state transitions."""
    s = 2036
    client.post(f"/api/v1/draft/generate?season={s}&seed=123")
    
    # Start draft
    start_resp = client.post(f"/api/v1/draft/start?season={s}&seed=456")
    assert start_resp.status_code == 200
    
    # Make a few picks
    pros = client.get(f"/api/v1/draft/prospects?season={s}").json()[:5]
    pids = [p["prospect_id"] for p in pros]
    
    # Team 1 picks first
    pick_resp = client.post("/api/v1/draft/pick", json={
        "season": s, "team_id": 1, "prospect_id": pids[0]
    })
    assert pick_resp.status_code == 200
    assert pick_resp.json().get("ok", False)
    
    # CPU picks for team 2
    cpu_resp = client.post(f"/api/v1/draft/cpu_pick?season={s}")
    assert cpu_resp.status_code == 200
    assert cpu_resp.json().get("ok", False)

def test_prospect_filtering(client: TestClient, seeded_db: Session):
    """Test that prospect filtering by position works."""
    s = 2036
    client.post(f"/api/v1/draft/generate?season={s}&seed=789")
    
    # Get all prospects
    all_pros = client.get(f"/api/v1/draft/prospects?season={s}").json()
    assert len(all_pros) >= 200
    
    # Get QB prospects only
    qb_pros = client.get(f"/api/v1/draft/prospects?season={s}&pos=QB").json()
    assert len(qb_pros) >= 4  # Should have at least 4 QBs
    assert all(p["pos"] == "QB" for p in qb_pros)
    
    # Get WR prospects only
    wr_pros = client.get(f"/api/v1/draft/prospects?season={s}&pos=WR").json()
    assert len(wr_pros) >= 20  # Should have many WRs
    assert all(p["pos"] == "WR" for p in wr_pros)

def test_scouting_reports(client: TestClient, seeded_db: Session):
    """Test scouting report functionality."""
    s = 2036
    client.post(f"/api/v1/draft/generate?season={s}&seed=321")
    
    pros = client.get(f"/api/v1/draft/prospects?season={s}").json()[:3]
    
    # Test scouting view without report
    sv1 = client.get(f"/api/v1/draft/scout_view?season={s}&team_id=1&prospect_id={pros[0]['prospect_id']}")
    assert sv1.status_code == 200
    data1 = sv1.json()
    assert "scouted_overall" in data1
    assert "confidence" in data1
    
    # Add scouting report
    scout_resp = client.post("/api/v1/draft/scout", json={
        "season": s, "team_id": 1, "prospect_id": pros[0]["prospect_id"],
        "bias_overall": 3, "confidence": 85, "notes": "Excellent player"
    })
    assert scout_resp.status_code == 200
    
    # Test scouting view with report
    sv2 = client.get(f"/api/v1/draft/scout_view?season={s}&team_id=1&prospect_id={pros[0]['prospect_id']}")
    assert sv2.status_code == 200
    data2 = sv2.json()
    assert data2["confidence"] == 85
    assert "Excellent player" in data2.get("notes", "")

def test_draft_board_management(client: TestClient, seeded_db: Session):
    """Test draft board setting and retrieval."""
    s = 2036
    client.post(f"/api/v1/draft/generate?season={s}&seed=654")
    
    pros = client.get(f"/api/v1/draft/prospects?season={s}").json()[:15]
    pids = [p["prospect_id"] for p in pros]
    
    # Set board
    board_resp = client.post("/api/v1/draft/board", json={
        "season": s, "team_id": 1, "ordered_prospect_ids": pids
    })
    assert board_resp.status_code == 200
    
    # Get board
    get_board_resp = client.get(f"/api/v1/draft/board?season={s}&team_id=1")
    assert get_board_resp.status_code == 200
    board_data = get_board_resp.json()
    assert board_data["ordered_prospect_ids"] == pids
    
    # Update board with different order
    reversed_pids = list(reversed(pids))
    update_resp = client.post("/api/v1/draft/board", json={
        "season": s, "team_id": 1, "ordered_prospect_ids": reversed_pids
    })
    assert update_resp.status_code == 200
    
    # Verify update
    updated_board = client.get(f"/api/v1/draft/board?season={s}&team_id=1").json()
    assert updated_board["ordered_prospect_ids"] == reversed_pids