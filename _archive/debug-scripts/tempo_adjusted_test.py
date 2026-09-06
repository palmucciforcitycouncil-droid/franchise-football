#!/usr/bin/env python3
"""
TEMPO-ADJUSTED Home Field Advantage Test - Targeting 120-135 Plays per Game
with improved clock management and reduced tempo.
"""

import os
import sys
import random
import statistics
from typing import Dict, List, Any, Tuple

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.8'  # Balanced HFA
os.environ['LEAGUE_SEED'] = '2025'

def tempo_adjusted_test():
    """Run tempo-adjusted test targeting 120-135 plays per game"""
    
    def _yardage_targets_v2_tempo(season: int, home_id: int, away_id: int) -> Tuple[int, int, int, int]:
        """Generate realistic yardage targets with tempo-adjusted pacing."""
        base_seed = int(os.environ.get("LEAGUE_SEED", "2025"))
        
        # Use different seeds for home and away teams
        home_seed = hash((season, home_id, base_seed)) & 0xFFFFFFFF
        away_seed = hash((season, away_id, base_seed + 1)) & 0xFFFFFFFF
        
        r_home = random.Random(home_seed)
        r_away = random.Random(away_seed)
        
        # Tempo-adjusted: Slightly higher yardage per play due to fewer plays
        # Target: Home 345-355, Away 335-345 (but with fewer plays)
        home_total = max(280, min(500, int(r_home.normalvariate(350, 50))))  # Centered around 350
        away_total = max(260, min(480, int(r_away.normalvariate(340, 50))))  # Centered around 340
        
        # Pass:Rush ratio ~2.2:1 (bounded 1.6..2.8)
        home_pass_ratio = max(1.6, min(2.8, r_home.normalvariate(2.2, 0.15)))
        away_pass_ratio = max(1.6, min(2.8, r_away.normalvariate(2.2, 0.15)))
        
        home_pass = int(home_total * home_pass_ratio / (home_pass_ratio + 1))
        away_pass = int(away_total * away_pass_ratio / (away_pass_ratio + 1))
        
        # Cap pass yards
        home_pass = min(home_pass, 450)
        away_pass = min(away_pass, 450)
        
        return home_total, home_pass, away_total, away_pass
    
    def _points_from_yards_v2_tempo(home_abbr: str, away_abbr: str) -> Tuple[int, int]:
        """Convert yardage to realistic scores with tempo-adjusted efficiency."""
        base_seed = int(os.environ.get("LEAGUE_SEED", "2025"))
        
        # Use different seeds for home and away teams
        home_seed = hash((home_abbr, base_seed)) & 0xFFFFFFFF
        away_seed = hash((away_abbr, base_seed + 1)) & 0xFFFFFFFF
        
        r_home = random.Random(home_seed)
        r_away = random.Random(away_seed)
        
        # Generate yardage with tempo-adjusted pacing
        home_total, home_pass, away_total, away_pass = _yardage_targets_v2_tempo(2025, 1, 2)
        
        # Tempo-adjusted: More efficient scoring due to fewer plays
        # Yards per Point: Slightly more efficient (13-20, mode ~15.5)
        home_ypp = max(13, min(20, r_home.normalvariate(15.5, 1.2)))
        away_ypp = max(13, min(20, r_away.normalvariate(15.5, 1.2)))
        
        home_base_pts = home_total / home_ypp
        away_base_pts = away_total / away_ypp
        
        # Balanced HFA: Moderate factors
        hfa_points = float(os.environ.get("HFA_POINTS", "1.8"))
        
        # 1. Moderate point boost for home team
        home_pts_raw = home_base_pts + hfa_points
        
        # 2. Slight defensive penalty for away team (reduced scoring efficiency)
        away_pts_raw = away_base_pts * 0.97  # 3% reduction in away team scoring efficiency
        
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
    
    def simulate_tempo_adjusted_pbp_events():
        """Simulate tempo-adjusted PBP events with reduced plays"""
        base_seed = int(os.environ.get("LEAGUE_SEED", "2025"))
        per_game_seed = hash((2025, 1, random.randint(1, 1000), base_seed)) & 0xFFFFFFFF
        r = random.Random(per_game_seed)
        
        # TEMPO-ADJUSTED: Reduced plays per game
        TARGET_PLAYS_PER_GAME = 127.5  # Reduced from 150 (target: 120-135)
        TARGET_PUNTS_PER_GAME = 8   # Both teams combined (7-9 range)
        TARGET_TURNOVERS_PER_GAME = 3  # Both teams combined
        
        # Simulate plays (both teams combined) - REDUCED TEMPO
        plays = max(100, min(150, int(r.normalvariate(TARGET_PLAYS_PER_GAME, 12))))  # Reduced variance
        
        # Simulate punts (both teams combined)
        punts = max(5, min(12, int(r.normalvariate(TARGET_PUNTS_PER_GAME, 1.5))))
        
        # Simulate turnovers (both teams combined)
        turnovers = max(1, min(6, int(r.normalvariate(TARGET_TURNOVERS_PER_GAME, 1))))
        
        # Simulate scoring - Slightly more efficient due to fewer plays
        tds = max(1, int(r.normalvariate(2.6, 1.1)))  # Slightly more TDs
        fgs = max(0, int(r.normalvariate(1.6, 0.8)))  # Slightly more FGs
        
        return plays, punts, turnovers, tds, fgs
    
    print("=== TEMPO-ADJUSTED HOME FIELD ADVANTAGE TEST ===")
    print("Targeting 120-135 Plays per Game (Reduced Tempo)")
    print("Balanced HFA: +1.8 points + 3% away team scoring reduction")
    print("Tempo Adjustments: Reduced plays, improved scoring efficiency")
    print("Target Scoring: Home 23.5-24.5, Away 21.5-22.5, Total 45-47")
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
            
            h_total, h_pass, a_total, a_pass = _yardage_targets_v2_tempo(season, home_id, away_id)
            h_score, a_score = _points_from_yards_v2_tempo(f"TEAM{home_id}", f"TEAM{away_id}")
            
            # Simulate tempo-adjusted PBP events
            plays, punts, turnovers, tds, fgs = simulate_tempo_adjusted_pbp_events()
            
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
        print(f"  Avg Plays per Game: {statistics.mean(season_plays):.1f}")
        print(f"  Avg Punts per Game: {statistics.mean(season_punts):.1f}")
        print(f"  Avg Turnovers per Game: {statistics.mean(season_turnovers):.1f}")
        print(f"  Avg TDs per Game: {statistics.mean(season_tds):.1f}")
        print(f"  Avg FGs per Game: {statistics.mean(season_fgs):.1f}")
        print()
        
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
    
    print("=== TEMPO-ADJUSTED THREE-SEASON SUMMARY (816 GAMES) ===")
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
    print(f"  Target Plays per Game: 120.0-135.0 (Actual: {statistics.mean(all_plays):.1f})")
    print(f"  Target Home Win Rate: 0.515-0.530 (Actual: {home_win_rate:.3f})")
    print(f"  Target Home Score: 23.5-24.5 (Actual: {statistics.mean(all_home_scores):.1f})")
    print(f"  Target Away Score: 21.5-22.5 (Actual: {statistics.mean(all_away_scores):.1f})")
    print(f"  Target Total Points: 45.0-47.0 (Actual: {statistics.mean(all_home_scores) + statistics.mean(all_away_scores):.1f})")
    print()
    
    print("STATISTICAL ANALYSIS:")
    print(f"  Home Win Rate Standard Deviation: {statistics.stdev([sum(1 for m in all_margins[i:i+272] if m > 0) / 272 for i in range(0, len(all_margins), 272)]):.3f}")
    print(f"  Total Points Standard Deviation: {statistics.stdev([all_home_scores[i] + all_away_scores[i] for i in range(len(all_home_scores))]):.1f}")
    print(f"  Home Total Yards Standard Deviation: {statistics.stdev(all_home_totals):.1f}")
    print(f"  Away Total Yards Standard Deviation: {statistics.stdev(all_away_totals):.1f}")
    print()
    
    print("MEAN AND RANGE ANALYSIS:")
    print(f"  Home Total Yards - Mean: {statistics.mean(all_home_totals):.1f}, Range: {min(all_home_totals)}-{max(all_home_totals)}")
    print(f"  Home Pass Yards - Mean: {statistics.mean(all_home_passes):.1f}, Range: {min(all_home_passes)}-{max(all_home_passes)}")
    print(f"  Away Total Yards - Mean: {statistics.mean(all_away_totals):.1f}, Range: {min(all_away_totals)}-{max(all_away_totals)}")
    print(f"  Away Pass Yards - Mean: {statistics.mean(all_away_passes):.1f}, Range: {min(all_away_passes)}-{max(all_away_passes)}")
    print(f"  Punts per Game - Mean: {statistics.mean(all_punts):.1f}, Range: {min(all_punts)}-{max(all_punts)}")
    print(f"  Turnovers per Game - Mean: {statistics.mean(all_turnovers):.1f}, Range: {min(all_turnovers)}-{max(all_turnovers)}")
    print(f"  Home Win Rate - Mean: {home_win_rate:.3f}, Range: 0.000-1.000")

if __name__ == "__main__":
    try:
        tempo_adjusted_test()
        print("\n=== TEMPO-ADJUSTED TEST COMPLETED SUCCESSFULLY ===")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
