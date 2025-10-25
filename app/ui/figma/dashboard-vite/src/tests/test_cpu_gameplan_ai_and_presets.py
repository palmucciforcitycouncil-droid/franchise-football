import pytest
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.gameplan import GameplanSelection, OffAgg, DefAgg, Coverage, BlitzStrategy, RZOff, RZDef
from app.services.gameplan_presets import (
    apply_preset_balanced, apply_preset_air_it_out, apply_preset_ground_pound,
    apply_preset_heat_qb, apply_preset_bend_rz, get_available_presets, apply_preset
)
from app.services.gameplan_cpu_ai import (
    choose_cpu_gameplan, choose_cpu_gameplan_for_week, choose_cpu_gameplan_for_team,
    get_cpu_gameplan_reasoning, OpponentProfile, load_opponent_profile
)

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_preset_balanced(session: Session):
    """Test that balanced preset applies correct values."""
    row = apply_preset_balanced(session, 2024, 3, 1, 2)
    
    assert row.off_agg == OffAgg.BALANCED
    assert row.def_agg == DefAgg.BALANCED
    assert row.coverage == Coverage.HYBRID
    assert row.blitz_strategy == BlitzStrategy.STANDARD
    assert row.rz_off == RZOff.BALANCED
    assert row.rz_def == RZDef.BALANCED
    assert row.season == 2024
    assert row.week == 3
    assert row.team_id == 1
    assert row.opponent_team_id == 2

def test_preset_air_it_out(session: Session):
    """Test that air-it-out preset applies aggressive passing values."""
    row = apply_preset_air_it_out(session, 2024, 3, 1, 2)
    
    assert row.off_agg == OffAgg.VERY_AGGRESSIVE
    assert row.def_agg == DefAgg.CONSERVATIVE
    assert row.coverage == Coverage.ZONE_HEAVY
    assert row.blitz_strategy == BlitzStrategy.SELECTIVE
    assert row.rz_off == RZOff.SPREAD_SHOT
    assert row.rz_def == RZDef.BEND

def test_preset_ground_pound(session: Session):
    """Test that ground-pound preset applies conservative run values."""
    row = apply_preset_ground_pound(session, 2024, 3, 1, 2)
    
    assert row.off_agg == OffAgg.VERY_CONSERVATIVE
    assert row.def_agg == DefAgg.BALANCED
    assert row.coverage == Coverage.HYBRID
    assert row.blitz_strategy == BlitzStrategy.STANDARD
    assert row.rz_off == RZOff.POWER_RUN
    assert row.rz_def == RZDef.RUN_SELLOUT

def test_preset_heat_qb(session: Session):
    """Test that heat-QB preset applies aggressive defense values."""
    row = apply_preset_heat_qb(session, 2024, 3, 1, 2)
    
    assert row.off_agg == OffAgg.BALANCED
    assert row.def_agg == DefAgg.AGGRESSIVE
    assert row.coverage == Coverage.HYBRID
    assert row.blitz_strategy == BlitzStrategy.BLITZ_HEAVY
    assert row.rz_off == RZOff.BALANCED
    assert row.rz_def == RZDef.PRESSURE_QB

def test_preset_bend_rz(session: Session):
    """Test that bend-don't-break preset applies conservative values."""
    row = apply_preset_bend_rz(session, 2024, 3, 1, 2)
    
    assert row.off_agg == OffAgg.CONSERVATIVE
    assert row.def_agg == DefAgg.CONSERVATIVE
    assert row.coverage == Coverage.ZONE_HEAVY
    assert row.blitz_strategy == BlitzStrategy.SELECTIVE
    assert row.rz_off == RZOff.PLAY_ACTION_HEAVY
    assert row.rz_def == RZDef.BEND

def test_preset_upsert(session: Session):
    """Test that presets can update existing gameplan selections."""
    # Apply preset first time
    row1 = apply_preset_balanced(session, 2024, 3, 1, 2)
    assert row1.off_agg == OffAgg.BALANCED
    
    # Apply different preset - should update existing
    row2 = apply_preset_air_it_out(session, 2024, 3, 1, 2)
    assert row2.id == row1.id  # Same record
    assert row2.off_agg == OffAgg.VERY_AGGRESSIVE  # Updated value

def test_get_available_presets():
    """Test that get_available_presets returns all preset names."""
    presets = get_available_presets()
    expected = ["balanced", "air_it_out", "ground_pound", "heat_qb", "bend_rz"]
    
    assert len(presets) == len(expected)
    for preset in expected:
        assert preset in presets

def test_apply_preset_by_name(session: Session):
    """Test that apply_preset works with preset names."""
    row = apply_preset(session, "heat_qb", 2024, 3, 1, 2)
    assert row.blitz_strategy == BlitzStrategy.BLITZ_HEAVY
    
    # Test invalid preset name
    with pytest.raises(ValueError):
        apply_preset(session, "invalid_preset", 2024, 3, 1, 2)

def test_cpu_gameplan_basic(session: Session):
    """Test that CPU AI generates a valid gameplan."""
    row = choose_cpu_gameplan(session, 2024, 3, 1, 2, seed=42)
    
    # Should have valid enum values
    assert row.off_agg in [OffAgg.VERY_CONSERVATIVE, OffAgg.CONSERVATIVE, OffAgg.BALANCED, OffAgg.AGGRESSIVE, OffAgg.VERY_AGGRESSIVE]
    assert row.def_agg in [DefAgg.VERY_CONSERVATIVE, DefAgg.CONSERVATIVE, DefAgg.BALANCED, DefAgg.AGGRESSIVE, DefAgg.VERY_AGGRESSIVE]
    assert row.coverage in [Coverage.MAN_HEAVY, Coverage.HYBRID, Coverage.ZONE_HEAVY]
    assert row.blitz_strategy in [BlitzStrategy.SELECTIVE, BlitzStrategy.STANDARD, BlitzStrategy.BLITZ_HEAVY]
    assert row.rz_off in [RZOff.POWER_RUN, RZOff.BALANCED, RZOff.PLAY_ACTION_HEAVY, RZOff.SPREAD_SHOT]
    assert row.rz_def in [RZDef.BEND, RZDef.BALANCED, RZDef.RUN_SELLOUT, RZDef.PRESSURE_QB]
    
    # Should have correct metadata
    assert row.season == 2024
    assert row.week == 3
    assert row.team_id == 1
    assert row.opponent_team_id == 2

def test_cpu_gameplan_deterministic(session: Session):
    """Test that CPU AI is deterministic with same seed."""
    row1 = choose_cpu_gameplan(session, 2024, 3, 1, 2, seed=123)
    row2 = choose_cpu_gameplan(session, 2024, 3, 1, 2, seed=123)
    
    # Should be identical with same seed
    assert row1.off_agg == row2.off_agg
    assert row1.def_agg == row2.def_agg
    assert row1.coverage == row2.coverage
    assert row1.blitz_strategy == row2.blitz_strategy
    assert row1.rz_off == row2.rz_off
    assert row1.rz_def == row2.rz_def

def test_cpu_gameplan_different_seeds(session: Session):
    """Test that different seeds can produce different results."""
    row1 = choose_cpu_gameplan(session, 2024, 3, 1, 2, seed=123)
    row2 = choose_cpu_gameplan(session, 2024, 3, 1, 2, seed=456)
    
    # Different seeds might produce different results (though not guaranteed)
    # At least test that the function doesn't crash with different seeds
    assert row1.season == row2.season
    assert row1.week == row2.week
    assert row1.team_id == row2.team_id
    assert row1.opponent_team_id == row2.opponent_team_id

def test_cpu_gameplan_upsert(session: Session):
    """Test that CPU AI can update existing gameplan selections."""
    # Create initial selection
    initial = GameplanSelection(season=2024, week=3, team_id=1, opponent_team_id=2, off_agg=OffAgg.BALANCED)
    session.add(initial); session.commit(); session.refresh(initial)
    
    # CPU AI should update existing
    updated = choose_cpu_gameplan(session, 2024, 3, 1, 2, seed=42)
    assert updated.id == initial.id  # Same record
    assert updated.off_agg != OffAgg.BALANCED  # Should be different

def test_cpu_gameplan_for_team(session: Session):
    """Test that CPU AI can generate gameplans for a team vs multiple opponents."""
    opponents = [2, 3, 4]
    choose_cpu_gameplan_for_team(session, 2024, 3, 1, opponents, seed=42)
    
    # Check that gameplans were created for all opponents
    for opp_id in opponents:
        row = session.exec(select(GameplanSelection).where(
            GameplanSelection.season == 2024,
            GameplanSelection.week == 3,
            GameplanSelection.team_id == 1,
            GameplanSelection.opponent_team_id == opp_id
        )).first()
        assert row is not None
        assert row.off_agg is not None

def test_cpu_gameplan_reasoning(session: Session):
    """Test that CPU AI reasoning is returned correctly."""
    reasoning = get_cpu_gameplan_reasoning(session, 2024, 3, 1, 2)
    
    assert "opponent_profile" in reasoning
    assert "offensive_reasoning" in reasoning
    assert "defensive_reasoning" in reasoning
    assert "red_zone_reasoning" in reasoning
    
    # Check that opponent profile has expected fields
    profile = reasoning["opponent_profile"]
    assert "pass_rate" in profile
    assert "deep_rate" in profile
    assert "sack_rate_allowed" in profile
    assert "run_success_rate" in profile
    assert "rz_td_offense" in profile
    assert "rz_td_defense_allowed" in profile
    assert "explosives_rate" in profile
    assert "ol_strength" in profile
    assert "dl_strength" in profile
    assert "secondary_strength" in profile

def test_opponent_profile_fallback():
    """Test that opponent profile fallback works."""
    profile = load_opponent_profile(None, 2024, 3, 1)
    
    assert isinstance(profile, OpponentProfile)
    assert 0.0 <= profile.pass_rate <= 1.0
    assert 0.0 <= profile.deep_rate <= 1.0
    assert 0.0 <= profile.sack_rate_allowed <= 1.0
    assert 0.0 <= profile.run_success_rate <= 1.0
    assert 0.0 <= profile.rz_td_offense <= 1.0
    assert 0.0 <= profile.rz_td_defense_allowed <= 1.0
    assert 0.0 <= profile.explosives_rate <= 1.0
    assert 0.0 <= profile.ol_strength <= 1.0
    assert 0.0 <= profile.dl_strength <= 1.0
    assert 0.0 <= profile.secondary_strength <= 1.0

def test_cpu_week_no_crash(session: Session):
    """Test that CPU week generation doesn't crash even without schedule model."""
    # This should not crash even if schedule model doesn't exist
    choose_cpu_gameplan_for_week(session, 2024, 3, seed=42)
    # If we get here without exception, test passes

def test_api_presets_roundtrip(client, seeded_db):
    """Test API roundtrip for presets."""
    # Apply a preset via API
    body = {
        "preset": "air_it_out", 
        "season": 2031, 
        "week": 3, 
        "team_id": 1, 
        "opponent_team_id": 2
    }
    r = client.post("/api/v1/gameplan/tools/apply_preset", json=body)
    assert r.status_code == 200
    assert r.json()["ok"]
    
    # Verify via existing gameplan get endpoint
    r = client.get("/api/v1/gameplan/get", params={"season": 2031, "week": 3, "team_id": 1, "opponent_team_id": 2})
    assert r.status_code == 200
    row = r.json()
    assert row["off_agg"] == "Very Aggressive"
    assert row["coverage"] == "Zone-Heavy"

def test_api_cpu_pick_basic(client, seeded_db):
    """Test API CPU pick functionality."""
    body = {
        "season": 2031, 
        "week": 4, 
        "team_id": 10, 
        "opponent_team_id": 11
    }
    r = client.post("/api/v1/gameplan/tools/cpu_pick", json=body)
    assert r.status_code == 200
    assert r.json()["ok"]
    
    sel = r.json()["selection"]
    assert sel["team_id"] == 10
    assert sel["opponent_team_id"] == 11
    assert sel["off_agg"] in ["Balanced", "Aggressive", "Conservative", "Very Aggressive", "Very Conservative"]

def test_api_cpu_week_no_crash(client, seeded_db):
    """Test API CPU week generation doesn't crash."""
    r = client.post("/api/v1/gameplan/tools/cpu_pick_week", json={"season": 2031, "week": 5})
    assert r.status_code == 200
    assert r.json()["ok"]

def test_api_get_presets(client, seeded_db):
    """Test API get presets endpoint."""
    r = client.get("/api/v1/gameplan/tools/presets")
    assert r.status_code == 200
    
    presets = r.json()["presets"]
    assert "balanced" in presets
    assert "air_it_out" in presets
    assert "ground_pound" in presets
    assert "heat_qb" in presets
    assert "bend_rz" in presets

def test_api_get_preset_info(client, seeded_db):
    """Test API get preset info endpoint."""
    r = client.get("/api/v1/gameplan/tools/presets/info")
    assert r.status_code == 200
    
    presets = r.json()
    assert len(presets) == 5
    
    # Check that each preset has required fields
    for preset in presets:
        assert "name" in preset
        assert "description" in preset
        assert "offensive_aggressiveness" in preset
        assert "defensive_aggressiveness" in preset
        assert "coverage_scheme" in preset
        assert "blitz_strategy" in preset
        assert "red_zone_offense" in preset
        assert "red_zone_defense" in preset

def test_api_cpu_reasoning(client, seeded_db):
    """Test API CPU reasoning endpoint."""
    r = client.get("/api/v1/gameplan/tools/cpu_pick/reasoning", params={
        "season": 2031, "week": 3, "team_id": 1, "opponent_team_id": 2
    })
    assert r.status_code == 200
    assert r.json()["ok"]
    
    reasoning = r.json()["reasoning"]
    assert "opponent_profile" in reasoning
    assert "offensive_reasoning" in reasoning
    assert "defensive_reasoning" in reasoning
    assert "red_zone_reasoning" in reasoning

def test_api_batch_preset(client, seeded_db):
    """Test API batch preset application."""
    body = {
        "preset": "balanced",
        "season": 2031,
        "week": 3,
        "matchups": [
            {"team_id": 1, "opponent_team_id": 2},
            {"team_id": 3, "opponent_team_id": 4}
        ]
    }
    r = client.post("/api/v1/gameplan/tools/apply_preset_batch", json=body)
    assert r.status_code == 200
    assert r.json()["ok"]
    
    selections = r.json()["selections"]
    assert len(selections) == 2
    for sel in selections:
        assert sel["off_agg"] == "Balanced"

def test_api_gameplan_stats(client, seeded_db):
    """Test API gameplan stats endpoint."""
    # First create some gameplans
    client.post("/api/v1/gameplan/tools/apply_preset", json={
        "preset": "balanced", "season": 2031, "week": 3, "team_id": 1, "opponent_team_id": 2
    })
    client.post("/api/v1/gameplan/tools/apply_preset", json={
        "preset": "air_it_out", "season": 2031, "week": 3, "team_id": 3, "opponent_team_id": 4
    })
    
    # Get stats
    r = client.get("/api/v1/gameplan/tools/stats", params={"season": 2031, "week": 3})
    assert r.status_code == 200
    assert r.json()["ok"]
    
    stats = r.json()["stats"]
    assert stats["total_selections"] == 2
    assert "offensive_aggressiveness" in stats
    assert "defensive_aggressiveness" in stats
    assert "coverage_scheme" in stats
    assert "blitz_strategy" in stats
    assert "red_zone_offense" in stats
    assert "red_zone_defense" in stats

