# tests/test_coach_ratings_focus.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db import get_engine
from app.models.coach import Coach, CoachRole, CoachFocus, CoachFocusAssignment
from app.models.core_min import Team
from app.services.coach_focus import compute_week_modifiers, set_focus, _focus_map, _delta
from app.services.coach_progression import progress_coaches_end_of_season
from app.engine.coach_mods_adapter import get_team_week_mods, apply_all_modifiers
from random import Random

client = TestClient(app)

def test_delta_function():
    """Test rating delta calculation."""
    assert _delta(50) == 0.0  # Center point
    assert _delta(99) == 0.98  # High rating
    assert _delta(1) == -0.98  # Low rating
    assert _delta(75) == 0.5   # Above average
    assert _delta(25) == -0.5  # Below average

def test_modifiers_reflect_ratings_and_focus(tmp_path):
    """Test modifiers reflect ratings and focus."""
    eng = get_engine()
    with Session(eng) as s:
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
            run_pass_tendency=75, offensive_aggression=80, red_zone_offense=78
        )

        dc = Coach(
            team_id=team.id, role=CoachRole.DC, coach_name="DC A", active=True,
            defensive_aggression=80, blitz_rate=82, coverage_mix=76, red_zone_defense=74
        )
        
        s.add_all([hc, oc, dc])
        s.commit()
        s.refresh_all([hc, oc, dc])
        
        # Focuses
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

def test_focus_assignment_and_retrieval(tmp_path):
    """Test focus assignment and retrieval."""
    eng = get_engine()
    with Session(eng) as s:
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
        
        # Retrieve focus map
        focus_map = _focus_map(s, team.id, 2025, 1)
        assert coach.coach_id in focus_map
        assert focus_map[coach.coach_id] == CoachFocus.OFF_GAMEPLAN

def test_coach_focus_api_endpoints(tmp_path):
    """Test coach focus API endpoints."""
    eng = get_engine()
    with Session(eng) as s:
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
        
        # Test set focus endpoint
        focus_data = {
            "team_id": team.id,
            "season": 2025,
            "week": 1,
            "coach_id": coach.coach_id,
            "role": CoachRole.HC,
            "focus": CoachFocus.OFF_GAMEPLAN
        }
        
        res = client.post("/api/v1/coach/set_focus", json=focus_data)
        assert res.status_code == 200
        assert res.json()["ok"] is True
        
        # Test modifiers preview endpoint
        res = client.get(f"/api/v1/coach/modifiers_preview?team_id={team.id}&season=2025&week=1")
        assert res.status_code == 200
        data = res.json()
        assert "run_pass_shift" in data
        assert "off_success_mult" in data
        assert "def_success_mult" in data
        assert "rz_off_bonus" in data
        assert "rz_def_bonus" in data
        assert "pace_mult" in data
        assert "two_min_off_bonus" in data
        assert "fourth_down_bias" in data
        assert "two_point_bias" in data
        assert "challenge_edge" in data
        assert "st_eff_bonus" in data
        assert "penalty_rate_mult" in data
        assert "fake_trick_prob" in data
        assert "blitz_bias" in data
        assert "coverage_eff" in data
        assert "dev_off_week" in data
        assert "dev_def_week" in data
        assert "chemistry_boost" in data
        
        # Test team focuses endpoint
        res = client.get(f"/api/v1/coach/team_focuses?team_id={team.id}&season=2025&week=1")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        coach_data = data[0]
        assert coach_data["coach_id"] == coach.coach_id
        assert coach_data["coach_name"] == "John Smith"
        assert coach_data["role"] == CoachRole.HC
        assert coach_data["current_focus"] == CoachFocus.OFF_GAMEPLAN

def test_engine_adapter_integration(tmp_path):
    """Test engine adapter integration."""
    eng = get_engine()
    with Session(eng) as s:
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
        
        # Test get_team_week_mods
        mods = get_team_week_mods(s, team.id, 2025, 1)
        assert mods.off_success_mult > 0  # Should have positive offense effect
        
        # Test apply_all_modifiers
        modified_values = apply_all_modifiers(
            offense_prob=0.5,
            defense_prob=0.5,
            run_pass_bias=0.0,
            plays_per_game=60.0,
            rz_td_prob_off=0.3,
            rz_td_prob_def=0.3,
            two_min_td_prob=0.1,
            fourth_down_aggr=0.0,
            two_point_aggr=0.0,
            challenge_success=0.0,
            st_success=0.8,
            penalty_rate=0.1,
            blitz_bias=0.0,
            coverage_efficiency=0.0,
            fake_play_prob=0.0,
            team_mods=mods
        )
        
        assert "offense_prob" in modified_values
        assert "defense_prob" in modified_values
        assert "run_pass_bias" in modified_values
        assert "plays_per_game" in modified_values
        assert "rz_td_prob_off" in modified_values
        assert "rz_td_prob_def" in modified_values
        assert "two_min_td_prob" in modified_values
        assert "fourth_down_aggr" in modified_values
        assert "two_point_aggr" in modified_values
        assert "challenge_success" in modified_values
        assert "st_success" in modified_values
        assert "penalty_rate" in modified_values
        assert "blitz_bias" in modified_values
        assert "coverage_efficiency" in modified_values
        assert "fake_play_prob" in modified_values
        
        # Offense success should be higher due to positive off_success_mult
        assert modified_values["offense_prob"] > 0.5

def test_coach_progression_end_of_season(tmp_path):
    """Test coach progression at end of season."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coaches
        hc = Coach(
            team_id=team.id, role=CoachRole.HC, coach_name="John Smith", active=True,
            run_pass_tendency=80, offensive_aggression=75, defensive_aggression=70,
            pace=70, clock_management=80, fourth_down_tendency=75, two_point_tendency=70,
            challenge_sense=70, discipline=80, motivation_chemistry=75,
            player_dev_offense=70, player_dev_defense=70,
            red_zone_offense=75, blitz_rate=70, coverage_mix=70, red_zone_defense=75,
            special_teams_quality=70, fake_trick_tendency=70
        )
        oc = Coach(
            team_id=team.id, role=CoachRole.OC, coach_name="Jane Doe", active=True,
            run_pass_tendency=80, offensive_aggression=75, defensive_aggression=70,
            pace=70, clock_management=80, fourth_down_tendency=75, two_point_tendency=70,
            challenge_sense=70, discipline=80, motivation_chemistry=75,
            player_dev_offense=70, player_dev_defense=70,
            red_zone_offense=75, blitz_rate=70, coverage_mix=70, red_zone_defense=75,
            special_teams_quality=70, fake_trick_tendency=70
        )
        
        s.add_all([hc, oc])
        s.commit()
        s.refresh_all([hc, oc])
        
        # Store original ratings
        original_hc_clock_management = hc.clock_management
        original_hc_motivation_chemistry = hc.motivation_chemistry
        original_oc_player_dev_offense = oc.player_dev_offense
        
        # Mock metrics for good performance
        metrics = {
            'off_rank': 5, 'def_rank': 8, 'st_rank': 12, 'rz_off_rank': 6, 'rz_def_rank': 9,
            'penalty_rate': 6.0, 'lg_penalty_rate': 7.0, 'w_pct': 0.70,
            'two_min_eff': 0.65, 'lg_two_min_eff': 0.55, 'pace_rank': 4
        }
        
        # Run progression
        rng = Random(42)  # Deterministic for testing
        progress_coaches_end_of_season(s, team.id, 2025, rng, metrics)
        
        # Refresh coaches
        s.refresh(hc)
        s.refresh(oc)
        
        # Ratings should have changed (either up or down based on performance)
        # The exact changes depend on the metrics, but they should be different
        assert hc.clock_management != original_hc_clock_management or hc.motivation_chemistry != original_hc_motivation_chemistry
        assert oc.player_dev_offense != original_oc_player_dev_offense

def test_role_weights_and_coefficients(tmp_path):
    """Test role weights and coefficient calculations."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create coaches with identical ratings but different roles
        hc = Coach(
            team_id=team.id, role=CoachRole.HC, coach_name="HC", active=True,
            run_pass_tendency=70, offensive_aggression=70, defensive_aggression=70,
            pace=70, clock_management=70, fourth_down_tendency=70, two_point_tendency=70,
            challenge_sense=70, discipline=70, motivation_chemistry=70,
            player_dev_offense=70, player_dev_defense=70,
            red_zone_offense=70, blitz_rate=70, coverage_mix=70, red_zone_defense=70,
            special_teams_quality=70, fake_trick_tendency=70
        )
        oc = Coach(
            team_id=team.id, role=CoachRole.OC, coach_name="OC", active=True,
            run_pass_tendency=70, offensive_aggression=70, defensive_aggression=70,
            pace=70, clock_management=70, fourth_down_tendency=70, two_point_tendency=70,
            challenge_sense=70, discipline=70, motivation_chemistry=70,
            player_dev_offense=70, player_dev_defense=70,
            red_zone_offense=70, blitz_rate=70, coverage_mix=70, red_zone_defense=70,
            special_teams_quality=70, fake_trick_tendency=70
        )
        ac = Coach(
            team_id=team.id, role=CoachRole.AC1, coach_name="AC", active=True,
            run_pass_tendency=70, offensive_aggression=70, defensive_aggression=70,
            pace=70, clock_management=70, fourth_down_tendency=70, two_point_tendency=70,
            challenge_sense=70, discipline=70, motivation_chemistry=70,
            player_dev_offense=70, player_dev_defense=70,
            red_zone_offense=70, blitz_rate=70, coverage_mix=70, red_zone_defense=70,
            special_teams_quality=70, fake_trick_tendency=70
        )
        
        s.add_all([hc, oc, ac])
        s.commit()
        s.refresh_all([hc, oc, ac])
        
        # Test modifiers computation
        mods = compute_week_modifiers(s, team.id, 2025, 1)
        
        # HC should have 4x weight, OC should have 2x weight, AC should have 1x weight
        # Since all ratings are 70 (delta = 0.4), the contributions should be proportional
        # This is a basic test to ensure role weights are applied correctly
        assert mods.run_pass_shift > 0  # All coaches contribute positively
        assert mods.off_success_mult > 0
        assert mods.def_success_mult > 0
        assert mods.pace_mult > 0
        assert mods.two_min_off_bonus > 0
        assert mods.fourth_down_bias > 0
        assert mods.two_point_bias > 0
        assert mods.challenge_edge > 0
        assert mods.st_eff_bonus > 0
        assert mods.penalty_rate_mult < 0  # Negative coefficient for discipline
        assert mods.fake_trick_prob > 0
        assert mods.blitz_bias > 0
        assert mods.coverage_eff > 0
        assert mods.dev_off_week > 0
        assert mods.dev_def_week > 0
        assert mods.chemistry_boost > 0


