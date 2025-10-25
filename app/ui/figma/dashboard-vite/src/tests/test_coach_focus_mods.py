# tests/test_coach_focus_mods.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db import get_engine
from app.models.coach import Coach, CoachRole, CoachFocus, CoachFocusAssignment
from app.models.core_min import Team
from app.services.coach_focus import compute_week_modifiers, set_focus, get_focus_map, _rating_delta
from app.services.coach_progression import progress_coaches_end_of_season
from app.engine.game_modifiers import get_team_mods_for_week, apply_all_modifiers
from random import Random

client = TestClient(app)

def test_rating_delta_function():
    """Test rating delta calculation."""
    assert _rating_delta(50) == 0.0  # Center point
    assert _rating_delta(99) == 0.98  # High rating
    assert _rating_delta(1) == -0.98  # Low rating
    assert _rating_delta(75) == 0.5   # Above average
    assert _rating_delta(25) == -0.5  # Below average

def test_role_weights_and_focus_math(tmp_path):
    """Test role weights and focus math calculations."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coaches with known ratings
        hc = Coach(
            first_name="John", last_name="Smith", age=45,
            team_id=team.id, role=CoachRole.HC, active=True,
            offense=90, defense=90, training=90, discipline=90, 
            two_minute=90, special_teams=90, development=90
        )
        oc = Coach(
            first_name="Jane", last_name="Doe", age=40,
            team_id=team.id, role=CoachRole.OC, active=True,
            offense=80, defense=60, training=70, discipline=75,
            two_minute=75, special_teams=70, development=80
        )
        dc = Coach(
            first_name="Bob", last_name="Johnson", age=42,
            team_id=team.id, role=CoachRole.DC, active=True,
            offense=60, defense=80, training=70, discipline=80,
            two_minute=70, special_teams=75, development=70
        )
        ac = Coach(
            first_name="Alice", last_name="Wilson", age=38,
            team_id=team.id, role=CoachRole.AC1, active=True,
            offense=70, defense=70, training=75, discipline=70,
            two_minute=70, special_teams=70, development=75
        )
        
        s.add_all([hc, oc, dc, ac])
        s.commit()
        s.refresh_all([hc, oc, dc, ac])
        
        # Set focuses
        set_focus(s, team.id, 2025, 1, hc.coach_id, CoachRole.HC, CoachFocus.OFF_GAMEPLAN)
        set_focus(s, team.id, 2025, 1, oc.coach_id, CoachRole.OC, CoachFocus.OFF_GAMEPLAN)
        set_focus(s, team.id, 2025, 1, dc.coach_id, CoachRole.DC, CoachFocus.DEF_GAMEPLAN)
        set_focus(s, team.id, 2025, 1, ac.coach_id, CoachRole.AC1, CoachFocus.SPECIAL_TEAMS)
        
        # Test modifiers computation
        mods = compute_week_modifiers(s, team.id, 2025, 1)
        
        # Should have positive offense effects due to HC and OC focusing on offense
        assert mods.offense_eff > 0
        # Should have positive defense effects due to DC focusing on defense
        assert mods.defense_eff > 0
        # Should have positive special teams effects due to AC focusing on ST
        assert mods.st_eff > 0
        # Should have negative injury/stamina multipliers due to good training ratings
        assert mods.injury_prob_mult < 0
        assert mods.stamina_decay_mult < 0
        # Should have negative penalty rate due to good discipline ratings
        assert mods.penalty_rate_mult < 0

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
            first_name="John", last_name="Smith", age=45,
            team_id=team.id, role=CoachRole.HC, active=True,
            offense=80, defense=75, training=70, discipline=80
        )
        s.add(coach)
        s.commit()
        s.refresh(coach)
        
        # Set focus
        set_focus(s, team.id, 2025, 1, coach.coach_id, CoachRole.HC, CoachFocus.OFF_GAMEPLAN)
        
        # Retrieve focus map
        focus_map = get_focus_map(s, team.id, 2025, 1)
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
            first_name="John", last_name="Smith", age=45,
            team_id=team.id, role=CoachRole.HC, active=True,
            offense=80, defense=75, training=70, discipline=80,
            two_minute=75, special_teams=70, development=80,
            scouting=75, leadership=85, adjustments=80
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
        assert "offense_eff" in data
        assert "defense_eff" in data
        assert "st_eff" in data
        assert "two_min_score_boost" in data
        assert "injury_prob_mult" in data
        assert "stamina_decay_mult" in data
        assert "penalty_rate_mult" in data
        assert "dev_progress_weekly" in data
        
        # Test team focuses endpoint
        res = client.get(f"/api/v1/coach/team_focuses?team_id={team.id}&season=2025&week=1")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        coach_data = data[0]
        assert coach_data["coach_id"] == coach.coach_id
        assert coach_data["name"] == "John Smith"
        assert coach_data["role"] == CoachRole.HC
        assert coach_data["current_focus"] == CoachFocus.OFF_GAMEPLAN

def test_game_modifiers_integration(tmp_path):
    """Test game modifiers integration."""
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coach
        coach = Coach(
            first_name="John", last_name="Smith", age=45,
            team_id=team.id, role=CoachRole.HC, active=True,
            offense=80, defense=75, training=70, discipline=80,
            two_minute=75, special_teams=70, development=80
        )
        s.add(coach)
        s.commit()
        s.refresh(coach)
        
        # Set focus
        set_focus(s, team.id, 2025, 1, coach.coach_id, CoachRole.HC, CoachFocus.OFF_GAMEPLAN)
        
        # Test get_team_mods_for_week
        mods = get_team_mods_for_week(s, team.id, 2025, 1)
        assert mods.offense_eff > 0  # Should have positive offense effect
        
        # Test apply_all_modifiers
        modified_values = apply_all_modifiers(
            off_success_prob=0.5,
            opp_off_success_prob=0.5,
            fg_make_prob=0.8,
            punt_net_yards=40.0,
            td_prob=0.1,
            injury_prob=0.05,
            stamina_decay=0.1,
            penalty_rate=0.1,
            team_mods=mods,
            is_two_minute=True
        )
        
        assert "off_success_prob" in modified_values
        assert "opp_off_success_prob" in modified_values
        assert "fg_make_prob" in modified_values
        assert "punt_net_yards" in modified_values
        assert "td_prob" in modified_values
        assert "injury_prob" in modified_values
        assert "stamina_decay" in modified_values
        assert "penalty_rate" in modified_values
        
        # Offense success should be higher due to positive offense_eff
        assert modified_values["off_success_prob"] > 0.5
        # Opponent offense should be lower due to positive defense_eff
        assert modified_values["opp_off_success_prob"] < 0.5

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
            first_name="John", last_name="Smith", age=45,
            team_id=team.id, role=CoachRole.HC, active=True,
            offense=80, defense=75, training=70, discipline=80,
            two_minute=75, special_teams=70, development=80,
            leadership=85, adjustments=80
        )
        oc = Coach(
            first_name="Jane", last_name="Doe", age=40,
            team_id=team.id, role=CoachRole.OC, active=True,
            offense=80, defense=60, training=70, discipline=75,
            two_minute=75, special_teams=70, development=80,
            leadership=70, adjustments=75
        )
        
        s.add_all([hc, oc])
        s.commit()
        s.refresh_all([hc, oc])
        
        # Store original ratings
        original_hc_offense = hc.offense
        original_hc_leadership = hc.leadership
        original_oc_offense = oc.offense
        
        # Run progression
        rng = Random(42)  # Deterministic for testing
        progress_coaches_end_of_season(s, team.id, 2025, rng)
        
        # Refresh coaches
        s.refresh(hc)
        s.refresh(oc)
        
        # Ratings should have changed (either up or down based on performance)
        # The exact changes depend on the mock team metrics, but they should be different
        assert hc.offense != original_hc_offense or hc.leadership != original_hc_leadership
        assert oc.offense != original_oc_offense

def test_season_cache_dev_progress(tmp_path):
    """Test season cache development progress accumulation."""
    from app.services.season_cache import accumulate_team_dev_progress, get_team_dev_progress_total
    
    eng = get_engine()
    with Session(eng) as s:
        # Create test team
        team = Team(abbrev="TEST", name="Test Team")
        s.add(team)
        s.commit()
        s.refresh(team)
        
        # Create test coach
        coach = Coach(
            first_name="John", last_name="Smith", age=45,
            team_id=team.id, role=CoachRole.HC, active=True,
            offense=80, defense=75, training=70, discipline=80,
            two_minute=75, special_teams=70, development=80
        )
        s.add(coach)
        s.commit()
        s.refresh(coach)
        
        # Set focus for multiple weeks
        for week in range(1, 4):  # Weeks 1-3
            set_focus(s, team.id, 2025, week, coach.coach_id, CoachRole.HC, CoachFocus.DEVELOPMENT)
        
        # Test accumulation
        total_progress = accumulate_team_dev_progress(s, team.id, 2025)
        assert total_progress > 0  # Should have accumulated some development progress
        
        # Test get_team_dev_progress_total
        progress_data = get_team_dev_progress_total(s, team.id, 2025)
        assert progress_data["team_id"] == team.id
        assert progress_data["season"] == 2025
        assert progress_data["dev_progress_total"] > 0


