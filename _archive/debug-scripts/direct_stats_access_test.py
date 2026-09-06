#!/usr/bin/env python3
"""
DIRECT STATS ACCESS TEST
Test accessing stats directly without Game records.
"""

import os
import sys
import requests

def test_direct_stats_access():
    """Test accessing stats directly"""
    
    print("DIRECT STATS ACCESS TEST")
    print("=" * 25)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Try to access team season stats
    print("Testing team season stats access...")
    try:
        response = requests.get(f"{base_url}/api/stats/teams/season?year=2025", timeout=10)
        print(f"Team season stats response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Team season stats returned {len(data)} results")
            if data:
                print(f"Sample team: Team {data[0]['team_id']} - {data[0]['total_yards']} yards")
        else:
            print(f"ERROR: Team season stats failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Team season stats failed: {e}")
    
    # Test 2: Try to access player season stats
    print("\nTesting player season stats access...")
    try:
        response = requests.get(f"{base_url}/api/stats/players/season?year=2025", timeout=10)
        print(f"Player season stats response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Player season stats returned {len(data)} results")
            if data:
                print(f"Sample player: Player {data[0]['player_id']} - {data[0]['pass_yards']} pass yards")
        else:
            print(f"ERROR: Player season stats failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Player season stats failed: {e}")
    
    # Test 3: Try to access leaders
    print("\nTesting leaders access...")
    try:
        response = requests.get(f"{base_url}/api/stats/leaders?year=2025&stat=pass_yards&top=5", timeout=10)
        print(f"Leaders response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Leaders returned {len(data)} results")
            if data:
                print(f"Top passer: Team {data[0]['team_id']} - {data[0]['stat_value']} yards")
        else:
            print(f"ERROR: Leaders failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Leaders failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_direct_stats_access()
