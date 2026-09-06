import pytest
from app.testing.mini_season_runner import memory_db
from app.config_sim_calibration import bands, safety
from scripts.phase5_calibration import run_phase5_calibrated_season
from sqlmodel import select
from app.models.pbp_event import PBPEvent
from app.models.team_priors import TeamPriors
from app.engine.pbp_curves import third_down_logit, red_zone_td_prob, fourth_down_decision, weather_adjustments
from app.engine.pbp_modifiers import compose_pass_complete_logit, pressure_probability_logit, sack_prob_from_pressure
from app.engine.safety_controller import SafetyController
from app.telemetry.game_metrics import GameMetrics
import random


def test_phase5_bands_and_guardrail_nonintrusive():
    """Test Phase 5 calibration ensures stats stay within bands."""
    with memory_db() as session:
        out = run_phase5_calibrated_season(session, weeks=2)  # ~4 games total in micro league
        
        # Get all PBP events
        all_events = session.exec(select(PBPEvent)).all()
        assert len(all_events) > 0, "Should have generated PBP events"
        
        # Aggregate by game_id
        from collections import defaultdict
        g = defaultdict(lambda: {"yards":0,"points":0,"punts":0,"fg_att":0,"sacks":0})
        
        for event in all_events:
            gid = event.game_id
            g[gid]["yards"] += event.yards_gained
            g[gid]["points"] += event.points_offense
            g[gid]["punts"]  += 1 if event.play_type == "punt" else 0
            g[gid]["fg_att"] += 1 if event.play_type == "fg" else 0
            g[gid]["sacks"]  += 1 if event.sack else 0
        
        assert len(g) >= 2, "Should have at least 2 games"
        
        # Coarse band checks (hard bounds only; realism tuned elsewhere)
        for gid, m in g.items():
            assert bands.YARDS_MIN <= m["yards"] <= bands.YARDS_MAX, f"Game {gid} yards {m['yards']} outside bounds"
            assert bands.POINTS_MIN <= m["points"] <= bands.POINTS_MAX, f"Game {gid} points {m['points']} outside bounds"
            assert bands.PUNTS_MIN <= m["punts"] <= bands.PUNTS_MAX, f"Game {gid} punts {m['punts']} outside bounds"
            assert bands.FG_ATT_MIN <= m["fg_att"] <= bands.FG_ATT_MAX, f"Game {gid} FG attempts {m['fg_att']} outside bounds"
            assert bands.SACKS_MIN <= m["sacks"] <= bands.SACKS_MAX, f"Game {gid} sacks {m['sacks']} outside bounds"


def test_phase5_option_c_components():
    """Test Option C components work correctly."""
    
    # Test third down logit table
    assert third_down_logit(1) > third_down_logit(3), "3rd & 1 should be easier than 3rd & 3"
    assert third_down_logit(3) > third_down_logit(6), "3rd & 3 should be easier than 3rd & 6"
    assert third_down_logit(6) > third_down_logit(9), "3rd & 6 should be easier than 3rd & 9"
    assert third_down_logit(9) > third_down_logit(12), "3rd & 9 should be easier than 3rd & 12"
    
    # Test red zone TD probability
    assert red_zone_td_prob(99, 0.0) > red_zone_td_prob(80, 0.0), "Goal line should have higher TD prob than 20-yard line"
    assert red_zone_td_prob(95, 0.1) > red_zone_td_prob(95, 0.0), "Positive team mod should increase TD prob"
    
    # Test fourth down decision
    rng = random.Random(42)
    # Own territory should mostly punt
    decision = fourth_down_decision(rng, 30, 5, 50, 0.5, False)
    assert decision == "PUNT", "Own territory 4th & 5 should punt"
    
    # Opponent territory short should go
    decision = fourth_down_decision(rng, 70, 2, 50, 0.8, False)
    assert decision in ["GO", "FG"], "Opponent territory 4th & 2 should go or FG"
    
    # Test weather adjustments
    clear = weather_adjustments(False, 5, "clear")
    rain = weather_adjustments(False, 15, "rain")
    snow = weather_adjustments(False, 20, "snow")
    
    assert clear["pass_logit"] == 0.0, "Clear weather should have no pass penalty"
    assert rain["pass_logit"] < 0.0, "Rain should have pass penalty"
    assert snow["pass_logit"] < rain["pass_logit"], "Snow should have worse pass penalty than rain"


def test_phase5_safety_controller():
    """Test safety controller works correctly."""
    controller = SafetyController()
    
    # Test early quarters (no intervention)
    metrics = GameMetrics(total_yards=1000, total_points=100, punts=0, fg_attempts=0, sacks=0)
    nudge = controller.evaluate(1, metrics)
    assert nudge.logit_delta == 0.0, "Q1 should have no nudge"
    assert not controller.active, "Controller should not be active in Q1"
    
    # Test Q3 with excessive offense (should trigger negative nudge)
    nudge = controller.evaluate(3, metrics)
    assert nudge.logit_delta < 0.0, "Excessive offense should trigger negative nudge"
    assert controller.active, "Controller should be active"
    
    # Test Q3 with insufficient offense (should trigger positive nudge)
    low_metrics = GameMetrics(total_yards=200, total_points=10, punts=15, fg_attempts=0, sacks=0)
    nudge = controller.evaluate(3, low_metrics)
    assert nudge.logit_delta > 0.0, "Insufficient offense should trigger positive nudge"
    
    # Test Q3 with normal metrics (no nudge)
    normal_metrics = GameMetrics(total_yards=500, total_points=45, punts=6, fg_attempts=4, sacks=5)
    nudge = controller.evaluate(3, normal_metrics)
    assert nudge.logit_delta == 0.0, "Normal metrics should have no nudge"
    assert not controller.active, "Controller should not be active with normal metrics"


def test_phase5_team_priors():
    """Test team priors system works correctly."""
    with memory_db() as session:
        # Test getting non-existent priors (should create neutral)
        priors = session.exec(
            select(TeamPriors).where(TeamPriors.season == 2025, TeamPriors.team_id == 1)
        ).first()
        
        if priors is None:
            # Create neutral priors
            priors = TeamPriors(season=2025, team_id=1)
            session.add(priors)
            session.commit()
        
        assert priors.off_epa_mod == 0.0, "Neutral priors should have 0.0 off_epa_mod"
        assert priors.def_stop_mod == 0.0, "Neutral priors should have 0.0 def_stop_mod"
        assert priors.third_down_mod == 0.0, "Neutral priors should have 0.0 third_down_mod"


def test_phase5_pbp_modifiers():
    """Test PBP modifiers work correctly."""
    
    # Test pass completion logit composition
    logit = compose_pass_complete_logit(
        qb_cov=0.7,
        wr_db=0.6,
        ol_dl=0.5,
        off_priors={"third_down_mod": 0.1, "off_epa_mod": 0.05},
        def_priors={"def_stop_mod": 0.02},
        situational_logit=0.3,
        rand_off=0.05,
        rand_def=-0.03,
        weather_pass_penalty=-0.1
    )
    
    assert logit > 0, "Good matchup should have positive logit"
    
    # Test pressure probability
    press_logit = pressure_probability_logit(
        ol_dl=0.3,  # Weak OL
        depth_secs=3.0,  # Long drop
        def_pressure_mod=0.1,
        rand_def=0.05
    )
    
    assert press_logit > 0, "Weak OL + long drop should have positive pressure logit"
    
    # Test sack probability from pressure
    sack_prob = sack_prob_from_pressure(0.3, 3.0)
    assert 0.0 <= sack_prob <= 1.0, "Sack probability should be between 0 and 1"


def test_phase5_realistic_statistics():
    """Test that Phase 5 produces realistic NFL statistics."""
    with memory_db() as session:
        out = run_phase5_calibrated_season(session, weeks=4, seed=2025)
        
        # Get all PBP events
        all_events = session.exec(select(PBPEvent)).all()
        
        # Calculate team averages
        teams = out['teams']
        games_per_team = len(out['games']) // len(teams)
        
        team_stats = {}
        for team_id in teams:
            team_events = [e for e in all_events if e.offense_team_id == team_id]
            team_stats[team_id] = {
                'yards': sum(e.yards_gained for e in team_events),
                'points': sum(e.points_offense for e in team_events),
                'punts': sum(1 for e in team_events if e.play_type == "punt"),
                'fg_attempts': sum(1 for e in team_events if e.play_type == "fg"),
                'sacks': sum(1 for e in all_events if e.sack and e.defense_team_id == team_id)
            }
        
        # Check realistic ranges
        for team_id, stats in team_stats.items():
            avg_yards = stats['yards'] / games_per_team
            avg_points = stats['points'] / games_per_team
            avg_punts = stats['punts'] / games_per_team
            avg_fgs = stats['fg_attempts'] / games_per_team
            avg_sacks = stats['sacks'] / games_per_team
            
            # Realistic NFL ranges
            assert 250 <= avg_yards <= 450, f"Team {team_id} yards/game {avg_yards:.1f} not realistic"
            assert 15 <= avg_points <= 40, f"Team {team_id} points/game {avg_points:.1f} not realistic"
            assert 2 <= avg_punts <= 6, f"Team {team_id} punts/game {avg_punts:.1f} not realistic"
            assert 1 <= avg_fgs <= 4, f"Team {team_id} FG attempts/game {avg_fgs:.1f} not realistic"
            assert 1 <= avg_sacks <= 4, f"Team {team_id} sacks/game {avg_sacks:.1f} not realistic"


def test_phase5_modern_4th_down_analytics():
    """Test that 4th down decisions follow modern analytics."""
    rng = random.Random(42)
    
    # Test own territory (should be conservative)
    decisions = []
    for _ in range(10):
        decision = fourth_down_decision(rng, 30, 5, 50, 0.5)
        decisions.append(decision)
    
    punt_count = decisions.count("PUNT")
    assert punt_count >= 7, "Own territory should mostly punt"
    
    # Test opponent territory short (should be aggressive)
    decisions = []
    for _ in range(10):
        decision = fourth_down_decision(rng, 70, 2, 50, 0.8)
        decisions.append(decision)
    
    go_count = decisions.count("GO")
    assert go_count >= 5, "Opponent territory short should often go"
    
    # Test no-man's land (should mix FG and punt)
    decisions = []
    for _ in range(10):
        decision = fourth_down_decision(rng, 62, 4, 60, 0.6)  # Increased kicker max to 60
        decisions.append(decision)
    
    fg_count = decisions.count("FG")
    punt_count = decisions.count("PUNT")
    assert fg_count >= 2, "No-man's land should sometimes try FG"
    assert punt_count >= 2, "No-man's land should sometimes punt"


def test_phase5_weather_effects():
    """Test that weather affects play outcomes."""
    
    # Test indoor vs outdoor
    indoor = weather_adjustments(True, 20, "rain")
    outdoor = weather_adjustments(False, 20, "rain")
    
    assert indoor["pass_logit"] == 0.0, "Indoor should nullify weather"
    assert outdoor["pass_logit"] < 0.0, "Outdoor rain should have penalty"
    
    # Test wind effects
    calm = weather_adjustments(False, 5, "clear")
    windy = weather_adjustments(False, 20, "clear")
    
    assert calm["fg_make_shift"] == 0.0, "Calm should have no FG shift"
    assert windy["fg_make_shift"] < 0.0, "Windy should have negative FG shift"
    
    # Test precipitation effects
    rain = weather_adjustments(False, 10, "rain")
    snow = weather_adjustments(False, 10, "snow")
    
    assert rain["pass_logit"] < 0.0, "Rain should have pass penalty"
    assert snow["pass_logit"] < rain["pass_logit"], "Snow should have worse penalty than rain"
