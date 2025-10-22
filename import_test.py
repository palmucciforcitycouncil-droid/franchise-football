#!/usr/bin/env python3
"""
IMPORT TEST
Test if the stats router can be imported without errors.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test importing the stats router"""
    
    print("IMPORT TEST")
    print("=" * 15)
    
    try:
        print("Testing stats models import...")
        from app.models.stats import PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats, PlayerCareerStats
        print("SUCCESS: Stats models imported")
    except Exception as e:
        print(f"ERROR: Stats models import failed: {e}")
        return False
    
    try:
        print("Testing stats router import...")
        from app.routers.stats import router
        print("SUCCESS: Stats router imported")
    except Exception as e:
        print(f"ERROR: Stats router import failed: {e}")
        return False
    
    try:
        print("Testing main app import...")
        from app.main import app
        print("SUCCESS: Main app imported")
    except Exception as e:
        print(f"ERROR: Main app import failed: {e}")
        return False
    
    print("\nAll imports successful!")
    return True

if __name__ == "__main__":
    test_imports()
