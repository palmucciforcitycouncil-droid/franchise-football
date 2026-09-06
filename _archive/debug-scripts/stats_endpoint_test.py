#!/usr/bin/env python3
"""
STATS ENDPOINT TEST
Test the stats endpoints with proper parameters.
"""

import os
import sys
import requests

def test_stats_endpoints():
    """Test the stats endpoints with proper parameters"""
    
    print("STATS ENDPOINT TEST")
    print("=" * 25)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Leaders endpoint with proper parameters
    try:
        response = requests.get(f"{base_url}/api/stats/leaders?year=2025&stat=pass_yards&top=5", timeout=10)
        print(f"Leaders endpoint response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Leaders endpoint returned {len(data)} results")
        elif response.status_code == 404:
            print("INFO: Leaders endpoint returned 404 (no data)")
        else:
            print(f"INFO: Leaders endpoint returned {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Leaders endpoint test failed: {e}")
    
    # Test 2: Player season stats endpoint
    try:
        response = requests.get(f"{base_url}/api/stats/players/season?year=2025", timeout=10)
        print(f"Player season stats response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Player season stats returned {len(data)} results")
        elif response.status_code == 404:
            print("INFO: Player season stats returned 404 (no data)")
        else:
            print(f"INFO: Player season stats returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Player season stats test failed: {e}")
    
    # Test 3: Team season stats endpoint
    try:
        response = requests.get(f"{base_url}/api/stats/teams/season?year=2025", timeout=10)
        print(f"Team season stats response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Team season stats returned {len(data)} results")
        elif response.status_code == 404:
            print("INFO: Team season stats returned 404 (no data)")
        else:
            print(f"INFO: Team season stats returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Team season stats test failed: {e}")
    
    # Test 4: Box score endpoint
    try:
        response = requests.get(f"{base_url}/api/stats/games/1", timeout=10)
        print(f"Box score response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Box score returned game {data.get('game_id', 'unknown')}")
        elif response.status_code == 404:
            print("INFO: Box score returned 404 (no data)")
        else:
            print(f"INFO: Box score returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Box score test failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_stats_endpoints()
