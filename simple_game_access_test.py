#!/usr/bin/env python3
"""
SIMPLE GAME ACCESS TEST
Test accessing game data to debug the rollup issue.
"""

import os
import sys
import requests

def test_simple_game_access():
    """Test simple game data access"""
    
    print("SIMPLE GAME ACCESS TEST")
    print("=" * 25)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Try to access game data directly
    print("Testing game data access...")
    try:
        # Try to get a game that exists
        response = requests.get(f"{base_url}/api/sim/games/1", timeout=10)
        print(f"Game 1 access response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Game 1 found - {data.get('home_team_id', 'unknown')} vs {data.get('away_team_id', 'unknown')}")
        else:
            print(f"ERROR: Game 1 access failed: {response.status_code}")
            
        # Try to get a different game
        response = requests.get(f"{base_url}/api/sim/games/2", timeout=10)
        print(f"Game 2 access response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Game 2 found - {data.get('home_team_id', 'unknown')} vs {data.get('away_team_id', 'unknown')}")
        else:
            print(f"ERROR: Game 2 access failed: {response.status_code}")
            
    except Exception as e:
        print(f"ERROR: Game access test failed: {e}")
    
    # Test 2: Try to access PBP data
    print("\nTesting PBP data access...")
    try:
        response = requests.get(f"{base_url}/api/sim/pbp-v2/2025/1", timeout=10)
        print(f"PBP data response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            print(f"SUCCESS: PBP data found - {len(events)} events")
            
            # Check if we have play events
            play_events = [e for e in events if e.get('event_type') == 'play']
            print(f"Play events: {len(play_events)}")
            
            if play_events:
                sample_play = play_events[0]
                print(f"Sample play: {sample_play.get('play', 'unknown')} - {sample_play.get('yards', 0)} yards")
        else:
            print(f"ERROR: PBP data access failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: PBP data access test failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_simple_game_access()
