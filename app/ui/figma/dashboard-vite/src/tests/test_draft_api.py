import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from app.models.draft import Prospect, DraftPick, DraftState, PickStatus
from app.main import app
from app.core.db import get_session

@pytest.fixture
def test_db():
    """Create a fresh in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Import all models to ensure they're registered
    from app.models.draft import Prospect, DraftPick, DraftState  # noqa: F401
    
    # Create all tables
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as sess:
        yield sess

@pytest.fixture
def seeded_draft_data(test_db):
    """Seed test database with draft data."""
    sess = test_db
    
    # Create prospects (64-96 with varied OVR/POS/college)
    prospects = []
    colleges = ["Alabama", "Ohio State", "Georgia", "Michigan", "Clemson", "LSU", "USC", "Texas", "Oklahoma", "Florida"]
    positions = ["QB", "RB", "WR", "TE", "OT", "OG", "C", "DE", "DT", "LB", "CB", "S"]
    
    for i in range(80):
        prospect = Prospect(
            first_name=f"Player{i+1}",
            last_name="Test",
            position=positions[i % len(positions)],
            college=colleges[i % len(colleges)],
            ovr=95 - (i // 8),  # OVR ranges from 95 down to 85
            draft_grade=8.5 - (i * 0.1),
            board_rank=i + 1 if i < 20 else None
        )
        sess.add(prospect)
        prospects.append(prospect)
    
    sess.commit()
    
    # Create draft picks for 7 rounds × 32 picks
    picks = []
    pick_number = 1
    
    for round_no in range(1, 8):
        for pick_in_round in range(1, 33):
            # Simple team assignment (round-robin)
            team_id = ((pick_number - 1) % 32) + 1
            
            pick = DraftPick(
                season_year=2024,
                round_no=round_no,
                pick_in_round=pick_in_round,
                overall_pick=pick_number,
                team_id=team_id,
                selected_prospect_id=None,
                status=PickStatus.PENDING
            )
            sess.add(pick)
            picks.append(pick)
            pick_number += 1
    
    sess.commit()
    
    # Create draft state (user team 1, current pick 5)
    state = DraftState(
        season_year=2024,
        current_pick_overall=5,
        user_team_id=1,
        is_paused=False,
        last_tick_utc=None
    )
    sess.add(state)
    sess.commit()
    
    return {
        'prospects': prospects,
        'picks': picks,
        'state': state
    }

@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    def override_get_session():
        return test_db
    
    app.dependency_overrides[get_session] = override_get_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

def test_get_draft_results(client, seeded_draft_data):
    """Test GET /api/draft/results returns 32 rows for the round."""
    response = client.get("/api/draft/results?round=1")
    assert response.status_code == 200
    
    data = response.json()
    assert data['season_year'] == 2024
    assert data['round'] == 1
    assert len(data['rows']) == 32
    
    # Check first few rows
    first_row = data['rows'][0]
    assert first_row['overall'] == 1
    assert first_row['round'] == 1
    assert first_row['pick_in_round'] == 1
    assert first_row['prospect_name_or_dash'] == "— — — — — — — —"
    assert first_row['ovr_or_dash'] == "— — — — — — — —"

def test_draft_results_user_on_clock(client, seeded_draft_data):
    """Test that when current_pick_overall belongs to user team, user_on_clock=true."""
    response = client.get("/api/draft/results?round=1")
    assert response.status_code == 200
    
    data = response.json()
    assert data['user_on_clock'] == True  # User team 1 has pick 5
    assert data['current_overall'] == 5

def test_draft_results_pending_rows_show_dashes(client, seeded_draft_data):
    """Test that pending rows show dashes."""
    response = client.get("/api/draft/results?round=1")
    assert response.status_code == 200
    
    data = response.json()
    for row in data['rows']:
        if row['overall'] <= 4:  # First 4 picks should show dashes
            assert row['prospect_name_or_dash'] == "— — — — — — — —"
            assert row['ovr_or_dash'] == "— — — — — — — —"
            assert row['pos_or_dash'] == "— — — — — — — —"
            assert row['college_or_dash'] == "— — — — — — — —"

def test_make_pick_success(client, seeded_draft_data):
    """Test POST /api/draft/pick/make sets the selected prospect."""
    # First, make a pick
    response = client.post("/api/draft/pick/make", json={"prospect_id": 1})
    assert response.status_code == 200
    
    result = response.json()
    assert result['ok'] == True
    assert "successfully" in result['message']
    
    # Verify the pick was made
    response = client.get("/api/draft/results?round=1")
    assert response.status_code == 200
    
    data = response.json()
    # Pick 5 should now show the prospect
    pick_5_row = next(row for row in data['rows'] if row['overall'] == 5)
    assert pick_5_row['prospect_name_or_dash'] == "Player1 Test"
    assert pick_5_row['ovr_or_dash'] == "95"
    assert pick_5_row['pos_or_dash'] == "QB"
    assert pick_5_row['college_or_dash'] == "Alabama"

def test_make_pick_already_selected(client, seeded_draft_data):
    """Test that cannot draft an already-selected prospect."""
    # Make first pick
    response = client.post("/api/draft/pick/make", json={"prospect_id": 1})
    assert response.status_code == 200
    
    # Try to draft same prospect again
    response = client.post("/api/draft/pick/make", json={"prospect_id": 1})
    assert response.status_code == 200
    
    result = response.json()
    assert result['ok'] == False
    assert "already selected" in result['message']

def test_make_pick_not_on_clock(client, seeded_draft_data):
    """Test that cannot pick when not on clock."""
    # Change state so user is not on clock
    from sqlmodel import select
    sess = test_db
    state = sess.exec(select(DraftState)).first()
    state.current_pick_overall = 6  # User team 1 has pick 5, so this is not their turn
    sess.add(state)
    sess.commit()
    
    response = client.post("/api/draft/pick/make", json={"prospect_id": 1})
    assert response.status_code == 200
    
    result = response.json()
    assert result['ok'] == False
    assert "Not your turn" in result['message']

def test_sim_next_user_pick(client, seeded_draft_data):
    """Test POST /api/draft/sim/next-user fills AI picks until user's next selection."""
    response = client.post("/api/draft/sim/next-user")
    assert response.status_code == 200
    
    result = response.json()
    assert result['ok'] == True
    assert "Ready for user pick" in result['message']
    
    # Verify current pick advanced to next user pick
    response = client.get("/api/draft/results?round=1")
    assert response.status_code == 200
    
    data = response.json()
    # Should be on next user pick (team 1 has picks 5, 37, 69, etc.)
    assert data['current_overall'] == 37  # Next user pick
    assert data['user_on_clock'] == True

def test_get_prospects(client, seeded_draft_data):
    """Test GET /api/draft/prospects returns prospects."""
    response = client.get("/api/draft/prospects")
    assert response.status_code == 200
    
    prospects = response.json()
    assert len(prospects) > 0
    assert len(prospects) <= 50  # Default limit
    
    # Check structure
    prospect = prospects[0]
    assert 'id' in prospect
    assert 'name' in prospect
    assert 'pos' in prospect
    assert 'college' in prospect
    assert 'ovr' in prospect
    assert 'grade' in prospect

def test_get_prospects_search(client, seeded_draft_data):
    """Test GET /api/draft/prospects with search query."""
    response = client.get("/api/draft/prospects?q=Alabama")
    assert response.status_code == 200
    
    prospects = response.json()
    assert len(prospects) > 0
    
    # All prospects should be from Alabama
    for prospect in prospects:
        assert "Alabama" in prospect['college']

def test_get_prospects_top_only(client, seeded_draft_data):
    """Test GET /api/draft/prospects with top_only filter."""
    response = client.get("/api/draft/prospects?top=true")
    assert response.status_code == 200
    
    prospects = response.json()
    assert len(prospects) > 0
    
    # All prospects should have OVR >= 80
    for prospect in prospects:
        assert prospect['ovr'] >= 80

def test_get_draft_board(client, seeded_draft_data):
    """Test GET /api/draft/board returns user's draft board."""
    response = client.get("/api/draft/board")
    assert response.status_code == 200
    
    data = response.json()
    assert 'prospects' in data
    assert len(data['prospects']) > 0

def test_add_to_board(client, seeded_draft_data):
    """Test POST /api/draft/board/add adds prospect to board."""
    response = client.post("/api/draft/board/add", json={"prospect_id": 1})
    assert response.status_code == 200
    
    result = response.json()
    assert result['ok'] == True
    assert "added to board" in result['message']

def test_round_tabs_all_rounds(client, seeded_draft_data):
    """Test that querying each round returns 32 rows."""
    for round_no in range(1, 8):
        response = client.get(f"/api/draft/results?round={round_no}")
        assert response.status_code == 200
        
        data = response.json()
        assert data['round'] == round_no
        assert len(data['rows']) == 32

def test_invalid_round_number(client, seeded_draft_data):
    """Test that invalid round numbers return 400."""
    response = client.get("/api/draft/results?round=0")
    assert response.status_code == 400
    
    response = client.get("/api/draft/results?round=8")
    assert response.status_code == 400

def test_prospects_limit(client, seeded_draft_data):
    """Test that prospects endpoint respects limit parameter."""
    response = client.get("/api/draft/prospects?limit=10")
    assert response.status_code == 200
    
    prospects = response.json()
    assert len(prospects) <= 10

def test_prospects_limit_cap(client, seeded_draft_data):
    """Test that limit is capped at 100."""
    response = client.get("/api/draft/prospects?limit=200")
    assert response.status_code == 200
    
    prospects = response.json()
    assert len(prospects) <= 100

def test_draft_state_advancement(client, seeded_draft_data):
    """Test that draft state advances correctly after picks."""
    # Make a pick
    response = client.post("/api/draft/pick/make", json={"prospect_id": 1})
    assert response.status_code == 200
    
    # Check that state advanced
    response = client.get("/api/draft/results?round=1")
    assert response.status_code == 200
    
    data = response.json()
    assert data['current_overall'] == 6  # Should advance from 5 to 6

def test_team_names_mapping(client, seeded_draft_data):
    """Test that team names are properly mapped."""
    response = client.get("/api/draft/results?round=1")
    assert response.status_code == 200
    
    data = response.json()
    # Check that team names are not just "Team X"
    team_names = [row['team_name'] for row in data['rows']]
    assert any("Patriots" in name for name in team_names)
    assert any("Bills" in name for name in team_names)

def test_draft_completion_simulation(client, seeded_draft_data):
    """Test simulation handles draft completion."""
    # Set state to near end of draft
    from sqlmodel import select
    sess = test_db
    state = sess.exec(select(DraftState)).first()
    state.current_pick_overall = 220  # Near end of 7 rounds
    sess.add(state)
    sess.commit()
    
    response = client.post("/api/draft/sim/next-user")
    assert response.status_code == 200
    
    result = response.json()
    # Should complete draft or reach end
    assert result['ok'] == True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])