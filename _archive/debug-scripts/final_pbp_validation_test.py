#!/usr/bin/env python3
"""
FINAL PBP VALIDATION TEST - Three Season Simulation
Tests the core PBP logic for realistic frequencies of Punts, Turnovers, and Scoring events.
"""

import os
import sys
import requests
import json
import time
from typing import Dict, List, Any

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.4'
os.environ['LEAGUE_SEED'] = '2025'

def run_three_season_validation():
    """Run comprehensive three-season simulation test"""
    
    print("FINAL PBP VALIDATION TEST - THREE SEASONS")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test server availability
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code != 200:
            print("ERROR: Server not available")
            return False
        print("SUCCESS: Server is running")
    except Exception as e:
        print(f"ERROR: Server connection failed: {e}")
        return False
    
    # Run three seasons
    seasons = [2025, 2026, 2027]
    total_games = 0
    total_plays = 0
    total_punts = 0
    total_turnovers = 0
    
    for season in seasons:
        print(f"\nSIMULATING SEASON {season}")
        print("-" * 30)
        
        # Build schedule
        try:
            response = requests.post(f"{base_url}/api/sim/schedule-all/{season}", timeout=30)
            if response.status_code != 200:
                print(f"ERROR: Schedule build failed for season {season}")
                continue
            schedule_data = response.json()
            games_count = schedule_data.get('games_created', 0)
            print(f"SUCCESS: Schedule built: {games_count} games")
        except Exception as e:
            print(f"ERROR: Schedule build error: {e}")
            continue
        
        # Play entire season
        try:
            response = requests.post(f"{base_url}/api/sim/play-season/{season}", timeout=60)
            if response.status_code != 200:
                print(f"ERROR: Season simulation failed for season {season}")
                continue
            season_data = response.json()
            print(f"SUCCESS: Season {season} completed")
        except Exception as e:
            print(f"ERROR: Season simulation error: {e}")
            continue
        
        # Analyze PBP for this season
        season_plays = 0
        season_punts = 0
        season_turnovers = 0
        
        for week in range(1, 19):  # 18 weeks
            try:
                # Get PBP for this week
                response = requests.get(f"{base_url}/api/sim/pbp-v2/{season}/{week}", timeout=10)
                if response.status_code != 200:
                    continue
                
                pbp_data = response.json()
                events = pbp_data.get('events', [])
                
                # Count event types
                for event in events:
                    event_type = event.get('event_type', '')
                    if event_type == 'play':
                        season_plays += 1
                    elif event_type == 'punt':
                        season_punts += 1
                    elif event_type == 'turnover':
                        season_turnovers += 1
                
            except Exception as e:
                print(f"WARNING: Week {week} analysis error: {e}")
                continue
        
        print(f"Season {season} Stats:")
        print(f"   Games: {games_count}")
        print(f"   Plays: {season_plays}")
        print(f"   Punts: {season_punts}")
        print(f"   Turnovers: {season_turnovers}")
        
        total_games += games_count
        total_plays += season_plays
        total_punts += season_punts
        total_turnovers += season_turnovers
    
    # Calculate final metrics
    if total_games == 0:
        print("ERROR: No games were simulated")
        return False
    
    avg_plays_per_game = total_plays / total_games
    avg_punts_per_game = total_punts / total_games
    avg_turnovers_per_game = total_turnovers / total_games
    
    print(f"\nFINAL VALIDATION RESULTS")
    print("=" * 40)
    print(f"Total Games Simulated: {total_games}")
    print(f"Total Plays: {total_plays}")
    print(f"Total Punts: {total_punts}")
    print(f"Total Turnovers: {total_turnovers}")
    print()
    print(f"KEY METRICS:")
    print(f"Average Plays per Game: {avg_plays_per_game:.1f}")
    print(f"Average Punts per Game: {avg_punts_per_game:.1f}")
    print(f"Average Turnovers per Game: {avg_turnovers_per_game:.1f}")
    print()
    
    # Validate against targets
    print(f"TARGET VALIDATION:")
    print(f"Plays per Game: {avg_plays_per_game:.1f} (Target: 120.0-135.0)")
    print(f"Punts per Game: {avg_punts_per_game:.1f} (Target: 7.0-8.5)")
    print(f"Turnovers per Game: {avg_turnovers_per_game:.1f} (Target: 2.5-3.5)")
    print()
    
    # Check if targets are met
    plays_ok = 120.0 <= avg_plays_per_game <= 135.0
    punts_ok = 7.0 <= avg_punts_per_game <= 8.5
    turnovers_ok = 2.5 <= avg_turnovers_per_game <= 3.5
    
    print(f"Plays Target Met: {plays_ok}")
    print(f"Punts Target Met: {punts_ok}")
    print(f"Turnovers Target Met: {turnovers_ok}")
    
    all_targets_met = plays_ok and punts_ok and turnovers_ok
    print(f"\nOVERALL RESULT: {'PASS' if all_targets_met else 'FAIL'}")
    
    return all_targets_met

if __name__ == "__main__":
    try:
        success = run_three_season_validation()
        if success:
            print("\nPBP VALIDATION SUCCESSFUL!")
        else:
            print("\nPBP VALIDATION FAILED!")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Test failed with error: {e}")
        sys.exit(1)
