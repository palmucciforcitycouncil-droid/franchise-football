#!/usr/bin/env python3
"""
STATS ROLLUP TEST
Test the stats rollup functionality.
"""

import os
import sys
import requests
import time

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.4'
os.environ['LEAGUE_SEED'] = '2025'

def test_stats_rollup():
    """Test the stats rollup functionality"""
    
    print("STATS ROLLUP TEST")
    print("=" * 20)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Roll up stats for season 2025
    print("Rolling up stats for season 2025...")
    try:
        response = requests.post(f"{base_url}/api/stats/rollup/season/2025", timeout=60)
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: {data.get('message', 'Stats rolled up')}")
        else:
            print(f"ERROR: Rollup failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR: Rollup request failed: {e}")
        return False
    
    # Wait a moment for processing
    time.sleep(2)
    
    # Test 2: Check if stats are now available
    print("\nTesting stats endpoints after rollup...")
    
    # Test team season stats
    try:
        response = requests.get(f"{base_url}/api/stats/teams/season?year=2025", timeout=10)
        print(f"Team season stats response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Team season stats returned {len(data)} results")
            if data:
                print(f"Sample team: Team {data[0]['team_id']} - {data[0]['total_yards']} yards, {data[0]['total_td']} TDs")
        else:
            print(f"ERROR: Team season stats returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Team season stats test failed: {e}")
    
    # Test player season stats
    try:
        response = requests.get(f"{base_url}/api/stats/players/season?year=2025", timeout=10)
        print(f"Player season stats response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Player season stats returned {len(data)} results")
            if data:
                print(f"Sample player: Player {data[0]['player_id']} - {data[0]['pass_yards']} pass yards")
        else:
            print(f"ERROR: Player season stats returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Player season stats test failed: {e}")
    
    # Test leaders
    try:
        response = requests.get(f"{base_url}/api/stats/leaders?year=2025&stat=pass_yards&top=5", timeout=10)
        print(f"Leaders response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Leaders returned {len(data)} results")
            if data:
                print(f"Top passer: Team {data[0]['team_id']} - {data[0]['stat_value']} yards")
        else:
            print(f"ERROR: Leaders returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Leaders test failed: {e}")
    
    # Test box score
    try:
        response = requests.get(f"{base_url}/api/stats/games/1", timeout=10)
        print(f"Box score response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Box score returned game {data.get('game_id', 'unknown')}")
        else:
            print(f"ERROR: Box score returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Box score test failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_stats_rollup()
