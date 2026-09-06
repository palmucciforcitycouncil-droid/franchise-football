#!/usr/bin/env python3
"""
STATS WITH DATA TEST
Test the stats endpoints after simulating some data.
"""

import os
import sys
import requests
import time

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.4'
os.environ['LEAGUE_SEED'] = '2025'

def test_stats_with_data():
    """Test the stats endpoints after simulating data"""
    
    print("STATS WITH DATA TEST")
    print("=" * 25)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Simulate a season first
    print("Simulating season 2025...")
    try:
        response = requests.post(f"{base_url}/api/sim/schedule-all/2025", timeout=30)
        if response.status_code == 200:
            print("SUCCESS: Schedule created")
        else:
            print(f"ERROR: Schedule creation failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Schedule creation failed: {e}")
        return False
    
    try:
        response = requests.post(f"{base_url}/api/sim/play-season/2025", timeout=60)
        if response.status_code == 200:
            print("SUCCESS: Season simulated")
        else:
            print(f"ERROR: Season simulation failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Season simulation failed: {e}")
        return False
    
    # Wait a moment for data to be processed
    time.sleep(2)
    
    # Test 2: Test stats endpoints now
    print("\nTesting stats endpoints...")
    
    # Test team season stats
    try:
        response = requests.get(f"{base_url}/api/stats/teams/season?year=2025", timeout=10)
        print(f"Team season stats response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Team season stats returned {len(data)} results")
            if data:
                print(f"Sample team: {data[0]}")
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
        else:
            print(f"ERROR: Player season stats returned {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Player season stats test failed: {e}")
    
    # Test leaders
    try:
        response = requests.get(f"{base_url}/api/stats/leaders?year=2025&stat=pass_yards&top=5", timeout=10)
        print(f"Leaders response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Leaders returned {len(data)} results")
        else:
            print(f"ERROR: Leaders returned {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Leaders test failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_stats_with_data()
