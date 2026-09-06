#!/usr/bin/env python3
"""
MINIMAL STATS CREATION TEST
Test creating a single stats record to debug the issue.
"""

import os
import sys
import requests

def test_minimal_stats_creation():
    """Test creating minimal stats records"""
    
    print("MINIMAL STATS CREATION TEST")
    print("=" * 30)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Try to create a simple stats record
    print("Testing minimal stats creation...")
    try:
        # Create a simple test endpoint
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
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_minimal_stats_creation()
