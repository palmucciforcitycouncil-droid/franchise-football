#!/usr/bin/env python3
"""
SCHEDULING ANALYSIS - NFL Rules Compliance Verification
Analyzes three consecutive seasons to verify strict NFL scheduling rules.
"""

import os
import sys
import requests
import json
import time
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.4'
os.environ['LEAGUE_SEED'] = '2025'

API_BASE = "http://127.0.0.1:8015/api/sim"

def analyze_scheduling_compliance():
    """Analyze three seasons for NFL scheduling rules compliance"""
    
    print("=== NFL SCHEDULING RULES COMPLIANCE ANALYSIS ===")
    print("Analyzing three consecutive seasons for strict NFL rules")
    print("Target: 272 games per season, 17 games per team, proper home/away quotas")
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE.replace('/api/sim', '')}/health", timeout=5)
        if response.status_code != 200:
            print("ERROR: Server not responding. Please start the server first.")
            return
    except requests.exceptions.RequestException:
        print("ERROR: Server not running. Please start the server first.")
        return
    
    print("SUCCESS: Server is running")
    
    # Seed teams
    print("Seeding teams...")
    response = requests.post(f"{API_BASE}/seed-teams")
    if response.status_code != 200:
        print(f"ERROR: Failed to seed teams: {response.text}")
        return
    print("SUCCESS: Teams seeded")
    
    season_results = []
    
    for season in range(2025, 2028):
        print(f"\n=== SEASON {season} ANALYSIS ===")
        
        # Build full schedule
        print("Building schedule...")
        response = requests.post(f"{API_BASE}/schedule-all/{season}")
        if response.status_code != 200:
            print(f"ERROR: Failed to build schedule: {response.text}")
            return
        
        schedule_data = response.json()
        print(f"SUCCESS: Schedule built: {schedule_data.get('games', 0)} games")
        
        # Get all games for this season
        print("Analyzing schedule data...")
        response = requests.get(f"{API_BASE}/games/{season}")
        if response.status_code != 200:
            print(f"ERROR: Failed to get games: {response.text}")
            return
        
        games_data = response.json()
        
        # Analyze the schedule
        season_analysis = analyze_season_schedule(games_data, season)
        season_results.append(season_analysis)
        
        # Print season results
        print_season_results(season_analysis, season)
    
    # Print overall summary
    print_overall_summary(season_results)

def analyze_season_schedule(games_data: List[Dict], season: int) -> Dict[str, Any]:
    """Analyze a single season's schedule for NFL compliance"""
    
    # Initialize tracking
    team_games = defaultdict(int)  # Total games per team
    team_home_games = defaultdict(int)  # Home games per team
    team_away_games = defaultdict(int)  # Away games per team
    team_venue_sequence = defaultdict(list)  # Venue sequence per team
    
    # Process each game
    for game in games_data:
        home_id = game.get('home_team_id')
        away_id = game.get('away_team_id')
        week = game.get('week')
        
        if home_id and away_id and week:
            # Count total games
            team_games[home_id] += 1
            team_games[away_id] += 1
            
            # Count home/away games
            team_home_games[home_id] += 1
            team_away_games[away_id] += 1
            
            # Track venue sequence
            team_venue_sequence[home_id].append(('H', week))
            team_venue_sequence[away_id].append(('A', week))
    
    # Sort venue sequences by week for each team
    for team_id in team_venue_sequence:
        team_venue_sequence[team_id].sort(key=lambda x: x[1])
    
    # Calculate venue streaks
    max_streaks = {}
    for team_id, sequence in team_venue_sequence.items():
        max_streak = 0
        current_streak = 0
        current_venue = None
        
        for venue, week in sequence:
            if venue == current_venue:
                current_streak += 1
            else:
                current_streak = 1
                current_venue = venue
            max_streak = max(max_streak, current_streak)
        
        max_streaks[team_id] = max_streak
    
    # Count home game quotas
    home_9_count = sum(1 for count in team_home_games.values() if count == 9)
    home_8_count = sum(1 for count in team_home_games.values() if count == 8)
    
    # Check if all teams have exactly 17 games
    all_teams_17_games = all(count == 17 for count in team_games.values())
    
    # Check venue streak compliance
    max_venue_streak = max(max_streaks.values()) if max_streaks else 0
    venue_streak_compliant = max_venue_streak <= 3
    
    return {
        'season': season,
        'total_games': len(games_data),
        'teams_with_17_games': sum(1 for count in team_games.values() if count == 17),
        'teams_with_other_games': sum(1 for count in team_games.values() if count != 17),
        'all_teams_17_games': all_teams_17_games,
        'home_9_count': home_9_count,
        'home_8_count': home_8_count,
        'home_quota_compliant': home_9_count == 16 and home_8_count == 16,
        'max_venue_streak': max_venue_streak,
        'venue_streak_compliant': venue_streak_compliant,
        'team_games': dict(team_games),
        'team_home_games': dict(team_home_games),
        'team_away_games': dict(team_away_games),
        'max_streaks': max_streaks
    }

def print_season_results(analysis: Dict[str, Any], season: int):
    """Print detailed results for a single season"""
    
    print(f"SEASON {season} RESULTS:")
    print(f"  Total Games: {analysis['total_games']} (Target: 272)")
    print(f"  Teams with 17 games: {analysis['teams_with_17_games']}/32")
    print(f"  Teams with other games: {analysis['teams_with_other_games']}/32")
    print(f"  All teams have 17 games: {'YES' if analysis['all_teams_17_games'] else 'NO'}")
    print(f"  Teams with 9 home games: {analysis['home_9_count']} (Target: 16)")
    print(f"  Teams with 8 home games: {analysis['home_8_count']} (Target: 16)")
    print(f"  Home/Away quota compliant: {'YES' if analysis['home_quota_compliant'] else 'NO'}")
    print(f"  Maximum venue streak: {analysis['max_venue_streak']} (Target: ≤3)")
    print(f"  Venue streak compliant: {'YES' if analysis['venue_streak_compliant'] else 'NO'}")
    
    # Show teams with non-standard game counts
    if not analysis['all_teams_17_games']:
        print("  Teams with non-17 games:")
        for team_id, count in analysis['team_games'].items():
            if count != 17:
                print(f"    Team {team_id}: {count} games")
    
    # Show teams with non-standard home game counts
    if not analysis['home_quota_compliant']:
        print("  Teams with non-standard home games:")
        for team_id, count in analysis['team_home_games'].items():
            if count not in [8, 9]:
                print(f"    Team {team_id}: {count} home games")
    
    # Show teams with excessive venue streaks
    if not analysis['venue_streak_compliant']:
        print("  Teams with excessive venue streaks:")
        for team_id, streak in analysis['max_streaks'].items():
            if streak > 3:
                print(f"    Team {team_id}: {streak} consecutive games")

def print_overall_summary(season_results: List[Dict[str, Any]]):
    """Print overall summary across all three seasons"""
    
    print("\n" + "="*60)
    print("=== OVERALL THREE-SEASON SUMMARY ===")
    print()
    
    # Check each metric across all seasons
    total_games_compliant = all(result['total_games'] == 272 for result in season_results)
    games_per_team_compliant = all(result['all_teams_17_games'] for result in season_results)
    home_quota_compliant = all(result['home_quota_compliant'] for result in season_results)
    venue_streak_compliant = all(result['venue_streak_compliant'] for result in season_results)
    
    print("NFL RULES COMPLIANCE CHECK:")
    print(f"  Total Games (272 per season): {'PASS' if total_games_compliant else 'FAIL'}")
    print(f"  Games Per Team (17 per team): {'PASS' if games_per_team_compliant else 'FAIL'}")
    print(f"  Home/Away Quota (16 teams each): {'PASS' if home_quota_compliant else 'FAIL'}")
    print(f"  Venue Streaks (≤3 max): {'PASS' if venue_streak_compliant else 'FAIL'}")
    print()
    
    # Detailed breakdown
    print("DETAILED BREAKDOWN:")
    for i, result in enumerate(season_results, 1):
        print(f"  Season {result['season']}:")
        print(f"    Games: {result['total_games']}/272")
        print(f"    Teams 17 games: {result['teams_with_17_games']}/32")
        print(f"    Home quota: {result['home_9_count']}/16 teams with 9 home, {result['home_8_count']}/16 teams with 8 home")
        print(f"    Max streak: {result['max_venue_streak']}")
    
    print()
    
    # Overall compliance
    all_compliant = all([total_games_compliant, games_per_team_compliant, home_quota_compliant, venue_streak_compliant])
    print(f"OVERALL COMPLIANCE: {'FULLY COMPLIANT' if all_compliant else 'NON-COMPLIANT'}")
    
    if not all_compliant:
        print("\nISSUES FOUND:")
        if not total_games_compliant:
            print("  - Total games per season not equal to 272")
        if not games_per_team_compliant:
            print("  - Not all teams have exactly 17 games")
        if not home_quota_compliant:
            print("  - Home/away game quota not properly distributed")
        if not venue_streak_compliant:
            print("  - Some teams have venue streaks exceeding 3 games")

if __name__ == "__main__":
    try:
        analyze_scheduling_compliance()
        print("\n=== SCHEDULING ANALYSIS COMPLETED ===")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
