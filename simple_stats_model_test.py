#!/usr/bin/env python3
"""
SIMPLE STATS MODEL TEST
Test creating a simple stats record to debug the issue.
"""

import os
import sys
import requests

def test_simple_stats_model():
    """Test creating a simple stats record"""
    
    print("SIMPLE STATS MODEL TEST")
    print("=" * 25)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Try to create a simple stats record
    print("Testing simple stats creation...")
    try:
        response = requests.post(f"{base_url}/api/stats/test-create", timeout=10)
        print(f"Test create response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: {data.get('message', 'Test stats created')}")
        else:
            print(f"ERROR: Test create failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Test create failed: {e}")
    
    # Test 2: Try to create a simple stats record with different data
    print("\nTesting simple stats creation with different data...")
    try:
        # Create a simple test endpoint that creates stats for game 1
        response = requests.post(f"{base_url}/api/stats/test-create-game-1", timeout=10)
        print(f"Test create game 1 response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: {data.get('message', 'Game 1 stats created')}")
        else:
            print(f"ERROR: Test create game 1 failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
    except Exception as e:
        print(f"ERROR: Test create game 1 failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_simple_stats_model()
