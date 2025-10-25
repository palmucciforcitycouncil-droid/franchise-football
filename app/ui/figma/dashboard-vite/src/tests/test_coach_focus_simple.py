# tests/test_coach_focus_simple.py
"""Simplified coach focus tests without full app imports."""
import pytest
from sqlmodel import Session, SQLModel, create_engine
from app.models.coach import Coach, CoachRole, CoachFocus, CoachFocusAssignment
from app.models.core_min import Team
from app.services.coach_focus import compute_week_modifiers, set_focus, _delta, ROLE_WT, COEF
from random import Random


@pytest.fixture(name="engine")
def engine_fixture():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_delta_function():
    """Test rating delta calculation."""
    assert _delta(50) == 0.0  # Center point
    assert _delta(99) == pytest.approx(0.98, abs=0.01)  # High rating
    assert _delta(1) == pytest.approx(-0.98, abs=0.01)  # Low rating
    assert _delta(75) == 0.5   # Above average
    assert _delta(25) == -0.5  # Below average


def test_role_weights():
    """Test role weights are correctly defined."""
    assert ROLE_WT[CoachRole.HC] == 4.0
    assert ROLE_WT[CoachRole.OC] == 2.0
    assert ROLE_WT[CoachRole.DC] == 2.0
    assert ROLE_WT[CoachRole.AC1] == 1.0
    assert ROLE_WT[CoachRole.AC2] == 1.0


def test_coefficients_defined():
    """Test all coefficients are defined."""
    required_coefs = [
        "RUN_PASS", "OFF", "DEF", "RZ_OFF", "RZ_DEF",
        "PACE", "TWO_MIN", "FOURTH", "TWO_PT", "CHALL",
        "ST", "PEN", "FAKE", "BLITZ", "COV",
        "DEV_OFF", "DEV_DEF", "CHEM"
    ]
    for coef in required_coefs:
        assert coef in COEF
        assert isinstance(COEF[coef], (int, float))


def test_focus_assignment_and_retrieval(engine):
    """Test focus assignment and retrieval."""
    with Session(engine) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coach
        coach = Coach(
            team_id=team.id, role=CoachRole.HC, coach_name="John Smith", active=True,
            run_pass_tendency=80, offensive_aggression=75, defensive_aggression=70,
            pace=70, clock_management=80, fourth_down_tendency=75, two_point_tendency=70,
            challenge_sense=70, discipline=80, motivation_chemistry=75,
            player_dev_offense=70, player_dev_defense=70,
            red_zone_offense=75, blitz_rate=70, coverage_mix=70, red_zone_defense=75,
            special_teams_quality=70, fake_trick_tendency=70
        )
        s.add(coach)
        s.commit()
        s.refresh(coach)
        
        # Set focus
        set_focus(s, team.id, 2025, 1, coach.coach_id, CoachRole.HC, CoachFocus.OFF_GAMEPLAN)
        
        # Retrieve and verify
        assignments = s.query(CoachFocusAssignment).filter_by(
            team_id=team.id, season=2025, week=1, coach_id=coach.coach_id
        ).all()
        
        assert len(assignments) == 1
        assert assignments[0].focus == CoachFocus.OFF_GAMEPLAN


def test_modifiers_reflect_ratings_and_focus(engine):
    """Test modifiers reflect ratings and focus."""
    with Session(engine) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Build a strong HC and OC/DC with clear biases
        hc = Coach(
            team_id=team.id, role=CoachRole.HC, coach_name="HC A", active=True,
            run_pass_tendency=70, offensive_aggression=75, defensive_aggression=65,
            pace=80, clock_management=78, fourth_down_tendency=72, two_point_tendency=55,
            challenge_sense=70, discipline=65, motivation_chemistry=68,
            player_dev_offense=60, player_dev_defense=60,
            red_zone_offense=72, blitz_rate=60, coverage_mix=62, red_zone_defense=66,
            special_teams_quality=64, fake_trick_tendency=58
        )

        oc = Coach(
            team_id=team.id, role=CoachRole.OC, coach_name="OC A", active=True,
            run_pass_tendency=75, offensive_aggression=80, defensive_aggression=50,
            pace=50, clock_management=50, fourth_down_tendency=50, two_point_tendency=50,
            challenge_sense=50, discipline=50, motivation_chemistry=50,
            player_dev_offense=70, player_dev_defense=50,
            red_zone_offense=78, blitz_rate=50, coverage_mix=50, red_zone_defense=50,
            special_teams_quality=50, fake_trick_tendency=50
        )

        dc = Coach(
            team_id=team.id, role=CoachRole.DC, coach_name="DC A", active=True,
            run_pass_tendency=50, offensive_aggression=50, defensive_aggression=80,
            pace=50, clock_management=50, fourth_down_tendency=50, two_point_tendency=50,
            challenge_sense=50, discipline=50, motivation_chemistry=50,
            player_dev_offense=50, player_dev_defense=75,
            red_zone_offense=50, blitz_rate=82, coverage_mix=76, red_zone_defense=74,
            special_teams_quality=50, fake_trick_tendency=50
        )
        
        s.add_all([hc, oc, dc])
        s.commit()
        
        # Set focuses
        set_focus(s, team.id, 2025, 1, hc.coach_id, CoachRole.HC, CoachFocus.TWO_MINUTE)
        set_focus(s, team.id, 2025, 1, oc.coach_id, CoachRole.OC, CoachFocus.OFF_GAMEPLAN)
        set_focus(s, team.id, 2025, 1, dc.coach_id, CoachRole.DC, CoachFocus.DEF_GAMEPLAN)
        
        mods = compute_week_modifiers(s, team.id, 2025, 1)
        
        # Should have positive effects due to good ratings and focuses
        assert mods.off_success_mult > 0
        assert mods.def_success_mult > 0
        assert mods.run_pass_shift > 0    # leaning pass
        assert mods.two_min_off_bonus > 0
        assert mods.blitz_bias > 0
        assert mods.pace_mult > 0
        assert mods.fourth_down_bias > 0
        assert mods.challenge_edge > 0
        assert mods.st_eff_bonus > 0
        assert mods.fake_trick_prob > 0
        assert mods.coverage_eff > 0
        assert mods.dev_off_week > 0
        assert mods.dev_def_week > 0
        assert mods.chemistry_boost > 0
        
        # Discipline should reduce penalties (negative multiplier)
        assert mods.penalty_rate_mult < 0


def test_modifiers_with_neutral_ratings(engine):
    """Test modifiers with neutral ratings (all 50)."""
    with Session(engine) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create coach with all neutral ratings
        coach = Coach(
            team_id=team.id, role=CoachRole.HC, coach_name="Neutral Coach", active=True,
            run_pass_tendency=50, offensive_aggression=50, defensive_aggression=50,
            pace=50, clock_management=50, fourth_down_tendency=50, two_point_tendency=50,
            challenge_sense=50, discipline=50, motivation_chemistry=50,
            player_dev_offense=50, player_dev_defense=50,
            red_zone_offense=50, blitz_rate=50, coverage_mix=50, red_zone_defense=50,
            special_teams_quality=50, fake_trick_tendency=50
        )
        s.add(coach)
        s.commit()
        
        mods = compute_week_modifiers(s, team.id, 2025, 1)
        
        # All modifiers should be near zero (within small tolerance for focus effects)
        assert abs(mods.run_pass_shift) < 0.05
        assert abs(mods.off_success_mult) < 0.05
        assert abs(mods.def_success_mult) < 0.05
        assert abs(mods.pace_mult) < 0.05


def test_focus_boosts(engine):
    """Test that focus assignments provide boosts."""
    with Session(engine) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create coach with good ratings
        coach = Coach(
            team_id=team.id, role=CoachRole.OC, coach_name="OC", active=True,
            run_pass_tendency=70, offensive_aggression=70, defensive_aggression=50,
            pace=50, clock_management=50, fourth_down_tendency=50, two_point_tendency=50,
            challenge_sense=50, discipline=50, motivation_chemistry=50,
            player_dev_offense=70, player_dev_defense=50,
            red_zone_offense=70, blitz_rate=50, coverage_mix=50, red_zone_defense=50,
            special_teams_quality=50, fake_trick_tendency=50
        )
        s.add(coach)
        s.commit()
        s.refresh(coach)
        
        # Get baseline modifiers without focus
        mods_no_focus = compute_week_modifiers(s, team.id, 2025, 1)
        baseline_off = mods_no_focus.off_success_mult
        
        # Set offensive gameplan focus
        set_focus(s, team.id, 2025, 2, coach.coach_id, CoachRole.OC, CoachFocus.OFF_GAMEPLAN)
        
        # Get modifiers with focus
        mods_with_focus = compute_week_modifiers(s, team.id, 2025, 2)
        focused_off = mods_with_focus.off_success_mult
        
        # Focus should provide a boost
        assert focused_off > baseline_off


def test_multiple_coaches_stack(engine):
    """Test that multiple coaches' effects stack."""
    with Session(engine) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create single coach
        hc_only = Coach(
            team_id=team.id, role=CoachRole.HC, coach_name="HC Only", active=True,
            run_pass_tendency=70, offensive_aggression=70, defensive_aggression=70,
            pace=70, clock_management=70, fourth_down_tendency=70, two_point_tendency=70,
            challenge_sense=70, discipline=70, motivation_chemistry=70,
            player_dev_offense=70, player_dev_defense=70,
            red_zone_offense=70, blitz_rate=70, coverage_mix=70, red_zone_defense=70,
            special_teams_quality=70, fake_trick_tendency=70
        )
        s.add(hc_only)
        s.commit()
        
        mods_single = compute_week_modifiers(s, team.id, 2025, 1)
        single_off = mods_single.off_success_mult
        
        # Add OC with same ratings
        oc = Coach(
            team_id=team.id, role=CoachRole.OC, coach_name="OC", active=True,
            run_pass_tendency=70, offensive_aggression=70, defensive_aggression=70,
            pace=70, clock_management=70, fourth_down_tendency=70, two_point_tendency=70,
            challenge_sense=70, discipline=70, motivation_chemistry=70,
            player_dev_offense=70, player_dev_defense=70,
            red_zone_offense=70, blitz_rate=70, coverage_mix=70, red_zone_defense=70,
            special_teams_quality=70, fake_trick_tendency=70
        )
        s.add(oc)
        s.commit()
        
        mods_multiple = compute_week_modifiers(s, team.id, 2025, 1)
        multiple_off = mods_multiple.off_success_mult
        
        # Multiple coaches should have greater effect
        assert multiple_off > single_off


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



