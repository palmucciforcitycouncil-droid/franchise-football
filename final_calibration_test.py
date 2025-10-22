#!/usr/bin/env python3
"""
FINAL PBP CALIBRATION VERIFICATION TEST
Tests the fine-tuned PBP v2 logic for realistic frequencies after adjustments.
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

def run_final_calibration_test():
    """Run final verification test for calibrated PBP v2"""
    
    print("FINAL PBP CALIBRATION VERIFICATION TEST")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8019"
    
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
    
    # Run three seasons for comprehensive validation
    seasons = [2025, 2026, 2027]
    total_games = 0
    total_plays = 0
    total_punts = 0
    total_turnovers = 0
    
    for season in seasons:
        print(f"\nSIMULATING SEASON {season}")
        print("-" * 25)
        
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
    
    print(f"\nFINAL CALIBRATION RESULTS")
    print("=" * 35)
    print(f"Total Games Simulated: {total_games}")
    print(f"Total Plays: {total_plays}")
    print(f"Total Punts: {total_punts}")
    print(f"Total Turnovers: {total_turnovers}")
    print()
    print(f"CALIBRATED METRICS:")
    print(f"Average Plays per Game: {avg_plays_per_game:.1f}")
    print(f"Average Punts per Game: {avg_punts_per_game:.1f}")
    print(f"Average Turnovers per Game: {avg_turnovers_per_game:.1f}")
    print()
    
    # Validate against targets
    print(f"TARGET VALIDATION:")
    print(f"Plays per Game: {avg_plays_per_game:.1f} (Target: 120.0-135.0)")
    print(f"Turnovers per Game: {avg_turnovers_per_game:.1f} (Target: 2.5-3.5)")
    print()
    
    # Check if targets are met
    plays_ok = 120.0 <= avg_plays_per_game <= 135.0
    turnovers_ok = 2.5 <= avg_turnovers_per_game <= 3.5
    
    print(f"Plays Target Met: {plays_ok}")
    print(f"Turnovers Target Met: {turnovers_ok}")
    
    all_targets_met = plays_ok and turnovers_ok
    print(f"\nOVERALL RESULT: {'PASS' if all_targets_met else 'FAIL'}")
    
    return all_targets_met

if __name__ == "__main__":
    try:
        success = run_final_calibration_test()
        if success:
            print("\nPBP CALIBRATION SUCCESSFUL!")
        else:
            print("\nPBP CALIBRATION NEEDS FURTHER ADJUSTMENT!")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Test failed with error: {e}")
        sys.exit(1)
