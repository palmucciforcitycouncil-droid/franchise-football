#!/usr/bin/env python3
"""
COMPREHENSIVE TEMPO-ADJUSTED TEST - Using Actual API
Tests the tempo adjustments implemented in PBP v2 system.
"""

import os
import sys
import requests
import json
import time
import statistics
from typing import Dict, List, Any, Tuple

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.8'  # Balanced HFA
os.environ['LEAGUE_SEED'] = '2025'

API_BASE = "http://127.0.0.1:8015/api/sim"

def test_tempo_adjusted_simulation():
    """Run comprehensive tempo-adjusted test using actual API"""
    
    print("=== COMPREHENSIVE TEMPO-ADJUSTED TEST ===")
    print("Using Actual PBP v2 API with Tempo Adjustments")
    print("Target: 120-135 Plays per Game, Balanced HFA")
    print("Target Scoring: Home 23.5-24.5, Away 21.5-22.5, Total 45-47")
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE.replace('/api/sim', '')}/health", timeout=5)
        if response.status_code != 200:
            print("ERROR: Server not responding. Please start the server first.")
            return
    except requests.exceptions.RequestException:
        print("ERROR: Server not running. Please start the server first.")
        return
    
    print("SUCCESS: Server is running")
    
    # Seed teams
    print("Seeding teams...")
    response = requests.post(f"{API_BASE}/seed-teams")
    if response.status_code != 200:
        print(f"ERROR: Failed to seed teams: {response.text}")
        return
    print("SUCCESS: Teams seeded")
    
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
        print(f"\n=== SEASON {season} ===")
        
        # Build full schedule
        print("Building schedule...")
        response = requests.post(f"{API_BASE}/schedule-all/{season}")
        if response.status_code != 200:
            print(f"ERROR: Failed to build schedule: {response.text}")
            return
        
        schedule_data = response.json()
        print(f"SUCCESS: Schedule built: {schedule_data.get('games', 0)} games")
        
        # Play entire season
        print("Playing season...")
        response = requests.post(f"{API_BASE}/play-season/{season}")
        if response.status_code != 200:
            print(f"ERROR: Failed to play season: {response.text}")
            return
        
        season_data = response.json()
        print(f"SUCCESS: Season played: {season_data.get('games', 0)} games")
        
        # Get season games data
        print("Analyzing season data...")
        response = requests.get(f"{API_BASE}/season-games/{season}")
        if response.status_code != 200:
            print(f"ERROR: Failed to get season games: {response.text}")
            return
        
        games_data = response.json()
        
        # Get PBP data for analysis
        season_plays = []
        season_punts = []
        season_turnovers = []
        season_tds = []
        season_fgs = []
        
        for week in range(1, 19):
            try:
                # Get week summary
                response = requests.get(f"{API_BASE}/diag/week-summary/{season}/{week}")
                if response.status_code == 200:
                    week_data = response.json()
                    season_plays.append(week_data.get('plays', 0))
                    season_punts.append(week_data.get('punts', 0))
                    season_turnovers.append(week_data.get('turnovers', 0))
                    season_tds.append(week_data.get('tds', 0))
                    season_fgs.append(week_data.get('field_goals', 0))
            except:
                pass  # Skip weeks with no data
        
        # Process games data
        season_home_totals = []
        season_home_passes = []
        season_away_totals = []
        season_away_passes = []
        season_home_scores = []
        season_away_scores = []
        season_margins = []
        
        for game in games_data:
            home_yards = game.get('team_yards', {}).get('home', {})
            away_yards = game.get('team_yards', {}).get('away', {})
            
            season_home_totals.append(home_yards.get('total', 0))
            season_home_passes.append(home_yards.get('pass', 0))
            season_away_totals.append(away_yards.get('total', 0))
            season_away_passes.append(away_yards.get('pass', 0))
            season_home_scores.append(game.get('home_score', 0))
            season_away_scores.append(game.get('away_score', 0))
            season_margins.append(game.get('home_score', 0) - game.get('away_score', 0))
        
        # Season averages
        home_wins = sum(1 for m in season_margins if m > 0)
        home_win_rate = home_wins / len(season_margins) if season_margins else 0
        
        avg_plays = statistics.mean(season_plays) if season_plays else 0
        avg_punts = statistics.mean(season_punts) if season_punts else 0
        avg_turnovers = statistics.mean(season_turnovers) if season_turnovers else 0
        avg_tds = statistics.mean(season_tds) if season_tds else 0
        avg_fgs = statistics.mean(season_fgs) if season_fgs else 0
        
        print(f"Games: {len(season_margins)}")
        print(f"Home Total Yards: {statistics.mean(season_home_totals):.1f} (range: {min(season_home_totals)}-{max(season_home_totals)})")
        print(f"Home Pass Yards: {statistics.mean(season_home_passes):.1f} (range: {min(season_home_passes)}-{max(season_home_passes)})")
        print(f"Away Total Yards: {statistics.mean(season_away_totals):.1f} (range: {min(season_away_totals)}-{max(season_away_totals)})")
        print(f"Away Pass Yards: {statistics.mean(season_away_passes):.1f} (range: {min(season_away_passes)}-{max(season_away_passes)})")
        print(f"Home Win Rate: {home_win_rate:.3f}")
        print(f"Avg Total Points: {statistics.mean(season_home_scores) + statistics.mean(season_away_scores):.1f}")
        print(f"Avg Plays per Game: {avg_plays:.1f}")
        print(f"Avg Punts per Game: {avg_punts:.1f}")
        print(f"Avg Turnovers per Game: {avg_turnovers:.1f}")
        print(f"Avg TDs per Game: {avg_tds:.1f}")
        print(f"Avg FGs per Game: {avg_fgs:.1f}")
        
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
    home_win_rate = home_wins / total_games if total_games > 0 else 0
    
    print("\n" + "="*60)
    print("=== TEMPO-ADJUSTED THREE-SEASON SUMMARY ===")
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
    
    # Check if targets are met
    plays_target_met = 120.0 <= statistics.mean(all_plays) <= 135.0
    hwr_target_met = 0.515 <= home_win_rate <= 0.530
    home_score_target_met = 23.5 <= statistics.mean(all_home_scores) <= 24.5
    away_score_target_met = 21.5 <= statistics.mean(all_away_scores) <= 22.5
    total_points_target_met = 45.0 <= (statistics.mean(all_home_scores) + statistics.mean(all_away_scores)) <= 47.0
    
    print("TARGET ACHIEVEMENT:")
    print(f"  PASS/FAIL Plays per Game: {'PASS' if plays_target_met else 'FAIL'}")
    print(f"  PASS/FAIL Home Win Rate: {'PASS' if hwr_target_met else 'FAIL'}")
    print(f"  PASS/FAIL Home Score: {'PASS' if home_score_target_met else 'FAIL'}")
    print(f"  PASS/FAIL Away Score: {'PASS' if away_score_target_met else 'FAIL'}")
    print(f"  PASS/FAIL Total Points: {'PASS' if total_points_target_met else 'FAIL'}")
    
    targets_met = sum([plays_target_met, hwr_target_met, home_score_target_met, away_score_target_met, total_points_target_met])
    print(f"\nOverall: {targets_met}/5 targets met")
    
    if targets_met >= 4:
        print("SUCCESS: TEMPO-ADJUSTED TEST SUCCESSFUL!")
    else:
        print("WARNING: Some targets not met - may need further tuning")

if __name__ == "__main__":
    try:
        test_tempo_adjusted_simulation()
        print("\n=== TEMPO-ADJUSTED TEST COMPLETED ===")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
