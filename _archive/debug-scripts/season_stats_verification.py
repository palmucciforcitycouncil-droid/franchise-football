#!/usr/bin/env python3
"""
END-OF-SEASON STATISTICS VERIFICATION TEST
Analyzes team and player stats aggregation accuracy for Season 2026.
"""

import os
import sys
import requests
import json
from typing import Dict, List, Any

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.4'
os.environ['LEAGUE_SEED'] = '2026'

def verify_season_stats():
    """Verify end-of-season statistics aggregation"""
    
    print("END-OF-SEASON STATISTICS VERIFICATION TEST")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8023"
    
    # Test server availability
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code != 200:
            print("ERROR: Server not available")
            return False
        print("SUCCESS: Server is running")
    except Exception as e:
        print(f"ERROR: Server connection failed: {e}")
        return False
    
    season = 2026
    
    print(f"\nSIMULATING SEASON {season}")
    print("-" * 25)
    
    # Build schedule
    try:
        response = requests.post(f"{base_url}/api/sim/schedule-all/{season}", timeout=30)
        if response.status_code != 200:
            print(f"ERROR: Schedule build failed")
            return False
        schedule_data = response.json()
        games_count = schedule_data.get('games_created', 0)
        print(f"SUCCESS: Schedule built: {games_count} games")
    except Exception as e:
        print(f"ERROR: Schedule build error: {e}")
        return False
    
    # Play entire season
    try:
        response = requests.post(f"{base_url}/api/sim/play-season/{season}", timeout=60)
        if response.status_code != 200:
            print(f"ERROR: Season simulation failed")
            return False
        season_data = response.json()
        print(f"SUCCESS: Season {season} completed")
    except Exception as e:
        print(f"ERROR: Season simulation error: {e}")
        return False
    
    # Get standings to find Kansas City Chiefs
    try:
        response = requests.get(f"{base_url}/api/sim/standings/{season}", timeout=10)
        if response.status_code != 200:
            print(f"ERROR: Could not get standings")
            return False
        standings_data = response.json()
        standings = standings_data.get('standings', [])
        
        # Find Kansas City Chiefs
        chiefs_team = None
        for team in standings:
            if team.get('abbr') == 'KC':  # Kansas City Chiefs abbreviation
                chiefs_team = team
                break
        
        if not chiefs_team:
            print("ERROR: Could not find Kansas City Chiefs in standings")
            return False
            
        chiefs_team_id = chiefs_team['team_id']
        print(f"SUCCESS: Found Kansas City Chiefs (Team ID: {chiefs_team_id})")
        
    except Exception as e:
        print(f"ERROR: Standings analysis error: {e}")
        return False
    
    # Analyze Chiefs team stats by aggregating individual games
    print(f"\nANALYZING KANSAS CITY CHIEFS TEAM STATS")
    print("-" * 40)
    
    chiefs_games = []
    chiefs_total_yards = 0
    chiefs_total_points = 0
    chiefs_total_turnovers = 0
    chiefs_total_punts = 0
    
    # Get all Chiefs games for the season
    for week in range(1, 19):  # 18 weeks
        try:
            # Get games for this week
            response = requests.get(f"{base_url}/api/sim/games/{season}/{week}", timeout=10)
            if response.status_code != 200:
                continue
            
            games_data = response.json()
            games = games_data.get('games', [])
            
            for game in games:
                if game.get('home_team_id') == chiefs_team_id or game.get('away_team_id') == chiefs_team_id:
                    chiefs_games.append(game)
                    
        except Exception as e:
            print(f"WARNING: Week {week} analysis error: {e}")
            continue
    
    print(f"Chiefs Games Found: {len(chiefs_games)}")
    
    # Analyze each Chiefs game
    for game in chiefs_games:
        game_id = game['id']
        is_home = game['home_team_id'] == chiefs_team_id
        
        # Get team stats for this game
        try:
            response = requests.get(f"{base_url}/api/sim/team-stats/{season}/{game['week']}", timeout=10)
            if response.status_code != 200:
                continue
            
            team_stats_data = response.json()
            teams = team_stats_data.get('teams', [])
            
            for team_stat in teams:
                if team_stat.get('team_id') == chiefs_team_id:
                    chiefs_total_yards += team_stat.get('yards', 0)
                    chiefs_total_points += team_stat.get('points', 0)
                    chiefs_total_turnovers += team_stat.get('turnovers', 0)
                    break
                    
        except Exception as e:
            print(f"WARNING: Game {game_id} stats error: {e}")
            continue
        
        # Get PBP for punts
        try:
            response = requests.get(f"{base_url}/api/sim/pbp-v2/{season}/{game['week']}", timeout=10)
            if response.status_code != 200:
                continue
            
            pbp_data = response.json()
            events = pbp_data.get('events', [])
            
            for event in events:
                if event.get('game_id') == game_id and event.get('event_type') == 'punt':
                    event_desc = event.get('description', '{}')
                    try:
                        desc_data = json.loads(event_desc)
                        team = desc_data.get('team', '')
                        if (team == 'home' and is_home) or (team == 'away' and not is_home):
                            chiefs_total_punts += 1
                    except:
                        pass
                        
        except Exception as e:
            print(f"WARNING: Game {game_id} PBP error: {e}")
            continue
    
    # Display Chiefs team stats
    print(f"\nKANSAS CITY CHIEFS TEAM STATS (Season {season})")
    print("=" * 50)
    print(f"Games Played: {len(chiefs_games)}")
    print(f"Total Yards For: {chiefs_total_yards}")
    print(f"Total Points For: {chiefs_total_points}")
    print(f"Total Turnovers Lost: {chiefs_total_turnovers}")
    print(f"Total Punts: {chiefs_total_punts}")
    print()
    
    # Calculate averages
    if len(chiefs_games) > 0:
        avg_yards = chiefs_total_yards / len(chiefs_games)
        avg_points = chiefs_total_points / len(chiefs_games)
        avg_turnovers = chiefs_total_turnovers / len(chiefs_games)
        avg_punts = chiefs_total_punts / len(chiefs_games)
        
        print(f"AVERAGES PER GAME:")
        print(f"Yards per Game: {avg_yards:.1f}")
        print(f"Points per Game: {avg_points:.1f}")
        print(f"Turnovers per Game: {avg_turnovers:.1f}")
        print(f"Punts per Game: {avg_punts:.1f}")
        print()
    
    # Note: Player stats would require additional endpoints or database queries
    # For now, we'll focus on team-level aggregation verification
    print("NOTE: Player-level stats analysis would require additional")
    print("endpoints or direct database access to individual player records.")
    print()
    
    # Verify realism
    print("REALISM CHECK:")
    print(f"Yards per Game: {avg_yards:.1f} (NFL Range: 300-400)")
    print(f"Points per Game: {avg_points:.1f} (NFL Range: 20-30)")
    print(f"Turnovers per Game: {avg_turnovers:.1f} (NFL Range: 1.5-2.5)")
    print(f"Punts per Game: {avg_punts:.1f} (NFL Range: 3-5)")
    print()
    
    # Check if stats are realistic
    yards_realistic = 300 <= avg_yards <= 400
    points_realistic = 20 <= avg_points <= 30
    turnovers_realistic = 1.5 <= avg_turnovers <= 2.5
    punts_realistic = 3 <= avg_punts <= 5
    
    print("REALISM VALIDATION:")
    print(f"Yards Realistic: {yards_realistic}")
    print(f"Points Realistic: {points_realistic}")
    print(f"Turnovers Realistic: {turnovers_realistic}")
    print(f"Punts Realistic: {punts_realistic}")
    print()
    
    all_realistic = yards_realistic and points_realistic and turnovers_realistic and punts_realistic
    print(f"OVERALL REALISM: {'PASS' if all_realistic else 'FAIL'}")
    
    return all_realistic

if __name__ == "__main__":
    try:
        success = verify_season_stats()
        if success:
            print("\nSTATISTICS VERIFICATION SUCCESSFUL!")
        else:
            print("\nSTATISTICS VERIFICATION NEEDS REVIEW!")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Test failed with error: {e}")
        sys.exit(1)
