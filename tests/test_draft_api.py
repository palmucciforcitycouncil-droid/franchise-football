import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, func, create_engine, SQLModel
from app.core.db import engine, get_session, create_db_and_tables
from app.models.draft import Prospect, DraftPick, DraftState, PickStatus
from app.services.draft_service import (
    get_draft_results, get_prospects, get_draft_board, add_to_board,
    make_pick, sim_until_next_user_pick, advance_clock,
    _get_draft_state, _get_team_name
)
from app.api.dto_draft import ActionResult
from app.main import app  # Import the main FastAPI app
from datetime import datetime, timedelta
import random

# --- Fixtures ---
@pytest.fixture(name="seeded_db")
def seeded_db_fixture():
    """Fresh in-memory SQLite database for each test, seeded with draft data."""
    test_engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)  # Create all tables

    with Session(test_engine) as session:
        # Seed Prospects
        positions = ["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
                    "DE", "DT", "LB", "CB", "S", "K", "P"]
        colleges = ["State U", "Tech A&M", "Coastal", "Midwest", "Ivy League"]
        prospects_data = []
        for i in range(1, 100):  # 99 prospects
            ovr = random.randint(60, 95)
            grade = round(random.uniform(5.0, 8.5), 1)
            pos = random.choice(positions)
            college = random.choice(colleges)
            prospects_data.append(Prospect(
                prospect_id=i,
                first_name=f"FN{i}",
                last_name=f"LN{i}",
                position=pos,
                college=college,
                ovr=ovr,
                draft_grade=grade
            ))
        session.add_all(prospects_data)
        session.commit()

        # Seed DraftPicks for 7 rounds * 32 picks
        season_year = 2024
        overall_pick_counter = 1
        draft_picks_data = []
        team_ids = list(range(1, 33))  # Assuming 32 teams
        random.shuffle(team_ids)  # Randomize initial pick order

        for round_no in range(1, 8):
            current_round_teams = list(team_ids)
            if round_no > 1:  # Snake draft logic for subsequent rounds
                if round_no % 2 == 0:  # Even rounds reverse order
                    current_round_teams.reverse()
                else:  # Odd rounds normal order
                    random.shuffle(current_round_teams)  # Reshuffle for realism, or keep fixed

            for pick_in_round in range(1, 33):
                team_id = current_round_teams[pick_in_round - 1]
                draft_picks_data.append(DraftPick(
                    season_year=season_year,
                    round_no=round_no,
                    pick_in_round=pick_in_round,
                    overall_pick=overall_pick_counter,
                    team_id=team_id,
                    status=PickStatus.PENDING
                ))
                overall_pick_counter += 1
        session.add_all(draft_picks_data)

        # Seed DraftState
        user_team_id = 1  # User controls Team 1
        # Set current pick to a mid-first round pick for testing sim_until_next_user_pick
        current_pick_overall = 5  # Example: Team 1 picks 5th
        
        # Find the pick for user_team_id at current_pick_overall
        user_pick_at_start = session.exec(
            select(DraftPick)
            .where(DraftPick.overall_pick == current_pick_overall)
        ).first()
        if user_pick_at_start:
            user_team_id = user_pick_at_start.team_id
        else:
            # Fallback if pick 5 doesn't exist or has no team_id
            user_team_id = 1

        draft_state = DraftState(
            season_year=season_year,
            current_pick_overall=current_pick_overall,
            user_team_id=user_team_id,
            is_paused=False,
            last_tick_utc=datetime.utcnow()
        )
        session.add(draft_state)
        session.commit()
        session.refresh(draft_state)

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

def test_get_draft_results(seeded_db: Session):
    season_year = 2024
    round_no = 1
    results = get_draft_results(seeded_db, season_year, round_no)
    assert results.season_year == season_year
    assert results.round == round_no
    assert len(results.rows) == 32
    assert results.current_overall == 5  # Initial state from fixture
    assert not results.user_on_clock  # Not on clock initially

    # Verify pending picks show dashes
    pending_pick = next((p for p in results.rows if p.overall == 1), None)
    assert pending_pick is not None
    assert pending_pick.prospect_name_or_dash == "— — — — — — — —"
    assert pending_pick.ovr_or_dash == "—"

def test_get_prospects(seeded_db: Session):
    prospects = get_prospects(seeded_db)
    assert len(prospects) > 0
    assert all(isinstance(p.id, int) for p in prospects)
    assert all(p.ovr >= 60 and p.ovr <= 95 for p in prospects)  # Based on seeding

    # Test search
    qb_prospects = get_prospects(seeded_db, q="QB")
    assert all("QB" in p.pos for p in qb_prospects)

    # Test limit
    limited_prospects = get_prospects(seeded_db, limit=5)
    assert len(limited_prospects) == 5

def test_get_draft_board(seeded_db: Session):
    user_team_id = 1
    # Add some prospects to the board first
    add_to_board(seeded_db, user_team_id, 1)
    add_to_board(seeded_db, user_team_id, 2)
    board = get_draft_board(seeded_db, user_team_id)
    assert len(board.prospects) == 2
    assert board.prospects[0].id == 1
    assert board.prospects[1].id == 2

def test_add_to_board(seeded_db: Session):
    user_team_id = 1
    prospect_id = 3
    result = add_to_board(seeded_db, user_team_id, prospect_id)
    assert result.ok is True
    assert "added to your draft board" in result.message
    
    prospect = seeded_db.get(Prospect, prospect_id)
    assert prospect.board_rank is not None

    # Try adding again, should update rank or be idempotent
    result_again = add_to_board(seeded_db, user_team_id, prospect_id)
    assert result_again.ok is True  # Should still be ok, just updates rank if already there

def test_make_pick_success(seeded_db: Session):
    season_year = 2024
    user_team_id = 1
    state = _get_draft_state(seeded_db, season_year)
    
    # Manually set a pick to ON_THE_CLOCK for the user's team
    pick_to_make = seeded_db.exec(
        select(DraftPick)
        .where(DraftPick.team_id == user_team_id, DraftPick.status == PickStatus.PENDING)
        .order_by(DraftPick.overall_pick)
    ).first()
    assert pick_to_make is not None
    
    # Update state to match the pick we found
    state.current_pick_overall = pick_to_make.overall_pick
    state.user_team_id = user_team_id  # Ensure state matches the team
    pick_to_make.status = PickStatus.ON_THE_CLOCK
    seeded_db.add(state)
    seeded_db.add(pick_to_make)
    seeded_db.commit()
    seeded_db.refresh(state)
    seeded_db.refresh(pick_to_make)

    prospect_to_draft = seeded_db.exec(select(Prospect).where(Prospect.prospect_id == 1)).first()
    assert prospect_to_draft is not None

    result = make_pick(seeded_db, season_year, prospect_to_draft.prospect_id, user_team_id)
    assert result.ok is True
    assert "drafted by" in result.message

    # Verify pick is updated
    updated_pick = seeded_db.get(DraftPick, pick_to_make.pick_id)
    assert updated_pick.status == PickStatus.MADE
    assert updated_pick.selected_prospect_id == prospect_to_draft.prospect_id
    
    # Verify draft state advanced
    updated_state = _get_draft_state(seeded_db, season_year)
    assert updated_state.current_pick_overall == pick_to_make.overall_pick + 1
    assert updated_state.is_paused is False  # Should unpause after user pick

def test_make_pick_validation_failures(seeded_db: Session):
    season_year = 2024
    user_team_id = 1
    state = _get_draft_state(seeded_db, season_year)
    original_overall_pick = state.current_pick_overall

    # Not on the clock - user team mismatch
    result = make_pick(seeded_db, season_year, 1, user_team_id)
    assert result.ok is False
    assert "Cannot make a pick for another team" in result.message

    # Manually set a pick to ON_THE_CLOCK for a *different* team
    other_team_pick = seeded_db.exec(
        select(DraftPick)
        .where(DraftPick.team_id != user_team_id, DraftPick.status == PickStatus.PENDING)
        .order_by(DraftPick.overall_pick)
    ).first()
    assert other_team_pick is not None
    
    state.current_pick_overall = other_team_pick.overall_pick
    other_team_pick.status = PickStatus.ON_THE_CLOCK
    seeded_db.add(state)
    seeded_db.add(other_team_pick)
    seeded_db.commit()
    seeded_db.refresh(state)
    seeded_db.refresh(other_team_pick)

    # Try to pick for user_team_id when another team is on the clock
    result = make_pick(seeded_db, season_year, 1, user_team_id)
    assert result.ok is False
    assert "It's not your team's pick" in result.message

    # Try to draft non-existent prospect
    state.current_pick_overall = original_overall_pick  # Reset for this test
    user_pick = seeded_db.exec(
        select(DraftPick)
        .where(DraftPick.team_id == user_team_id, DraftPick.status == PickStatus.PENDING)
        .order_by(DraftPick.overall_pick)
    ).first()
    assert user_pick is not None
    user_pick.status = PickStatus.ON_THE_CLOCK
    state.current_pick_overall = user_pick.overall_pick
    state.user_team_id = user_team_id  # Ensure state matches
    seeded_db.add(state)
    seeded_db.add(user_pick)
    seeded_db.commit()
    seeded_db.refresh(state)
    seeded_db.refresh(user_pick)

    result = make_pick(seeded_db, season_year, 9999, user_team_id)
    assert result.ok is False
    assert "Prospect not found" in result.message

    # Draft an already selected prospect
    first_prospect = seeded_db.get(Prospect, 1)
    first_pick = seeded_db.exec(select(DraftPick).where(DraftPick.overall_pick == 1)).first()
    first_pick.selected_prospect_id = first_prospect.prospect_id
    first_pick.status = PickStatus.MADE
    seeded_db.add(first_pick)
    seeded_db.commit()

    result = make_pick(seeded_db, season_year, first_prospect.prospect_id, user_team_id)
    assert result.ok is False
    assert "already been drafted" in result.message


def test_sim_until_next_user_pick(seeded_db: Session):
    season_year = 2024
    user_team_id = 1
    state = _get_draft_state(seeded_db, season_year)
    original_current_pick = state.current_pick_overall  # Should be 5 from fixture

    # Ensure user is not on clock initially
    current_pick_obj = seeded_db.exec(select(DraftPick).where(DraftPick.overall_pick == original_current_pick)).first()
    assert current_pick_obj.team_id != user_team_id  # Fixture sets user_team_id to the team at pick 5

    result = sim_until_next_user_pick(seeded_db, season_year, user_team_id)
    assert result.ok is True
    assert "Simulated to your pick" in result.message

    updated_state = _get_draft_state(seeded_db, season_year)
    assert updated_state.is_paused is True  # Should be paused on user pick

    # Verify current_pick_overall is now a user pick
    user_next_pick = seeded_db.exec(
        select(DraftPick)
        .where(DraftPick.overall_pick == updated_state.current_pick_overall)
    ).first()
    assert user_next_pick.team_id == user_team_id
    assert user_next_pick.status == PickStatus.ON_THE_CLOCK

    # Test sim to end of draft
    # Manually advance state to near end of draft
    last_pick_overall = seeded_db.exec(select(func.max(DraftPick.overall_pick))).first()
    state.current_pick_overall = last_pick_overall - 5  # 5 picks from end
    state.user_team_id = 999  # Ensure no more user picks
    seeded_db.add(state)
    seeded_db.commit()
    seeded_db.refresh(state)

    result_end = sim_until_next_user_pick(seeded_db, season_year, user_team_id)
    assert result_end.ok is True
    assert "Simulated to end of draft" in result_end.message
    updated_state_end = _get_draft_state(seeded_db, season_year)
    assert updated_state_end.current_pick_overall == last_pick_overall + 1
    assert updated_state_end.is_paused is True

def test_advance_clock(seeded_db: Session):
    season_year = 2024
    state = _get_draft_state(seeded_db, season_year)
    original_pick = state.current_pick_overall  # Should be 5

    # Pick is PENDING, should become ON_THE_CLOCK
    advance_clock(seeded_db, season_year)
    current_pick = seeded_db.exec(select(DraftPick).where(DraftPick.overall_pick == original_pick)).first()
    assert current_pick.status == PickStatus.ON_THE_CLOCK

    # If paused, should not advance
    state.is_paused = True
    seeded_db.add(state)
    seeded_db.commit()
    seeded_db.refresh(state)
    
    advance_clock(seeded_db, season_year)
    current_pick_after_pause = seeded_db.exec(select(DraftPick).where(DraftPick.overall_pick == original_pick)).first()
    assert current_pick_after_pause.status == PickStatus.ON_THE_CLOCK  # Still ON_THE_CLOCK, not advanced

def test_api_endpoints_exist(client: TestClient):
    # Just test that endpoints are reachable and return 200/400 as expected for basic calls
    # Detailed logic is tested in service functions
    season = 2024
    round_no = 1
    user_team_id = 1

    # GET /api/v1/draft/results
    response = client.get(f"/api/v1/draft/results?season={season}&round={round_no}")
    assert response.status_code == 200
    assert "rows" in response.json()

    # GET /api/v1/draft/prospects
    response = client.get("/api/v1/draft/prospects?q=QB&limit=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # GET /api/v1/draft/board
    response = client.get(f"/api/v1/draft/board?user_team_id={user_team_id}")
    assert response.status_code == 200
    assert "prospects" in response.json()

    # POST /api/v1/draft/board:add
    response = client.post(f"/api/v1/draft/board:add?prospect_id=1&user_team_id={user_team_id}")
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # POST /api/v1/draft/pick:make (requires being on the clock)
    # This will fail if not on clock, which is expected for a simple reachability test
    response = client.post(f"/api/v1/draft/pick:make?prospect_id=2&season={season}&team_id={user_team_id}")
    assert response.status_code == 200  # FastAPI returns 200 for ActionResult even if ok=False
    assert response.json()["ok"] is False
    assert "Not on the clock" in response.json()["message"]

    # POST /api/v1/draft/sim:next-user
    response = client.post(f"/api/v1/draft/sim:next-user?season={season}&user_team_id={user_team_id}")
    assert response.status_code == 200
    assert response.json()["ok"] is True
