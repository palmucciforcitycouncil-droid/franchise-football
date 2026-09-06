#!/usr/bin/env python3
"""
SIMPLE STATS API TEST
Quick test of the stats API endpoints.
"""

import os
import sys
import requests
import json

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.4'
os.environ['LEAGUE_SEED'] = '2025'

def test_stats_api():
    """Test the stats API endpoints"""
    
    print("SIMPLE STATS API TEST")
    print("=" * 30)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Server is running")
        else:
            print(f"ERROR: Server not available: {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Server connection failed: {e}")
        return False
    
    # Test 2: Check if stats router is loaded
    try:
        response = requests.get(f"{base_url}/api/stats/games/1", timeout=5)
        print(f"Stats API Response: {response.status_code}")
        if response.status_code == 404:
            print("INFO: Stats API not found - this is expected if no games exist")
        elif response.status_code == 200:
            print("SUCCESS: Stats API is working")
        else:
            print(f"INFO: Stats API returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Stats API test failed: {e}")
    
    # Test 3: Check if we need to simulate a season first
    try:
        response = requests.get(f"{base_url}/api/sim/season-summary/2025", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Season 2025 exists")
        else:
            print("INFO: Season 2025 not found - need to simulate first")
    except Exception as e:
        print(f"ERROR: Season check failed: {e}")
    
    print("\nTest completed!")
    return True

if __name__ == "__main__":
    test_stats_api()
