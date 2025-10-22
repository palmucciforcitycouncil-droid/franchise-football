#!/usr/bin/env python3
"""
MINIMAL STATS TEST
Test if the stats router is working with minimal dependencies.
"""

import os
import sys
import requests

def test_minimal_stats():
    """Test minimal stats functionality"""
    
    print("MINIMAL STATS TEST")
    print("=" * 20)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Check if stats router is loaded
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: API docs accessible")
            # Check if stats endpoints are in the docs
            if "stats" in response.text.lower():
                print("SUCCESS: Stats endpoints found in docs")
            else:
                print("WARNING: Stats endpoints not found in docs")
        else:
            print(f"ERROR: API docs not accessible: {response.status_code}")
    except Exception as e:
        print(f"ERROR: API docs test failed: {e}")
    
    # Test 2: Check if we can access the stats router directly
    try:
        response = requests.get(f"{base_url}/api/stats/", timeout=5)
        print(f"Stats root response: {response.status_code}")
        if response.status_code == 404:
            print("INFO: Stats root returns 404 (expected)")
        elif response.status_code == 200:
            print("SUCCESS: Stats root accessible")
        else:
            print(f"INFO: Stats root returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Stats root test failed: {e}")
    
    # Test 3: Check if we can access a specific stats endpoint
    try:
        response = requests.get(f"{base_url}/api/stats/leaders", timeout=5)
        print(f"Leaders endpoint response: {response.status_code}")
        if response.status_code == 422:
            print("SUCCESS: Leaders endpoint accessible (422 = missing required params)")
        elif response.status_code == 404:
            print("ERROR: Leaders endpoint not found")
        else:
            print(f"INFO: Leaders endpoint returned {response.status_code}")
    except Exception as e:
        print(f"ERROR: Leaders endpoint test failed: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_minimal_stats()
