import pytest
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.gameplan import (
    GameplanSelection, OffAgg, DefAgg, Coverage, BlitzStrategy, RZOff, RZDef
)
from app.services.gameplan_mapping import (
    build_deltas, GameplanDeltas, merge, OFF_AGG_MAP, DEF_AGG_MAP, 
    COVERAGE_MAP, BLITZ_MAP, RZ_OFF_MAP, RZ_DEF_MAP
)
from app.engine.gameplan_apply import (
    apply_gameplan, EngineConfig, create_default_config, apply_gameplan_to_default
)

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_off_agg_maps_as_expected():
    """Test that offensive aggressiveness maps to expected deltas."""
    d = build_deltas(OffAgg.VERY_AGGRESSIVE, DefAgg.BALANCED, Coverage.HYBRID, 
                     BlitzStrategy.STANDARD, RZOff.BALANCED, RZDef.BALANCED)
    assert d.pass_bias_delta > 0 and d.depth_bias_delta > 0
    assert d.go4it_cutoff_delta < 0 and d.two_point_tendency_delta > 0

def test_blitz_heavy_multiplies():
    """Test that blitz heavy strategy multiplies blitz rate correctly."""
    d = build_deltas(OffAgg.BALANCED, DefAgg.AGGRESSIVE, Coverage.HYBRID, 
                     BlitzStrategy.BLITZ_HEAVY, RZOff.BALANCED, RZDef.BALANCED)
    assert d.base_blitz_rate_delta > 0
    assert abs(d.blitz_rate_multiplier - 1.20) < 1e-9

def test_rz_off_and_def_adjustments_stack():
    """Test that red zone offense and defense adjustments stack correctly."""
    d = build_deltas(OffAgg.BALANCED, DefAgg.BALANCED, Coverage.HYBRID, 
                     BlitzStrategy.STANDARD, RZOff.PLAY_ACTION_HEAVY, RZDef.PRESSURE_QB)
    assert d.rz_pass_bias_delta > 0 and d.rz_shot_play_rate_delta > 0
    assert d.rz_blitz_rate_delta > 0

def test_api_roundtrip_save_and_get(session: Session):
    """Test API roundtrip save and get functionality."""
    from app.ui.api_gameplan import get_gameplan, save_gameplan
    from app.models.gameplan import GameplanDTO
    
    # Create a gameplan (HC only)
    gameplan_data = GameplanDTO(
        season=2031, week=7, team_id=1, opponent_team_id=2, coach_id=101,
        coach_role="HC",  # Only HCs can set gameplans
        off_agg=OffAgg.AGGRESSIVE, def_agg=DefAgg.CONSERVATIVE,
        coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.BLITZ_HEAVY,
        rz_off=RZOff.SPREAD_SHOT, rz_def=RZDef.BEND
    )
    
    # Save it
    saved = save_gameplan(gameplan_data, session)
    assert saved.blitz_strategy == BlitzStrategy.BLITZ_HEAVY
    assert saved.coach_role == "HC"
    
    # Get it back
    retrieved = get_gameplan(2031, 7, 1, 2, 101, session)
    assert retrieved.blitz_strategy == BlitzStrategy.BLITZ_HEAVY
    assert retrieved.off_agg == OffAgg.AGGRESSIVE
    assert retrieved.def_agg == DefAgg.CONSERVATIVE
    assert retrieved.coach_role == "HC"

def test_deltas_endpoint(session: Session):
    """Test the deltas endpoint."""
    from app.ui.api_gameplan import get_deltas, save_gameplan
    from app.models.gameplan import GameplanDTO
    
    # Save a gameplan first (HC only)
    gameplan_data = GameplanDTO(
        season=2031, week=7, team_id=1, opponent_team_id=2, coach_id=101,
        coach_role="HC",  # Only HCs can set gameplans
        off_agg=OffAgg.VERY_AGGRESSIVE, def_agg=DefAgg.BALANCED,
        coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.STANDARD,
        rz_off=RZOff.BALANCED, rz_def=RZDef.BALANCED
    )
    save_gameplan(gameplan_data, session)
    
    # Get deltas
    deltas = get_deltas(2031, 7, 1, 2, 101, session)
    
    # Should have aggressive offensive deltas
    assert deltas.pass_bias_delta > 0
    assert deltas.depth_bias_delta > 0
    assert deltas.go4it_cutoff_delta < 0
    assert deltas.two_point_tendency_delta > 0

def test_hc_only_validation(session: Session):
    """Test that only HCs can save gameplans."""
    from app.ui.api_gameplan import save_gameplan
    from app.models.gameplan import GameplanDTO
    from fastapi import HTTPException
    
    # Try to save as OC (should fail)
    oc_gameplan = GameplanDTO(
        season=2031, week=7, team_id=1, opponent_team_id=2, coach_id=102,
        coach_role="OC",  # OC cannot set gameplans
        off_agg=OffAgg.AGGRESSIVE, def_agg=DefAgg.BALANCED,
        coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.STANDARD,
        rz_off=RZOff.BALANCED, rz_def=RZDef.BALANCED
    )
    
    try:
        save_gameplan(oc_gameplan, session)
        assert False, "OC should not be able to save gameplans"
    except HTTPException as e:
        assert e.status_code == 403
        assert "Only Head Coaches (HC) can set gameplans" in str(e.detail)
    
    # Try to save as DC (should fail)
    dc_gameplan = GameplanDTO(
        season=2031, week=7, team_id=1, opponent_team_id=2, coach_id=103,
        coach_role="DC",  # DC cannot set gameplans
        off_agg=OffAgg.BALANCED, def_agg=DefAgg.AGGRESSIVE,
        coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.STANDARD,
        rz_off=RZOff.BALANCED, rz_def=RZDef.BALANCED
    )
    
    try:
        save_gameplan(dc_gameplan, session)
        assert False, "DC should not be able to save gameplans"
    except HTTPException as e:
        assert e.status_code == 403
        assert "Only Head Coaches (HC) can set gameplans" in str(e.detail)
    
    # Try to save as AC (should fail)
    ac_gameplan = GameplanDTO(
        season=2031, week=7, team_id=1, opponent_team_id=2, coach_id=104,
        coach_role="AC1",  # AC cannot set gameplans
        off_agg=OffAgg.BALANCED, def_agg=DefAgg.BALANCED,
        coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.STANDARD,
        rz_off=RZOff.BALANCED, rz_def=RZDef.BALANCED
    )
    
    try:
        save_gameplan(ac_gameplan, session)
        assert False, "AC should not be able to save gameplans"
    except HTTPException as e:
        assert e.status_code == 403
        assert "Only Head Coaches (HC) can set gameplans" in str(e.detail)
    
    # HC should be able to save (should succeed)
    hc_gameplan = GameplanDTO(
        season=2031, week=7, team_id=1, opponent_team_id=2, coach_id=101,
        coach_role="HC",  # HC can set gameplans
        off_agg=OffAgg.AGGRESSIVE, def_agg=DefAgg.AGGRESSIVE,
        coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.STANDARD,
        rz_off=RZOff.BALANCED, rz_def=RZDef.BALANCED
    )
    
    saved = save_gameplan(hc_gameplan, session)
    assert saved.coach_role == "HC"
    assert saved.off_agg == OffAgg.AGGRESSIVE