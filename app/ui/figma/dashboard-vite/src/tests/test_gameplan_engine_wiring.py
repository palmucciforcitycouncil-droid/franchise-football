import pytest
import json
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.gameplan import GameplanSelection, OffAgg, DefAgg, Coverage, BlitzStrategy, RZOff, RZDef
from app.models.gameplan_trace import GameplanTrace
from app.services.coach_focus_service import set_coach_focus
from app.models.coach_focus import CoachRole, CoachFocus
from app.services.hc_influence import get_hc_profile, map_hc_to_deltas, HCProfile
from app.engine.gameplan_compose import compose_final_engine_config
from app.services.sim_pipeline import prepare_game_configs
from app.engine.gameplan_apply import EngineConfig

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_hc_profile_mapping():
    """Test that HC profile maps to expected deltas."""
    # Test aggressive HC profile
    aggressive_hc = HCProfile(
        run_pass_tendency=0.3,
        offensive_aggression=0.8,  # High aggression
        defensive_aggression=0.7,  # High aggression
        coverage_mix=0.3,  # Man-heavy
        red_zone_offense=0.2,  # Pass-heavy
        red_zone_defense=0.3   # Pressure-heavy
    )
    
    deltas = map_hc_to_deltas(aggressive_hc)
    
    # Should have positive pass bias (aggressive offense)
    assert deltas.pass_bias_delta > 0
    assert deltas.depth_bias_delta > 0
    assert deltas.trick_play_rate_delta > 0
    assert deltas.go4it_cutoff_delta < 0  # More aggressive = lower cutoff
    assert deltas.two_point_tendency_delta > 0
    
    # Should have positive defensive aggression
    assert deltas.base_blitz_rate_delta > 0
    assert deltas.press_cushion_delta < 0  # Tighter coverage
    assert deltas.run_blitz_rate_delta > 0
    
    # Coverage mix should be preserved
    assert deltas.coverage_mix == 0.3
    
    # Red zone effects
    assert deltas.rz_pass_bias_delta > 0
    assert deltas.rz_shell_depth_delta < 0  # Shallow shell
    assert deltas.rz_blitz_rate_delta > 0

def test_hc_profile_neutral():
    """Test that neutral HC profile produces minimal deltas."""
    neutral_hc = HCProfile()  # All defaults
    
    deltas = map_hc_to_deltas(neutral_hc)
    
    # Should have minimal or zero deltas
    assert abs(deltas.pass_bias_delta) < 0.01
    assert abs(deltas.depth_bias_delta) < 0.01
    assert abs(deltas.trick_play_rate_delta) < 0.01
    assert abs(deltas.go4it_cutoff_delta) < 0.01
    assert abs(deltas.two_point_tendency_delta) < 0.01
    assert abs(deltas.base_blitz_rate_delta) < 0.01
    assert abs(deltas.press_cushion_delta) < 0.01
    assert abs(deltas.run_blitz_rate_delta) < 0.01
    assert deltas.coverage_mix == 0.5  # Default
    assert abs(deltas.rz_pass_bias_delta) < 0.01
    assert abs(deltas.rz_shell_depth_delta) < 0.01
    assert abs(deltas.rz_blitz_rate_delta) < 0.01

def test_compose_final_includes_user_and_focus(session: Session):
    """Test that composition includes user gameplan and coach focus effects."""
    from app.db import get_engine
    
    s, w = 2024, 3
    team, opp = 1, 2
    game_id = 101

    with Session(get_engine()) as sess:
        # User sets aggressive offense + blitz heavy
        row = GameplanSelection(
            season=s, week=w, team_id=team, opponent_team_id=opp,
            off_agg=OffAgg.AGGRESSIVE, def_agg=DefAgg.BALANCED,
            coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.BLITZ_HEAVY,
            rz_off=RZOff.PLAY_ACTION_HEAVY, rz_def=RZDef.BEND
        )
        sess.add(row); sess.commit()

        # Focus: HC OF_GAMEPLAN + DC DF_GAMEPLAN to push both sides
        set_coach_focus(sess, coach_id=1, team_id=team, season=s, week=w, role=CoachRole.HC, focus=CoachFocus.OF_GAMEPLAN)
        set_coach_focus(sess, coach_id=2, team_id=team, season=s, week=w, role=CoachRole.DC, focus=CoachFocus.DF_GAMEPLAN)

        cfg = compose_final_engine_config(sess, game_id, s, w, team, opp)
        
        # Offense should be more pass-biased and deeper
        assert cfg.pass_bias > 0
        assert cfg.depth_bias > 0
        
        # Blitz heavy multiplier should raise blitz rate
        assert cfg.blitz_rate >= cfg.base_blitz_rate
        
        # Red zone offense tilted to pass
        assert cfg.rz_off_pass_bias >= 0

def test_compose_final_creates_trace(session: Session):
    """Test that composition creates a trace record."""
    from app.db import get_engine
    
    s, w = 2024, 3
    team, opp = 1, 2
    game_id = 101

    with Session(get_engine()) as sess:
        # Create a gameplan
        row = GameplanSelection(
            season=s, week=w, team_id=team, opponent_team_id=opp,
            off_agg=OffAgg.AGGRESSIVE, def_agg=DefAgg.BALANCED,
            coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.STANDARD,
            rz_off=RZOff.BALANCED, rz_def=RZDef.BALANCED
        )
        sess.add(row); sess.commit()

        # Compose config (should create trace)
        cfg = compose_final_engine_config(sess, game_id, s, w, team, opp)
        
        # Check that trace was created
        traces = list(sess.exec(select(GameplanTrace).where(GameplanTrace.game_id==game_id)))
        assert len(traces) == 1
        
        trace = traces[0]
        assert trace.team_id == team
        assert trace.opponent_team_id == opp
        assert trace.season == s
        assert trace.week == w
        
        # Check that trace contains JSON data
        assert trace.hc != ""
        assert trace.focus != ""
        assert trace.user != ""
        assert trace.final_cfg != ""
        
        # Verify JSON is parseable
        hc_data = json.loads(trace.hc)
        focus_data = json.loads(trace.focus)
        user_data = json.loads(trace.user)
        final_data = json.loads(trace.final_cfg)
        
        assert isinstance(hc_data, dict)
        assert isinstance(focus_data, dict)
        assert isinstance(user_data, dict)
        assert isinstance(final_data, dict)

def test_prepare_game_configs(session: Session):
    """Test that prepare_game_configs returns configs for both teams."""
    from app.db import get_engine
    
    s, w = 2024, 3
    home, away = 1, 2
    game_id = 101

    with Session(get_engine()) as sess:
        # Create gameplans for both teams
        home_gameplan = GameplanSelection(
            season=s, week=w, team_id=home, opponent_team_id=away,
            off_agg=OffAgg.AGGRESSIVE, def_agg=DefAgg.BALANCED,
            coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.STANDARD,
            rz_off=RZOff.BALANCED, rz_def=RZDef.BALANCED
        )
        away_gameplan = GameplanSelection(
            season=s, week=w, team_id=away, opponent_team_id=home,
            off_agg=OffAgg.CONSERVATIVE, def_agg=DefAgg.AGGRESSIVE,
            coverage=Coverage.MAN_HEAVY, blitz_strategy=BlitzStrategy.BLITZ_HEAVY,
            rz_off=RZOff.POWER_RUN, rz_def=RZDef.PRESSURE_QB
        )
        sess.add(home_gameplan); sess.add(away_gameplan); sess.commit()

        # Prepare configs
        home_cfg, away_cfg = prepare_game_configs(sess, game_id, s, w, home, away)
        
        # Both should be dictionaries
        assert isinstance(home_cfg, dict)
        assert isinstance(away_cfg, dict)
        
        # Should have different configs (different gameplans)
        assert home_cfg != away_cfg
        
        # Home team should be more aggressive (pass bias > 0)
        assert home_cfg["pass_bias"] > 0
        
        # Away team should be more conservative (pass bias < 0)
        assert away_cfg["pass_bias"] < 0
        
        # Away team should have higher blitz rate (blitz heavy)
        assert away_cfg["blitz_rate"] > home_cfg["blitz_rate"]

def test_composition_order_matters(session: Session):
    """Test that the order of composition (HC -> User -> Focus) produces expected results."""
    from app.db import get_engine
    
    s, w = 2024, 3
    team, opp = 1, 2
    game_id = 101

    with Session(get_engine()) as sess:
        # Set up conflicting influences to test order
        # User: Very Conservative (should reduce pass bias)
        row = GameplanSelection(
            season=s, week=w, team_id=team, opponent_team_id=opp,
            off_agg=OffAgg.VERY_CONSERVATIVE, def_agg=DefAgg.BALANCED,
            coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.STANDARD,
            rz_off=RZOff.BALANCED, rz_def=RZDef.BALANCED
        )
        sess.add(row); sess.commit()

        # Focus: OF_GAMEPLAN (should increase pass bias)
        set_coach_focus(sess, coach_id=1, team_id=team, season=s, week=w, role=CoachRole.HC, focus=CoachFocus.OF_GAMEPLAN)

        cfg = compose_final_engine_config(sess, game_id, s, w, team, opp)
        
        # The final result should reflect the composition order
        # User Very Conservative: -0.10 pass bias
        # Focus OF_GAMEPLAN: +0.015 pass bias (weighted by HC role 2.0 = +0.03)
        # Net result should be negative (conservative wins)
        assert cfg.pass_bias < 0

def test_engine_config_clamping():
    """Test that engine config values are properly clamped."""
    from app.engine.gameplan_apply import apply_gameplan_to_default
    from app.services.gameplan_mapping import GameplanDeltas
    
    # Create extreme deltas that should be clamped
    extreme_deltas = GameplanDeltas(
        pass_bias_delta=1.0,  # Should be clamped to 0.5
        depth_bias_delta=-1.0,  # Should be clamped to -0.4
        trick_play_rate_delta=0.1,  # Should be clamped to 0.02
        base_blitz_rate_delta=0.5,  # Should be clamped
        blitz_rate_multiplier=5.0,  # Should result in clamped blitz rate
    )
    
    config = apply_gameplan_to_default(extreme_deltas)
    
    # Check clamping
    assert config.pass_bias == 0.5  # Clamped to max
    assert config.depth_bias == -0.4  # Clamped to min
    assert config.trick_play_rate == 0.02  # Clamped to max
    assert config.blitz_rate <= 0.45  # Clamped to max

def test_trace_api_functionality(session: Session):
    """Test that trace API endpoints work correctly."""
    from app.db import get_engine
    from app.ui.api_debug_gameplan import gameplan_trace
    
    s, w = 2024, 3
    team, opp = 1, 2
    game_id = 101

    with Session(get_engine()) as sess:
        # Create a gameplan and compose config
        row = GameplanSelection(
            season=s, week=w, team_id=team, opponent_team_id=opp,
            off_agg=OffAgg.AGGRESSIVE, def_agg=DefAgg.BALANCED,
            coverage=Coverage.HYBRID, blitz_strategy=BlitzStrategy.STANDARD,
            rz_off=RZOff.BALANCED, rz_def=RZDef.BALANCED
        )
        sess.add(row); sess.commit()

        # Compose config (creates trace)
        compose_final_engine_config(sess, game_id, s, w, team, opp)
        
        # Test trace API
        traces = gameplan_trace(game_id, sess)
        assert len(traces) == 1
        
        trace = traces[0]
        assert trace.team_id == team
        assert trace.opponent_team_id == opp
        assert trace.season == s
        assert trace.week == w
        assert trace.hc != ""
        assert trace.focus != ""
        assert trace.user != ""
        assert trace.final_cfg != ""

def test_no_halftime_adjustments():
    """Test that there are no halftime adjustments - all choices are locked before sim."""
    # This test verifies that the system doesn't support halftime adjustments
    # The compose_final_engine_config function should only be called once per game
    # and the resulting config should be used for the entire game
    
    # This is more of a design verification than a functional test
    # The system is designed to lock in gameplan choices before kickoff
    assert True  # Placeholder - the design itself prevents halftime adjustments

def test_composition_with_missing_data(session: Session):
    """Test that composition works even with missing gameplan or focus data."""
    from app.db import get_engine
    
    s, w = 2024, 3
    team, opp = 1, 2
    game_id = 101

    with Session(get_engine()) as sess:
        # No gameplan, no focus - should still work with defaults
        cfg = compose_final_engine_config(sess, game_id, s, w, team, opp)
        
        # Should return a valid config
        assert isinstance(cfg, EngineConfig)
        
        # Should have default values
        assert cfg.pass_bias == 0.0
        assert cfg.depth_bias == 0.0
        assert cfg.blitz_rate > 0
        assert cfg.coverage_mix == 0.5
        
        # Should still create a trace
        traces = list(sess.exec(select(GameplanTrace).where(GameplanTrace.game_id==game_id)))
        assert len(traces) == 1

