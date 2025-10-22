#!/usr/bin/env python3
"""
RNG Validation Test Script
Tests deterministic behavior and seed variation for the simulation
"""

import os
import requests
import json
import time

def test_rng_validation():
    """Test RNG deterministic behavior and seed variation"""
    
    print("RNG VALIDATION TEST")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8015"
    
    # Test 1: Deterministic Repeat (Seed 101)
    print("\nTEST 1: Deterministic Repeat (Seed 101)")
    print("-" * 40)
    
    # Set seed for first run
    os.environ['LEAGUE_SEED'] = '101'
    
    print("Running simulation with SEED = 101 (Run A)...")
    
    # Seed teams
    response = requests.post(f"{base_url}/api/sim/seed-teams")
    if response.status_code != 200:
        print(f"FAILED to seed teams: {response.status_code}")
        return False
    
    # Build schedule
    response = requests.post(f"{base_url}/api/sim/schedule/2026")
    if response.status_code != 200:
        print(f"FAILED to build schedule: {response.status_code}")
        return False
    
    # Play season
    response = requests.post(f"{base_url}/api/sim/play-season/2026")
    if response.status_code != 200:
        print(f"FAILED to play season: {response.status_code}")
        return False
    
    # Get standings for Run A
    response = requests.get(f"{base_url}/api/sim/standings/2026")
    if response.status_code != 200:
        print(f"FAILED to get standings: {response.status_code}")
        return False
    
    run_a_data = response.json()
    run_a_results = {}
    
    # Extract results for our test teams
    test_teams = ["Chiefs", "Jets", "Eagles", "Panthers", "Dolphins"]
    for team_data in run_a_data:
        team_name = team_data.get('team_name', '')
        if team_name in test_teams:
            wins = team_data.get('wins', 0)
            losses = team_data.get('losses', 0)
            run_a_results[team_name] = f"{wins}-{losses}"
    
    print("Running simulation with SEED = 101 (Run B)...")
    
    # Reset and run again with same seed
    os.environ['LEAGUE_SEED'] = '101'
    
    # Seed teams again
    response = requests.post(f"{base_url}/api/sim/seed-teams")
    
    # Build schedule again
    response = requests.post(f"{base_url}/api/sim/schedule/2026")
    
    # Play season again
    response = requests.post(f"{base_url}/api/sim/play-season/2026")
    
    # Get standings for Run B
    response = requests.get(f"{base_url}/api/sim/standings/2026")
    run_b_data = response.json()
    run_b_results = {}
    
    # Extract results for our test teams
    for team_data in run_b_data:
        team_name = team_data.get('team_name', '')
        if team_name in test_teams:
            wins = team_data.get('wins', 0)
            losses = team_data.get('losses', 0)
            run_b_results[team_name] = f"{wins}-{losses}"
    
    print("\n📋 TEST 1 RESULTS:")
    print("Team".ljust(12) + "Run A (Seed 101)".ljust(18) + "Run B (Seed 101)".ljust(18) + "Status")
    print("-" * 60)
    
    test1_passed = True
    for team in test_teams:
        run_a = run_a_results.get(team, "N/A")
        run_b = run_b_results.get(team, "N/A")
        status = "✅ Identical" if run_a == run_b else "❌ Different"
        if run_a != run_b:
            test1_passed = False
        print(f"{team.ljust(12)}{run_a.ljust(18)}{run_b.ljust(18)}{status}")
    
    print(f"\n🎯 TEST 1 OVERALL: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    
    # Test 2: Seed Variation (Seed 202)
    print("\n📊 TEST 2: Seed Variation (Seed 202)")
    print("-" * 40)
    
    # Set different seed
    os.environ['LEAGUE_SEED'] = '202'
    
    print("Running simulation with SEED = 202...")
    
    # Seed teams with new seed
    response = requests.post(f"{base_url}/api/sim/seed-teams")
    
    # Build schedule
    response = requests.post(f"{base_url}/api/sim/schedule/2026")
    
    # Play season
    response = requests.post(f"{base_url}/api/sim/play-season/2026")
    
    # Get standings for Seed 202
    response = requests.get(f"{base_url}/api/sim/standings/2026")
    seed_202_data = response.json()
    seed_202_results = {}
    
    # Extract results for our test teams
    for team_data in seed_202_data:
        team_name = team_data.get('team_name', '')
        if team_name in test_teams:
            wins = team_data.get('wins', 0)
            losses = team_data.get('losses', 0)
            seed_202_results[team_name] = f"{wins}-{losses}"
    
    print("\n📋 TEST 2 RESULTS:")
    print("Team".ljust(12) + "Test 1 (Seed 101)".ljust(18) + "Test 2 (Seed 202)".ljust(18) + "Status")
    print("-" * 60)
    
    test2_passed = True
    for team in test_teams:
        seed_101 = run_a_results.get(team, "N/A")
        seed_202 = seed_202_results.get(team, "N/A")
        status = "✅ Different" if seed_101 != seed_202 else "❌ Identical"
        if seed_101 == seed_202:
            test2_passed = False
        print(f"{team.ljust(12)}{seed_101.ljust(18)}{seed_202.ljust(18)}{status}")
    
    print(f"\n🎯 TEST 2 OVERALL: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    # Final Results
    print("\n" + "=" * 50)
    print("🏆 FINAL RNG VALIDATION RESULTS")
    print("=" * 50)
    print(f"Test 1 (Deterministic Repeat): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Seed Variation): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    overall_passed = test1_passed and test2_passed
    print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if overall_passed else '❌ SOME TESTS FAILED'}")
    
    return overall_passed

if __name__ == "__main__":
    try:
        test_rng_validation()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("Make sure the server is running on http://127.0.0.1:8015")
