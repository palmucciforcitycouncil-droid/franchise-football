#!/usr/bin/env python3
"""
SIMPLE ROLLUP DEBUG TEST
Debug the rollup_game_stats function step by step.
"""

import os
import sys
import requests

def test_simple_rollup_debug():
    """Test simple rollup debugging"""
    
    print("SIMPLE ROLLUP DEBUG TEST")
    print("=" * 25)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Try to roll up just one game
    print("Testing single game rollup...")
    try:
        # First, let's find a game that exists
        response = requests.get(f"{base_url}/api/sim/pbp-v2/2025/1", timeout=10)
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            print(f"Found {len(events)} events for week 1")
            
            # Try to roll up game 1
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
        else:
            print(f"ERROR: Could not access PBP data: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Single game rollup test failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_simple_rollup_debug()
