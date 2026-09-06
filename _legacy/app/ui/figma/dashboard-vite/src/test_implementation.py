#!/usr/bin/env python3
"""
Simple test script to verify Advanced Stats implementation.
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    try:
        print("Testing imports...")
        
        # Test DTO imports
        from app.ui.dto import GameBoxDTO, PlayerSeasonLineDTO, TeamSeasonLineDTO, LeadersDTO
        print("+ DTO models imported successfully")
        
        # Test stats services
        from app.services.stats.rollup import rollup_game_stats
        from app.services.stats.materialize import materialize_season, materialize_career
        from app.services.stats.validators import validate_game_totals
        from app.services.stats.read import get_game_box, get_leaders
        print("+ Stats services imported successfully")
        
        # Test API
        from app.ui.api_stats import router
        print("+ API router imported successfully")
        
        # Test CLI
        from app.ui.cli_stats import app as cli_app
        print("+ CLI app imported successfully")
        
        # Test models
        from app.models.stats_models import PlayerGameStats, TeamGameStats
        from app.models.pbp_event import PBPEvent
        print("+ Models imported successfully")
        
        print("\nAll imports successful!")
        return True
        
    except ImportError as e:
        print(f"ERROR: Import error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

def test_fixtures():
    """Test that fixtures exist and are valid JSON."""
    try:
        print("\nTesting fixtures...")
        
        import json
        
        # Test PBP fixture
        with open("tests/fixtures/pbp_sample_advanced.json", "r") as f:
            pbp_data = json.load(f)
        print(f"+ PBP fixture loaded: {len(pbp_data)} events")
        
        # Test expected rollup fixture
        with open("tests/fixtures/expected_rollup_snapshot.json", "r") as f:
            rollup_data = json.load(f)
        print(f"+ Expected rollup fixture loaded: game {rollup_data['game_id']}")
        
        print("+ All fixtures valid!")
        return True
        
    except FileNotFoundError as e:
        print(f"ERROR: Fixture not found: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in fixture: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

def test_api_structure():
    """Test API structure."""
    try:
        print("\nTesting API structure...")
        
        from fastapi import FastAPI
        from app.ui.api_stats import router
        
        app = FastAPI()
        app.include_router(router)
        
        # Check routes
        routes = [route.path for route in app.routes]
        expected_routes = [
            "/api/stats/games/{game_id}",
            "/api/stats/leaders",
            "/api/stats/players/season",
            "/api/stats/teams/season",
            "/api/stats/rollup/game/{game_id}",
            "/api/stats/materialize/season/{year}",
            "/api/stats/materialize/career",
            "/api/stats/validate",
            "/api/stats/health"
        ]
        
        for route in expected_routes:
            if route in routes:
                print(f"+ Route {route} found")
            else:
                print(f"ERROR: Route {route} missing")
                return False
        
        print("+ All API routes present!")
        return True
        
    except Exception as e:
        print(f"ERROR: API structure error: {e}")
        return False

def main():
    """Run all tests."""
    print("Advanced Stats Implementation Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_fixtures,
        test_api_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All tests passed! Implementation looks good.")
        return 0
    else:
        print("FAILED: Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
