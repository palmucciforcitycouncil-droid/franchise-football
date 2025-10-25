import pytest
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.roster import DepthChart
from app.models.player import Player
from app.services.depth_chart_service import (
    list_depth_chart, set_depth_chart, auto_fill, lineup_for_game,
    ORDERED_SLOTS, ELIGIBILITY, get_depth_chart_by_slot, validate_depth_chart,
    get_available_players_for_slot, update_single_slot, clear_depth_chart,
    get_depth_chart_summary, get_injured_players_in_lineup, get_depth_chart_with_player_info
)
from app.engine.lineup_adapter import (
    offense_group, defense_group, special_group, get_starting_lineup,
    get_backup_lineup, get_depth_at_position, get_offensive_line,
    get_skill_positions, get_defensive_front, get_defensive_backs,
    get_specialists, get_returners, validate_lineup_completeness,
    get_lineup_summary, get_position_groups, get_player_slot_mapping,
    get_slot_depth, get_total_depth, is_lineup_complete, get_missing_positions
)

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_auto_fill_and_get_lineup(client, seeded_db, season_setup):
    """Test auto-fill and get lineup functionality."""
    s, w = season_setup.current_season, season_setup.current_week
    team, opp = season_setup.user_team_id, season_setup.opponent_team_id

    # Autofill should complete without error
    r = client.post(f"/api/v1/roster/auto_fill?team_id={team}&season={s}&week={w}&game_id=1001&opponent_id={opp}")
    assert r.status_code == 200

    # Fetch chart
    r = client.get(f"/api/v1/roster/depth_chart?team_id={team}")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    
    # Fetch lineup for engine
    r = client.get(f"/api/v1/roster/lineup_for_game?team_id={team}&season={s}&week={w}&game_id=1001&opponent_id={opp}")
    assert r.status_code == 200
    slots = r.json()["slots"]
    assert "QB" in slots and "K" in slots

def test_set_depth_chart_roundtrip(client, seeded_db):
    """Test setting depth chart and reading it back."""
    # Minimal manual post and readback
    body = {
        "team_id": 1,
        "items": [
            {"slot": "QB", "order_index": 0, "player_id": 123},
            {"slot": "RB", "order_index": 0, "player_id": 124},
            {"slot": "K", "order_index": 0, "player_id": 125}
        ]
    }
    r = client.post("/api/v1/roster/depth_chart", json=body)
    assert r.status_code == 200

    r = client.get("/api/v1/roster/depth_chart?team_id=1")
    data = r.json()
    assert any(row["slot"] == "QB" and row["player_id"] == 123 for row in data)

def test_depth_chart_models(session: Session):
    """Test depth chart model creation."""
    depth_chart = DepthChart(
        team_id=1,
        slot="QB",
        order_index=0,
        player_id=123
    )
    
    session.add(depth_chart)
    session.commit()
    session.refresh(depth_chart)
    
    assert depth_chart.id is not None
    assert depth_chart.team_id == 1
    assert depth_chart.slot == "QB"
    assert depth_chart.order_index == 0
    assert depth_chart.player_id == 123

def test_list_depth_chart(session: Session):
    """Test listing depth chart."""
    # Create test depth chart entries
    entries = [
        DepthChart(team_id=1, slot="QB", order_index=0, player_id=123),
        DepthChart(team_id=1, slot="RB", order_index=0, player_id=124),
        DepthChart(team_id=1, slot="QB", order_index=1, player_id=125)
    ]
    
    for entry in entries:
        session.add(entry)
    session.commit()
    
    # List depth chart
    rows = list_depth_chart(session, 1)
    assert len(rows) == 3
    assert any(row.slot == "QB" and row.order_index == 0 for row in rows)

def test_set_depth_chart(session: Session):
    """Test setting depth chart."""
    # Set depth chart
    items = [
        ("QB", 0, 123),
        ("RB", 0, 124),
        ("K", 0, 125)
    ]
    set_depth_chart(session, 1, items)
    
    # Verify entries
    rows = list_depth_chart(session, 1)
    assert len(rows) == 3
    assert any(row.slot == "QB" and row.player_id == 123 for row in rows)

def test_auto_fill(session: Session):
    """Test auto-fill functionality."""
    # Create test players
    players = [
        Player(name="QB1", team_id=1, pos="QB", overall=85),
        Player(name="QB2", team_id=1, pos="QB", overall=75),
        Player(name="RB1", team_id=1, pos="RB", overall=80),
        Player(name="K1", team_id=1, pos="K", overall=70)
    ]
    
    for player in players:
        session.add(player)
    session.commit()
    
    # Auto-fill depth chart
    auto_fill(session, 1, 2024, 1, 1001, 2)
    
    # Verify entries
    rows = list_depth_chart(session, 1)
    assert len(rows) > 0
    
    # Check QB slot is filled with best player
    qb_rows = [r for r in rows if r.slot == "QB" and r.order_index == 0]
    assert len(qb_rows) == 1
    assert qb_rows[0].player_id == players[0].player_id  # Best QB

def test_lineup_for_game(session: Session):
    """Test lineup for game functionality."""
    # Create test players and depth chart
    players = [
        Player(name="QB1", team_id=1, pos="QB", overall=85),
        Player(name="RB1", team_id=1, pos="RB", overall=80),
        Player(name="K1", team_id=1, pos="K", overall=70)
    ]
    
    for player in players:
        session.add(player)
    session.commit()
    
    # Set depth chart
    items = [
        ("QB", 0, players[0].player_id),
        ("RB", 0, players[1].player_id),
        ("K", 0, players[2].player_id)
    ]
    set_depth_chart(session, 1, items)
    
    # Get lineup
    lineup = lineup_for_game(session, 1, 2024, 1, 1001, 2)
    
    assert "QB" in lineup
    assert "RB" in lineup
    assert "K" in lineup
    assert lineup["QB"][0] == players[0].player_id

def test_eligibility_map():
    """Test position eligibility mapping."""
    assert "QB" in ELIGIBILITY
    assert "QB" in ELIGIBILITY["QB"]
    assert "WR" in ELIGIBILITY["WR1"]
    assert "WR" in ELIGIBILITY["WR2"]
    assert "WR" in ELIGIBILITY["WR3"]

def test_ordered_slots():
    """Test ordered slots list."""
    assert "QB" in ORDERED_SLOTS
    assert "K" in ORDERED_SLOTS
    assert "P" in ORDERED_SLOTS
    assert len(ORDERED_SLOTS) > 0

def test_validate_depth_chart(session: Session):
    """Test depth chart validation."""
    # Create incomplete depth chart
    entries = [
        DepthChart(team_id=1, slot="QB", order_index=0, player_id=123),
        # Missing K and P
    ]
    
    for entry in entries:
        session.add(entry)
    session.commit()
    
    # Validate
    issues = validate_depth_chart(session, 1)
    assert "errors" in issues
    assert "warnings" in issues
    assert any("Missing starting K" in error for error in issues["errors"])

def test_get_available_players_for_slot(session: Session):
    """Test getting available players for a slot."""
    # Create test players
    players = [
        Player(name="QB1", team_id=1, pos="QB", overall=85),
        Player(name="QB2", team_id=1, pos="QB", overall=75),
        Player(name="RB1", team_id=1, pos="RB", overall=80)
    ]
    
    for player in players:
        session.add(player)
    session.commit()
    
    # Get available QBs
    qbs = get_available_players_for_slot(session, 1, "QB")
    assert len(qbs) == 2
    assert all(p.pos == "QB" for p in qbs)

def test_update_single_slot(session: Session):
    """Test updating a single slot."""
    # Create initial entry
    entry = DepthChart(team_id=1, slot="QB", order_index=0, player_id=123)
    session.add(entry)
    session.commit()
    
    # Update slot
    success = update_single_slot(session, 1, "QB", 0, 124)
    assert success is True
    
    # Verify update
    rows = list_depth_chart(session, 1)
    qb_row = next(r for r in rows if r.slot == "QB" and r.order_index == 0)
    assert qb_row.player_id == 124

def test_clear_depth_chart(session: Session):
    """Test clearing depth chart."""
    # Create entries
    entries = [
        DepthChart(team_id=1, slot="QB", order_index=0, player_id=123),
        DepthChart(team_id=1, slot="RB", order_index=0, player_id=124)
    ]
    
    for entry in entries:
        session.add(entry)
    session.commit()
    
    # Clear depth chart
    clear_depth_chart(session, 1)
    
    # Verify cleared
    rows = list_depth_chart(session, 1)
    assert len(rows) == 0

def test_get_depth_chart_summary(session: Session):
    """Test depth chart summary."""
    # Create entries
    entries = [
        DepthChart(team_id=1, slot="QB", order_index=0, player_id=123),
        DepthChart(team_id=1, slot="RB", order_index=0, player_id=124),
        DepthChart(team_id=1, slot="QB", order_index=1, player_id=None)
    ]
    
    for entry in entries:
        session.add(entry)
    session.commit()
    
    # Get summary
    summary = get_depth_chart_summary(session, 1)
    assert summary["team_id"] == 1
    assert summary["total_slots"] == 3
    assert summary["filled_slots"] == 2
    assert summary["empty_slots"] == 1

def test_lineup_adapter_offense_group():
    """Test offense group extraction."""
    slots = {
        "QB": [123],
        "RB": [124],
        "WR1": [125],
        "WR2": [126],
        "WR3": [127],
        "TE": [128],
        "LT": [129],
        "LG": [130],
        "C": [131],
        "RG": [132],
        "RT": [133]
    }
    
    offense = offense_group(slots)
    assert len(offense) == 11
    assert 123 in offense  # QB
    assert 124 in offense  # RB

def test_lineup_adapter_defense_group():
    """Test defense group extraction."""
    slots = {
        "EDGE1": [201],
        "EDGE2": [202],
        "DL1": [203],
        "DL2": [204],
        "LB1": [205],
        "LB2": [206],
        "CB1": [207],
        "CB2": [208],
        "S1": [209],
        "S2": [210]
    }
    
    defense = defense_group(slots)
    assert len(defense) == 10
    assert 201 in defense  # EDGE1
    assert 205 in defense  # LB1

def test_lineup_adapter_special_group():
    """Test special teams group extraction."""
    slots = {
        "K": [301],
        "P": [302],
        "LS": [303],
        "KR": [304],
        "PR": [305]
    }
    
    special = special_group(slots)
    assert special["K"] == 301
    assert special["P"] == 302
    assert special["LS"] == 303
    assert special["KR"] == 304
    assert special["PR"] == 305

def test_get_starting_lineup():
    """Test getting starting lineup."""
    slots = {
        "QB": [123, 124],
        "RB": [125, 126],
        "K": [127]
    }
    
    starters = get_starting_lineup(slots)
    assert starters["QB"] == 123
    assert starters["RB"] == 125
    assert starters["K"] == 127

def test_get_backup_lineup():
    """Test getting backup lineup."""
    slots = {
        "QB": [123, 124, 125],
        "RB": [126, 127],
        "K": [128]
    }
    
    backups = get_backup_lineup(slots)
    assert backups["QB"] == [124, 125]
    assert backups["RB"] == [127]
    assert backups["K"] == []

def test_validate_lineup_completeness():
    """Test lineup completeness validation."""
    # Complete lineup
    complete_slots = {
        "QB": [123],
        "K": [124],
        "P": [125]
    }
    
    issues = validate_lineup_completeness(complete_slots)
    assert len(issues["errors"]) == 0
    
    # Incomplete lineup
    incomplete_slots = {
        "QB": [123],
        "K": [],
        "P": [125]
    }
    
    issues = validate_lineup_completeness(incomplete_slots)
    assert len(issues["errors"]) > 0
    assert any("Missing K" in error for error in issues["errors"])

def test_get_lineup_summary():
    """Test lineup summary."""
    slots = {
        "QB": [123, 124],
        "RB": [125],
        "K": [126],
        "P": [],
        "LS": [127]
    }
    
    summary = get_lineup_summary(slots)
    assert summary["total_players"] == 5
    assert summary["filled_slots"] == 4
    assert summary["empty_slots"] == 1

def test_api_endpoints(client, seeded_db):
    """Test all API endpoints."""
    # Test get depth chart
    r = client.get("/api/v1/roster/depth_chart?team_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test set depth chart
    r = client.post("/api/v1/roster/depth_chart", json={
        "team_id": 1,
        "items": [
            {"slot": "QB", "order_index": 0, "player_id": 123},
            {"slot": "RB", "order_index": 0, "player_id": 124}
        ]
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True
    
    # Test auto fill
    r = client.post("/api/v1/roster/auto_fill?team_id=1&season=2024&week=1&game_id=1001&opponent_id=2")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    
    # Test lineup for game
    r = client.get("/api/v1/roster/lineup_for_game?team_id=1&season=2024&week=1&game_id=1001&opponent_id=2")
    assert r.status_code == 200
    assert "slots" in r.json()
    
    # Test eligibility
    r = client.get("/api/v1/roster/eligibility")
    assert r.status_code == 200
    assert "slots" in r.json()
    assert "eligibility" in r.json()
    
    # Test depth chart by slot
    r = client.get("/api/v1/roster/depth_chart/by_slot?team_id=1")
    assert r.status_code == 200
    
    # Test validate depth chart
    r = client.get("/api/v1/roster/depth_chart/validate?team_id=1")
    assert r.status_code == 200
    assert "errors" in r.json()
    assert "warnings" in r.json()
    
    # Test available players
    r = client.get("/api/v1/roster/depth_chart/available_players?team_id=1&slot=QB")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test update single slot
    r = client.post("/api/v1/roster/depth_chart/update_slot", json={
        "team_id": 1,
        "slot": "QB",
        "order_index": 0,
        "player_id": 123
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True
    
    # Test clear depth chart
    r = client.post("/api/v1/roster/depth_chart/clear?team_id=1")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    
    # Test depth chart summary
    r = client.get("/api/v1/roster/depth_chart/summary?team_id=1")
    assert r.status_code == 200
    assert "team_id" in r.json()
    
    # Test injured players
    r = client.get("/api/v1/roster/depth_chart/injured_players?team_id=1&season=2024&week=1&game_id=1001&opponent_id=2")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test depth chart with player info
    r = client.get("/api/v1/roster/depth_chart/with_player_info?team_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test offense lineup
    r = client.get("/api/v1/roster/depth_chart/offense?team_id=1")
    assert r.status_code == 200
    
    # Test defense lineup
    r = client.get("/api/v1/roster/depth_chart/defense?team_id=1")
    assert r.status_code == 200
    
    # Test special teams lineup
    r = client.get("/api/v1/roster/depth_chart/special_teams?team_id=1")
    assert r.status_code == 200
    
    # Test starters
    r = client.get("/api/v1/roster/depth_chart/starters?team_id=1")
    assert r.status_code == 200
    
    # Test backups
    r = client.get("/api/v1/roster/depth_chart/backups?team_id=1")
    assert r.status_code == 200
    
    # Test position depth
    r = client.get("/api/v1/roster/depth_chart/position/QB?team_id=1")
    assert r.status_code == 200
    
    # Test empty slots
    r = client.get("/api/v1/roster/depth_chart/empty_slots?team_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test filled slots
    r = client.get("/api/v1/roster/depth_chart/filled_slots?team_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_error_handling(client, seeded_db):
    """Test error handling in API endpoints."""
    # Test invalid slot
    r = client.post("/api/v1/roster/depth_chart", json={
        "team_id": 1,
        "items": [
            {"slot": "INVALID", "order_index": 0, "player_id": 123}
        ]
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True  # Invalid slots are ignored
    
    # Test update invalid slot
    r = client.post("/api/v1/roster/depth_chart/update_slot", json={
        "team_id": 1,
        "slot": "INVALID",
        "order_index": 0,
        "player_id": 123
    })
    assert r.status_code == 200
    assert r.json()["ok"] is False

def test_position_eligibility():
    """Test position eligibility rules."""
    # Test QB eligibility
    assert "QB" in ELIGIBILITY["QB"]
    
    # Test WR eligibility
    assert "WR" in ELIGIBILITY["WR1"]
    assert "WR" in ELIGIBILITY["WR2"]
    assert "WR" in ELIGIBILITY["WR3"]
    
    # Test OL eligibility
    assert "LT" in ELIGIBILITY["LT"]
    assert "T" in ELIGIBILITY["LT"]
    assert "OL" in ELIGIBILITY["LT"]
    
    # Test special teams eligibility
    assert "K" in ELIGIBILITY["K"]
    assert "P" in ELIGIBILITY["P"]
    assert "LS" in ELIGIBILITY["LS"]
    assert "C" in ELIGIBILITY["LS"]

def test_auto_fill_with_limited_players(session: Session):
    """Test auto-fill with limited player pool."""
    # Create only QB and K
    players = [
        Player(name="QB1", team_id=1, pos="QB", overall=85),
        Player(name="K1", team_id=1, pos="K", overall=70)
    ]
    
    for player in players:
        session.add(player)
    session.commit()
    
    # Auto-fill
    auto_fill(session, 1, 2024, 1, 1001, 2)
    
    # Check that QB and K are filled
    rows = list_depth_chart(session, 1)
    qb_rows = [r for r in rows if r.slot == "QB" and r.order_index == 0]
    k_rows = [r for r in rows if r.slot == "K" and r.order_index == 0]
    
    assert len(qb_rows) == 1
    assert qb_rows[0].player_id == players[0].player_id
    assert len(k_rows) == 1
    assert k_rows[0].player_id == players[1].player_id

def test_depth_chart_with_player_info(session: Session):
    """Test depth chart with player information."""
    # Create player
    player = Player(name="Test QB", team_id=1, pos="QB", overall=85, age=25)
    session.add(player)
    session.commit()
    session.refresh(player)
    
    # Create depth chart entry
    entry = DepthChart(team_id=1, slot="QB", order_index=0, player_id=player.player_id)
    session.add(entry)
    session.commit()
    
    # Get depth chart with player info
    result = get_depth_chart_with_player_info(session, 1)
    
    assert len(result) == 1
    assert result[0]["slot"] == "QB"
    assert result[0]["player_id"] == player.player_id
    assert result[0]["player_info"]["name"] == "Test QB"
    assert result[0]["player_info"]["pos"] == "QB"
    assert result[0]["player_info"]["overall"] == 85

