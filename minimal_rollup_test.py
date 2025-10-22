#!/usr/bin/env python3
"""
MINIMAL ROLLUP TEST
Test the minimal rollup function step by step.
"""

import os
import sys
import requests

def test_minimal_rollup():
    """Test the minimal rollup function"""
    
    print("MINIMAL ROLLUP TEST")
    print("=" * 20)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Try to roll up just one game
    print("Testing single game rollup...")
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
    
    # Test 2: Try to roll up a different game
    print("\nTesting game 2 rollup...")
    try:
        response = requests.post(f"{base_url}/api/stats/rollup/game/2", timeout=30)
        print(f"Game 2 rollup response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: {data.get('message', 'Game 2 stats rolled up')}")
        else:
            print(f"ERROR: Game 2 rollup failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Game 2 rollup request failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_minimal_rollup()
