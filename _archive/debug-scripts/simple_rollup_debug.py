#!/usr/bin/env python3
"""
SIMPLE ROLLUP DEBUG TEST
Debug the stats rollup process step by step.
"""

import os
import sys
import requests

def test_simple_rollup():
    """Test simple rollup functionality"""
    
    print("SIMPLE ROLLUP DEBUG TEST")
    print("=" * 25)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Check if we can access a specific game
    print("Testing game 1 rollup...")
    try:
        response = requests.post(f"{base_url}/api/stats/rollup/game/1", timeout=30)
        print(f"Game 1 rollup response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: {data.get('message', 'Game 1 stats rolled up')}")
        else:
            print(f"ERROR: Game 1 rollup failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Game 1 rollup request failed: {e}")
    
    # Test 2: Check if we can access the game directly
    print("\nTesting game 1 access...")
    try:
        response = requests.get(f"{base_url}/api/sim/games/1", timeout=10)
        print(f"Game 1 access response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Game 1 found - {data.get('home_team_id', 'unknown')} vs {data.get('away_team_id', 'unknown')}")
        else:
            print(f"ERROR: Game 1 access failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Game 1 access failed: {e}")
    
    # Test 3: Check if we can access PBP data
    print("\nTesting PBP data access...")
    try:
        response = requests.get(f"{base_url}/api/sim/pbp-v2/2025/1", timeout=10)
        print(f"PBP data response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            print(f"SUCCESS: PBP data found - {len(events)} events")
        else:
            print(f"ERROR: PBP data access failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: PBP data access failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_simple_rollup()
