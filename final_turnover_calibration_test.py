#!/usr/bin/env python3
"""
FINAL TURNOVER CALIBRATION TEST - Single Season
Quick verification of the final turnover rate adjustment to achieve 100% realism compliance.
"""

import os
import sys
import requests
import json

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.4'
os.environ['LEAGUE_SEED'] = '2025'

def final_turnover_calibration_test():
    """Final single-season test for turnover calibration"""
    
    print("FINAL TURNOVER CALIBRATION TEST - SINGLE SEASON")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8022"
    
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
    
    # Run single season for final verification
    season = 2025
    
    print(f"\nSIMULATING SEASON {season}")
    print("-" * 25)
    
    # Build schedule
    try:
        response = requests.post(f"{base_url}/api/sim/schedule-all/{season}", timeout=30)
        if response.status_code != 200:
            print(f"ERROR: Schedule build failed")
            return False
        schedule_data = response.json()
        games_count = schedule_data.get('games_created', 0)
        print(f"SUCCESS: Schedule built: {games_count} games")
    except Exception as e:
        print(f"ERROR: Schedule build error: {e}")
        return False
    
    # Play entire season
    try:
        response = requests.post(f"{base_url}/api/sim/play-season/{season}", timeout=60)
        if response.status_code != 200:
            print(f"ERROR: Season simulation failed")
            return False
        season_data = response.json()
        print(f"SUCCESS: Season {season} completed")
    except Exception as e:
        print(f"ERROR: Season simulation error: {e}")
        return False
    
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
    
    # Calculate metrics
    avg_plays_per_game = season_plays / games_count
    avg_punts_per_game = season_punts / games_count
    avg_turnovers_per_game = season_turnovers / games_count
    
    print(f"\nFINAL TURNOVER CALIBRATION RESULTS")
    print("=" * 40)
    print(f"Games: {games_count}")
    print(f"Plays: {season_plays}")
    print(f"Punts: {season_punts}")
    print(f"Turnovers: {season_turnovers}")
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
        success = final_turnover_calibration_test()
        if success:
            print("\nFINAL TURNOVER CALIBRATION SUCCESSFUL!")
            print("100% REALISM COMPLIANCE ACHIEVED!")
        else:
            print("\nFINAL TURNOVER CALIBRATION NEEDS FURTHER ADJUSTMENT!")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Test failed with error: {e}")
        sys.exit(1)
