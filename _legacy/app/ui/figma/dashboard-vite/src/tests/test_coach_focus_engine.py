import pytest
from sqlmodel import Session, select
from app.models.coach_focus import (
    CoachFocusAssignment, TeamWeeklyCoachEffects, TeamSeasonFocusTally,
    CoachFocus, CoachRole
)
from app.services.coach_focus_service import (
    set_coach_focus, get_team_week_focuses, aggregate_weekly_effects,
    development_progression_bonus, ROLE_WEIGHT, BASE_EFFECTS
)
from app.engine.focus_hooks import (
    get_focus_bundle, apply_playcall_focus, adjust_injury_probability,
    adjust_stamina_drain, adjust_two_minute_success, PlaycallParams
)

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    from sqlmodel import create_engine, SQLModel
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def season_setup():
    """Mock season setup for testing."""
    class MockSeasonSetup:
        current_season = 2024
        user_team_id = 1
    return MockSeasonSetup()

def test_role_weight_aggregation(session: Session, season_setup):
    """Test that role weights are applied correctly in aggregation."""
    s, w, team = season_setup.current_season, 3, season_setup.user_team_id
    
    # HC OF, OC OF, AC1 TRAINING -> should bump offense deltas and reduce injury/stamina
    set_coach_focus(session, coach_id=101, team_id=team, season=s, week=w, role=CoachRole.HC, focus=CoachFocus.OF_GAMEPLAN)
    set_coach_focus(session, coach_id=102, team_id=team, season=s, week=w, role=CoachRole.OC, focus=CoachFocus.OF_GAMEPLAN)
    set_coach_focus(session, coach_id=103, team_id=team, season=s, week=w, role=CoachRole.AC1, focus=CoachFocus.TRAINING)

    bundle = aggregate_weekly_effects(session, team, s, w)

    # OF gameplan added twice with weights (2.0 + 1.5) * 0.015 = 0.0525; clamped to 0.05
    assert abs(bundle.run_pass_tendency_delta - 0.05) < 1e-6
    # training: injury mult should be < 1.0
    assert bundle.injury_prob_multiplier < 1.0
    assert bundle.stamina_drain_multiplier < 1.0

def test_weekly_snapshot_persistence(session: Session, season_setup):
    """Test that weekly snapshots are persisted correctly."""
    s, w, team = season_setup.current_season, 5, season_setup.user_team_id
    
    # Set some focuses
    set_coach_focus(session, coach_id=201, team_id=team, season=s, week=w, role=CoachRole.HC, focus=CoachFocus.DF_GAMEPLAN)
    
    # Aggregate effects (should create snapshot)
    bundle = aggregate_weekly_effects(session, team, s, w)
    
    # Check snapshot was created
    snap = session.exec(select(TeamWeeklyCoachEffects).where(
        TeamWeeklyCoachEffects.team_id==team,
        TeamWeeklyCoachEffects.season==s,
        TeamWeeklyCoachEffects.week==w
    )).first()
    
    assert snap is not None
    assert snap.defensive_aggression_delta > 0  # Should have DF gameplan effect

def test_season_development_bonus(session: Session, season_setup):
    """Test that development focus accumulates correctly for end-of-season bonus."""
    s, team = season_setup.current_season, season_setup.user_team_id
    
    # Simulate 6 weighted DEV weeks: HC (2.0) + AC1 (1.0) repeated 2 weeks
    for w in (1, 2, 3):
        set_coach_focus(session, 201, team, s, w, CoachRole.HC, CoachFocus.DEVELOPMENT)
        set_coach_focus(session, 202, team, s, w, CoachRole.AC1, CoachFocus.DEVELOPMENT)
        # Aggregate to update tally
        aggregate_weekly_effects(session, team, s, w)
    
    bonus = development_progression_bonus(session, team, s)
    # 3 weeks * (2.0 + 1.0) = 9 points → 9 * 0.005 = 0.045
    assert 0.044 <= bonus <= 0.046

def test_focus_effect_clamping(session: Session, season_setup):
    """Test that effects are properly clamped to safe ranges."""
    s, w, team = season_setup.current_season, 1, season_setup.user_team_id
    
    # Set multiple coaches with same focus to test clamping
    for coach_id in range(101, 111):  # 10 coaches
        set_coach_focus(session, coach_id=coach_id, team_id=team, season=s, week=w, 
                       role=CoachRole.HC, focus=CoachFocus.OF_GAMEPLAN)
    
    bundle = aggregate_weekly_effects(session, team, s, w)
    
    # Should be clamped to max values
    assert bundle.run_pass_tendency_delta <= 0.05
    assert bundle.offensive_aggression_delta <= 0.05
    assert bundle.pace_delta <= 0.05
    assert bundle.fourth_down_delta <= 0.04
    assert bundle.two_point_delta <= 0.04

def test_multiplier_clamping(session: Session, season_setup):
    """Test that multipliers are properly clamped."""
    s, w, team = season_setup.current_season, 1, season_setup.user_team_id
    
    # Set many training focuses to test multiplier clamping
    for coach_id in range(101, 111):  # 10 coaches
        set_coach_focus(session, coach_id=coach_id, team_id=team, season=s, week=w,
                       role=CoachRole.HC, focus=CoachFocus.TRAINING)
    
    bundle = aggregate_weekly_effects(session, team, s, w)
    
    # Multipliers should be clamped
    assert 0.85 <= bundle.injury_prob_multiplier <= 1.05
    assert 0.85 <= bundle.stamina_drain_multiplier <= 1.05

def test_season_tally_accumulation(session: Session, season_setup):
    """Test that season tallies accumulate correctly across weeks."""
    s, team = season_setup.current_season, season_setup.user_team_id
    
    # Set different focuses across multiple weeks
    focuses = [
        (CoachFocus.OF_GAMEPLAN, CoachRole.HC),
        (CoachFocus.DF_GAMEPLAN, CoachRole.DC),
        (CoachFocus.TRAINING, CoachRole.AC1),
        (CoachFocus.DEVELOPMENT, CoachRole.AC2),
    ]
    
    for week, (focus, role) in enumerate(focuses, 1):
        set_coach_focus(session, coach_id=100+week, team_id=team, season=s, week=week, role=role, focus=focus)
        aggregate_weekly_effects(session, team, s, week)
    
    # Check season tally
    tally = session.exec(select(TeamSeasonFocusTally).where(
        TeamSeasonFocusTally.team_id==team,
        TeamSeasonFocusTally.season==s
    )).first()
    
    assert tally is not None
    assert tally.of_gameplan_points == 2.0  # HC weight
    assert tally.df_gameplan_points == 1.5  # DC weight
    assert tally.training_points == 1.0     # AC1 weight
    assert tally.development_points == 1.0   # AC2 weight

def test_engine_hooks_integration(session: Session, season_setup):
    """Test that engine hooks work correctly with focus bundles."""
    s, w, team = season_setup.current_season, 1, season_setup.user_team_id
    
    # Set some focuses
    set_coach_focus(session, coach_id=101, team_id=team, season=s, week=w, role=CoachRole.HC, focus=CoachFocus.OF_GAMEPLAN)
    set_coach_focus(session, coach_id=102, team_id=team, season=s, week=w, role=CoachRole.OC, focus=CoachFocus.TRAINING)
    
    # Get focus bundle
    bundle = get_focus_bundle(session, team, s, w)
    
    # Test playcall parameter adjustment
    base_params = PlaycallParams(
        run_pass_bias=0.0,
        offense_aggr=0.5,
        defense_aggr=0.5,
        pace=1.0,
        fourth_down=0.3,
        two_point=0.1,
        st_quality=0.5
    )
    
    adjusted_params = apply_playcall_focus(base_params, bundle)
    
    # Should have offensive gameplan effects
    assert adjusted_params.run_pass_bias > base_params.run_pass_bias
    assert adjusted_params.offense_aggr > base_params.offense_aggr
    assert adjusted_params.pace > base_params.pace
    
    # Test injury/stamina adjustments
    base_injury_prob = 0.05
    adjusted_injury_prob = adjust_injury_probability(base_injury_prob, bundle)
    assert adjusted_injury_prob < base_injury_prob  # Training reduces injury
    
    base_stamina_drain = 0.1
    adjusted_stamina_drain = adjust_stamina_drain(base_stamina_drain, bundle)
    assert adjusted_stamina_drain < base_stamina_drain  # Training reduces stamina drain

def test_two_minute_offense_effect(session: Session, season_setup):
    """Test that two-minute offense focus affects success probability."""
    s, w, team = season_setup.current_season, 1, season_setup.user_team_id
    
    # Set two-minute offense focus
    set_coach_focus(session, coach_id=101, team_id=team, season=s, week=w, 
                   role=CoachRole.HC, focus=CoachFocus.TWO_MIN_OFFENSE)
    
    bundle = get_focus_bundle(session, team, s, w)
    
    base_success_prob = 0.4
    adjusted_success_prob = adjust_two_minute_success(base_success_prob, bundle)
    
    assert adjusted_success_prob > base_success_prob
    assert adjusted_success_prob == base_success_prob + bundle.two_min_offense_success_delta

def test_special_teams_effect(session: Session, season_setup):
    """Test that special teams focus affects ST quality."""
    s, w, team = season_setup.current_season, 1, season_setup.user_team_id
    
    # Set special teams focus
    set_coach_focus(session, coach_id=101, team_id=team, season=s, week=w,
                   role=CoachRole.HC, focus=CoachFocus.SPECIAL_TEAMS)
    
    bundle = get_focus_bundle(session, team, s, w)
    
    assert bundle.special_teams_quality_delta > 0

def test_development_focus_no_weekly_effect(session: Session, season_setup):
    """Test that development focus has no immediate weekly effect."""
    s, w, team = season_setup.current_season, 1, season_setup.user_team_id
    
    # Set development focus
    set_coach_focus(session, coach_id=101, team_id=team, season=s, week=w,
                   role=CoachRole.HC, focus=CoachFocus.DEVELOPMENT)
    
    bundle = get_focus_bundle(session, team, s, w)
    
    # Development should not affect any weekly simulation parameters
    assert bundle.run_pass_tendency_delta == 0.0
    assert bundle.offensive_aggression_delta == 0.0
    assert bundle.defensive_aggression_delta == 0.0
    assert bundle.pace_delta == 0.0
    assert bundle.fourth_down_delta == 0.0
    assert bundle.two_point_delta == 0.0
    assert bundle.special_teams_quality_delta == 0.0
    assert bundle.injury_prob_multiplier == 1.0
    assert bundle.stamina_drain_multiplier == 1.0
    assert bundle.two_min_offense_success_delta == 0.0

def test_scouting_focus_no_weekly_effect(session: Session, season_setup):
    """Test that scouting focus has no immediate weekly effect."""
    s, w, team = season_setup.current_season, 1, season_setup.user_team_id
    
    # Set scouting focus
    set_coach_focus(session, coach_id=101, team_id=team, season=s, week=w,
                   role=CoachRole.HC, focus=CoachFocus.SCOUTING)
    
    bundle = get_focus_bundle(session, team, s, w)
    
    # Scouting should not affect any weekly simulation parameters
    assert bundle.run_pass_tendency_delta == 0.0
    assert bundle.offensive_aggression_delta == 0.0
    assert bundle.defensive_aggression_delta == 0.0
    assert bundle.pace_delta == 0.0
    assert bundle.fourth_down_delta == 0.0
    assert bundle.two_point_delta == 0.0
    assert bundle.special_teams_quality_delta == 0.0
    assert bundle.injury_prob_multiplier == 1.0
    assert bundle.stamina_drain_multiplier == 1.0
    assert bundle.two_min_offense_success_delta == 0.0

def test_focus_assignment_upsert(session: Session, season_setup):
    """Test that focus assignments can be updated (upsert behavior)."""
    s, w, team = season_setup.current_season, 1, season_setup.user_team_id
    coach_id = 101
    
    # Set initial focus
    set_coach_focus(session, coach_id=coach_id, team_id=team, season=s, week=w,
                   role=CoachRole.HC, focus=CoachFocus.OF_GAMEPLAN)
    
    # Update to different focus
    set_coach_focus(session, coach_id=coach_id, team_id=team, season=s, week=w,
                   role=CoachRole.HC, focus=CoachFocus.DF_GAMEPLAN)
    
    # Should only have one assignment
    assignments = get_team_week_focuses(session, team, s, w)
    assert len(assignments) == 1
    assert assignments[0].focus == CoachFocus.DF_GAMEPLAN

def test_empty_team_effects(session: Session, season_setup):
    """Test that teams with no focus assignments get neutral effects."""
    s, w, team = season_setup.current_season, 1, season_setup.user_team_id
    
    bundle = aggregate_weekly_effects(session, team, s, w)
    
    # Should have neutral/zero effects
    assert bundle.run_pass_tendency_delta == 0.0
    assert bundle.offensive_aggression_delta == 0.0
    assert bundle.defensive_aggression_delta == 0.0
    assert bundle.pace_delta == 0.0
    assert bundle.fourth_down_delta == 0.0
    assert bundle.two_point_delta == 0.0
    assert bundle.special_teams_quality_delta == 0.0
    assert bundle.injury_prob_multiplier == 1.0
    assert bundle.stamina_drain_multiplier == 1.0
    assert bundle.two_min_offense_success_delta == 0.0

def test_role_weight_constants():
    """Test that role weights are set correctly."""
    assert ROLE_WEIGHT[CoachRole.HC] == 2.0
    assert ROLE_WEIGHT[CoachRole.OC] == 1.5
    assert ROLE_WEIGHT[CoachRole.DC] == 1.5
    assert ROLE_WEIGHT[CoachRole.AC1] == 1.0
    assert ROLE_WEIGHT[CoachRole.AC2] == 1.0

def test_base_effects_structure():
    """Test that base effects are properly structured."""
    # All focuses should have entries (even if empty)
    for focus in CoachFocus:
        assert focus in BASE_EFFECTS
    
    # Check some specific effects
    assert BASE_EFFECTS[CoachFocus.OF_GAMEPLAN]['run_pass_tendency_delta'] > 0
    assert BASE_EFFECTS[CoachFocus.DF_GAMEPLAN]['defensive_aggression_delta'] > 0
    assert BASE_EFFECTS[CoachFocus.TRAINING]['injury_prob_multiplier'] < 0
    assert BASE_EFFECTS[CoachFocus.SPECIAL_TEAMS]['special_teams_quality_delta'] > 0
    assert BASE_EFFECTS[CoachFocus.TWO_MIN_OFFENSE]['two_min_offense_success_delta'] > 0