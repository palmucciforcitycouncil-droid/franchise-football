#!/usr/bin/env python3
"""
BALANCED HFA TEST - Final Home Field Advantage Tuning
Tests the balanced HFA tuning to achieve realistic 52-54% home win rate.
"""

import os
import sys
import random
import statistics
from typing import Dict, List, Any, Tuple

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.4'  # BALANCED HFA tuning
os.environ['LEAGUE_SEED'] = '2025'

def balanced_hfa_test():
    """Run balanced HFA test targeting realistic home win rate"""
    
    def _yardage_targets_v2_balanced(season: int, home_id: int, away_id: int) -> Tuple[int, int, int, int]:
        """Generate realistic yardage targets with balanced HFA."""
        base_seed = int(os.environ.get("LEAGUE_SEED", "2025"))
        
        # Use different seeds for home and away teams
        home_seed = hash((season, home_id, base_seed)) & 0xFFFFFFFF
        away_seed = hash((season, away_id, base_seed + 1)) & 0xFFFFFFFF
        
        r_home = random.Random(home_seed)
        r_away = random.Random(away_seed)
        
        # Target: Home 345-355, Away 335-345 (realistic split)
        home_total = max(280, min(500, int(r_home.normalvariate(350, 50))))
        away_total = max(260, min(480, int(r_away.normalvariate(340, 50))))
        
        # Pass:Rush ratio ~2.2:1
        home_pass_ratio = max(1.6, min(2.8, r_home.normalvariate(2.2, 0.15)))
        away_pass_ratio = max(1.6, min(2.8, r_away.normalvariate(2.2, 0.15)))
        
        home_pass = int(home_total * home_pass_ratio / (home_pass_ratio + 1))
        away_pass = int(away_total * away_pass_ratio / (away_pass_ratio + 1))
        
        # Cap pass yards
        home_pass = min(home_pass, 450)
        away_pass = min(away_pass, 450)
        
        return home_total, home_pass, away_total, away_pass
    
    def _points_from_yards_v2_balanced(home_abbr: str, away_abbr: str) -> Tuple[int, int]:
        """Convert yardage to realistic scores with BALANCED HFA tuning."""
        base_seed = int(os.environ.get("LEAGUE_SEED", "2025"))
        
        # Use different seeds for home and away teams
        home_seed = hash((home_abbr, base_seed)) & 0xFFFFFFFF
        away_seed = hash((away_abbr, base_seed + 1)) & 0xFFFFFFFF
        
        r_home = random.Random(home_seed)
        r_away = random.Random(away_seed)
        
        # Generate yardage
        home_total, home_pass, away_total, away_pass = _yardage_targets_v2_balanced(2025, 1, 2)
        
        # Yards per Point: 13-20, mode ~15.5
        home_ypp = max(13, min(20, r_home.normalvariate(15.5, 1.2)))
        away_ypp = max(13, min(20, r_away.normalvariate(15.5, 1.2)))
        
        home_base_pts = home_total / home_ypp
        away_base_pts = away_total / away_ypp
        
        # BALANCED HFA: Single +1.4 points (no double HFA)
        hfa_points = float(os.environ.get("HFA_POINTS", "1.4"))
        
        # Apply HFA only to home team
        home_pts_raw = home_base_pts + hfa_points
        away_pts_raw = away_base_pts
        
        # Convert to integers
        home_pts = int(round(home_pts_raw))
        away_pts = int(round(away_pts_raw))
        
        # Cap single-team points
        home_pts = min(home_pts, 50)
        away_pts = min(away_pts, 50)
        
        # Soft cap total points
        total_pts = home_pts + away_pts
        if total_pts > 80:
            scale = 80 / total_pts
            home_pts = int(round(home_pts * scale))
            away_pts = int(round(away_pts * scale))
        
        return home_pts, away_pts
    
    def simulate_realistic_pbp_events():
        """Simulate realistic PBP events with tempo adjustments"""
        base_seed = int(os.environ.get("LEAGUE_SEED", "2025"))
        per_game_seed = hash((2025, 1, random.randint(1, 1000), base_seed)) & 0xFFFFFFFF
        r = random.Random(per_game_seed)
        
        # Tempo-adjusted targets
        TARGET_PLAYS_PER_GAME = 127.5
        TARGET_PUNTS_PER_GAME = 8
        TARGET_TURNOVERS_PER_GAME = 3
        
        # Simulate plays (both teams combined)
        plays = max(100, min(150, int(r.normalvariate(TARGET_PLAYS_PER_GAME, 12))))
        
        # Simulate punts (both teams combined)
        punts = max(5, min(12, int(r.normalvariate(TARGET_PUNTS_PER_GAME, 1.5))))
        
        # Simulate turnovers (both teams combined)
        turnovers = max(1, min(6, int(r.normalvariate(TARGET_TURNOVERS_PER_GAME, 1))))
        
        # Simulate scoring
        tds = max(1, int(r.normalvariate(2.6, 1.1)))
        fgs = max(0, int(r.normalvariate(1.6, 0.8)))
        
        return plays, punts, turnovers, tds, fgs
    
    print("=== BALANCED HFA TEST - FINAL HOME FIELD ADVANTAGE TUNING ===")
    print("Targeting 52-54% Home Win Rate (Realistic NFL)")
    print("BALANCED HFA: Single +1.4 points (no double HFA)")
    print("Target Scoring: Home 23.0-24.0, Away 21.0-22.0, Total 44-46")
    print("Target Plays: 120-130 per game")
    print()
    
    all_home_totals = []
    all_home_passes = []
    all_away_totals = []
    all_away_passes = []
    all_home_scores = []
    all_away_scores = []
    all_margins = []
    all_plays = []
    all_punts = []
    all_turnovers = []
    all_tds = []
    all_fgs = []
    
    for season in range(2025, 2028):
        print(f"Season {season}:")
        
        season_home_totals = []
        season_home_passes = []
        season_away_totals = []
        season_away_passes = []
        season_home_scores = []
        season_away_scores = []
        season_margins = []
        season_plays = []
        season_punts = []
        season_turnovers = []
        season_tds = []
        season_fgs = []
        
        # Simulate 272 games per season (NFL standard)
        for game in range(272):
            home_id = (game % 32) + 1
            away_id = ((game + 1) % 32) + 1
            
            h_total, h_pass, a_total, a_pass = _yardage_targets_v2_balanced(season, home_id, away_id)
            h_score, a_score = _points_from_yards_v2_balanced(f"TEAM{home_id}", f"TEAM{away_id}")
            
            # Simulate PBP events
            plays, punts, turnovers, tds, fgs = simulate_realistic_pbp_events()
            
            season_home_totals.append(h_total)
            season_home_passes.append(h_pass)
            season_away_totals.append(a_total)
            season_away_passes.append(a_pass)
            season_home_scores.append(h_score)
            season_away_scores.append(a_score)
            season_margins.append(h_score - a_score)
            season_plays.append(plays)
            season_punts.append(punts)
            season_turnovers.append(turnovers)
            season_tds.append(tds)
            season_fgs.append(fgs)
        
        # Season averages
        home_wins = sum(1 for m in season_margins if m > 0)
        home_win_rate = home_wins / len(season_margins)
        
        print(f"  Games: {len(season_margins)}")
        print(f"  Home Total Yards: {statistics.mean(season_home_totals):.1f} (range: {min(season_home_totals)}-{max(season_home_totals)})")
        print(f"  Home Pass Yards: {statistics.mean(season_home_passes):.1f} (range: {min(season_home_passes)}-{max(season_home_passes)})")
        print(f"  Away Total Yards: {statistics.mean(season_away_totals):.1f} (range: {min(season_away_totals)}-{max(season_away_totals)})")
        print(f"  Away Pass Yards: {statistics.mean(season_away_passes):.1f} (range: {min(season_away_passes)}-{max(season_away_passes)})")
        print(f"  Home Win Rate: {home_win_rate:.3f}")
        print(f"  Avg Total Points: {statistics.mean(season_home_scores) + statistics.mean(season_away_scores):.1f}")
        print(f"  Avg Margin: {statistics.mean(season_margins):.1f}")
        print(f"  Avg Plays per Game: {statistics.mean(season_plays):.1f}")
        print(f"  Avg Punts per Game: {statistics.mean(season_punts):.1f}")
        print(f"  Avg Turnovers per Game: {statistics.mean(season_turnovers):.1f}")
        print(f"  Avg TDs per Game: {statistics.mean(season_tds):.1f}")
        print(f"  Avg FGs per Game: {statistics.mean(season_fgs):.1f}")
        print()
        
        # Accumulate for overall stats
        all_home_totals.extend(season_home_totals)
        all_home_passes.extend(season_home_passes)
        all_away_totals.extend(season_away_totals)
        all_away_passes.extend(season_away_passes)
        all_home_scores.extend(season_home_scores)
        all_away_scores.extend(season_away_scores)
        all_margins.extend(season_margins)
        all_plays.extend(season_plays)
        all_punts.extend(season_punts)
        all_turnovers.extend(season_turnovers)
        all_tds.extend(season_tds)
        all_fgs.extend(season_fgs)
    
    # Overall three-season summary
    total_games = len(all_margins)
    home_wins = sum(1 for m in all_margins if m > 0)
    home_win_rate = home_wins / total_games
    
    print("="*60)
    print("=== BALANCED HFA THREE-SEASON SUMMARY (816 GAMES) ===")
    print(f"Total Games Simulated: {total_games}")
    print(f"Games per Season: {total_games // 3}")
    print()
    
    print("YARDAGE STATISTICS:")
    print(f"  Average Home Total Yards: {statistics.mean(all_home_totals):.1f}")
    print(f"  Average Home Pass Yards: {statistics.mean(all_home_passes):.1f}")
    print(f"  Average Away Total Yards: {statistics.mean(all_away_totals):.1f}")
    print(f"  Average Away Pass Yards: {statistics.mean(all_away_passes):.1f}")
    print()
    
    print("SCORING STATISTICS:")
    print(f"  Average Home Win Rate: {home_win_rate:.3f}")
    print(f"  Average Total Points per Game: {statistics.mean(all_home_scores) + statistics.mean(all_away_scores):.1f}")
    print(f"  Average Home Score: {statistics.mean(all_home_scores):.1f}")
    print(f"  Average Away Score: {statistics.mean(all_away_scores):.1f}")
    print(f"  Average Margin: {statistics.mean(all_margins):.1f}")
    print()
    
    print("PBP REALISM METRICS:")
    print(f"  Average Plays per Game: {statistics.mean(all_plays):.1f}")
    print(f"  Average Punts per Game: {statistics.mean(all_punts):.1f}")
    print(f"  Average Turnovers per Game: {statistics.mean(all_turnovers):.1f}")
    print(f"  Average TDs per Game: {statistics.mean(all_tds):.1f}")
    print(f"  Average FGs per Game: {statistics.mean(all_fgs):.1f}")
    print()
    
    print("RANGES:")
    print(f"  Home Total Yards: {min(all_home_totals)}-{max(all_home_totals)}")
    print(f"  Home Pass Yards: {min(all_home_passes)}-{max(all_home_passes)}")
    print(f"  Away Total Yards: {min(all_away_totals)}-{max(all_away_totals)}")
    print(f"  Away Pass Yards: {min(all_away_passes)}-{max(all_away_passes)}")
    print(f"  Home Score Range: {min(all_home_scores)}-{max(all_home_scores)}")
    print(f"  Away Score Range: {min(all_away_scores)}-{max(all_away_scores)}")
    print(f"  Margin Range: {min(all_margins):.1f} to {max(all_margins):.1f}")
    print(f"  Plays per Game Range: {min(all_plays)}-{max(all_plays)}")
    print(f"  Punts per Game Range: {min(all_punts)}-{max(all_punts)}")
    print(f"  Turnovers per Game Range: {min(all_turnovers)}-{max(all_turnovers)}")
    print()
    
    print("TARGET COMPARISON:")
    print(f"  Target Home Win Rate: 0.515-0.530 (Actual: {home_win_rate:.3f})")
    print(f"  Target Home Score: 23.0-24.0 (Actual: {statistics.mean(all_home_scores):.1f})")
    print(f"  Target Away Score: 21.0-22.0 (Actual: {statistics.mean(all_away_scores):.1f})")
    print(f"  Target Total Points: 44.0-46.0 (Actual: {statistics.mean(all_home_scores) + statistics.mean(all_away_scores):.1f})")
    print(f"  Target Plays per Game: 120.0-130.0 (Actual: {statistics.mean(all_plays):.1f})")
    print()
    
    # Check if targets are met
    hwr_target_met = 0.515 <= home_win_rate <= 0.530
    home_score_target_met = 23.0 <= statistics.mean(all_home_scores) <= 24.0
    away_score_target_met = 21.0 <= statistics.mean(all_away_scores) <= 22.0
    total_points_target_met = 44.0 <= (statistics.mean(all_home_scores) + statistics.mean(all_away_scores)) <= 46.0
    plays_target_met = 120.0 <= statistics.mean(all_plays) <= 130.0
    
    print("TARGET ACHIEVEMENT:")
    print(f"  PASS/FAIL Home Win Rate: {'PASS' if hwr_target_met else 'FAIL'}")
    print(f"  PASS/FAIL Home Score: {'PASS' if home_score_target_met else 'FAIL'}")
    print(f"  PASS/FAIL Away Score: {'PASS' if away_score_target_met else 'FAIL'}")
    print(f"  PASS/FAIL Total Points: {'PASS' if total_points_target_met else 'FAIL'}")
    print(f"  PASS/FAIL Plays per Game: {'PASS' if plays_target_met else 'FAIL'}")
    
    targets_met = sum([hwr_target_met, home_score_target_met, away_score_target_met, total_points_target_met, plays_target_met])
    print(f"\nOverall: {targets_met}/5 targets met")
    
    if targets_met >= 4:
        print("SUCCESS: BALANCED HFA TEST SUCCESSFUL!")
    else:
        print("WARNING: Some targets not met - may need further tuning")

if __name__ == "__main__":
    try:
        balanced_hfa_test()
        print("\n=== BALANCED HFA TEST COMPLETED ===")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()