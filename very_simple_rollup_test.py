#!/usr/bin/env python3
"""
VERY SIMPLE ROLLUP TEST
Test creating stats without any complex processing.
"""

import os
import sys
import requests

def test_very_simple_rollup():
    """Test very simple rollup"""
    
    print("VERY SIMPLE ROLLUP TEST")
    print("=" * 25)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Try to create stats for game 1 directly
    print("Testing direct stats creation for game 1...")
    try:
        response = requests.post(f"{base_url}/api/stats/test-create-game-1", timeout=10)
        print(f"Direct create response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: {data.get('message', 'Game 1 stats created')}")
        else:
            print(f"ERROR: Direct create failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Direct create failed: {e}")
    
    # Test 2: Try to access stats for game 1
    print("\nTesting stats access for game 1...")
    try:
        response = requests.get(f"{base_url}/api/stats/games/1", timeout=10)
        print(f"Stats access response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Stats found for game {data.get('game_id', 'unknown')}")
        else:
            print(f"ERROR: Stats access failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Stats access failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_very_simple_rollup()
