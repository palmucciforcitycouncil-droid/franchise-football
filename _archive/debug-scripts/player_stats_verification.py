#!/usr/bin/env python3
"""
ENHANCED PLAYER STATS VERIFICATION TEST
Analyzes individual player statistics for Kansas City Chiefs QB.
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

def analyze_player_stats():
    """Analyze individual player statistics from PBP data"""
    
    print("ENHANCED PLAYER STATS VERIFICATION TEST")
    print("=" * 45)
    
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
    
    # Analyze Chiefs QB stats by parsing PBP data
    print(f"\nANALYZING CHIEFS QB STATS FROM PBP DATA")
    print("-" * 40)
    
    qb_pass_attempts = 0
    qb_completions = 0
    qb_passing_yards = 0
    qb_touchdowns = 0
    qb_interceptions = 0
    
    # Get all Chiefs games for the season
    for week in range(1, 19):  # 18 weeks
        try:
            # Get games for this week
            response = requests.get(f"{base_url}/api/sim/games/{season}/{week}", timeout=10)
            if response.status_code != 200:
                continue
            
            games_data = response.json()
            games = games_data.get('games', [])
            
            chiefs_game = None
            for game in games:
                if game.get('home_team_id') == chiefs_team_id or game.get('away_team_id') == chiefs_team_id:
                    chiefs_game = game
                    break
            
            if not chiefs_game:
                continue
                
            game_id = chiefs_game['id']
            is_home = chiefs_game['home_team_id'] == chiefs_team_id
            
            # Get PBP for this game
            response = requests.get(f"{base_url}/api/sim/pbp-v2/{season}/{week}", timeout=10)
            if response.status_code != 200:
                continue
            
            pbp_data = response.json()
            events = pbp_data.get('events', [])
            
            for event in events:
                if event.get('game_id') == game_id and event.get('event_type') == 'play':
                    event_desc = event.get('description', '{}')
                    try:
                        desc_data = json.loads(event_desc)
                        team = desc_data.get('team', '')
                        play_type = desc_data.get('play', '')
                        
                        # Check if this is a Chiefs play
                        if (team == 'home' and is_home) or (team == 'away' and not is_home):
                            if play_type == 'pass':
                                qb_pass_attempts += 1
                                if desc_data.get('complete', False):
                                    qb_completions += 1
                                    yards = desc_data.get('yards', 0)
                                    qb_passing_yards += max(0, yards)  # Only positive yards
                                    
                    except:
                        pass
                        
        except Exception as e:
            print(f"WARNING: Week {week} analysis error: {e}")
            continue
    
    # Also count TDs and INTs from PBP
    for week in range(1, 19):
        try:
            response = requests.get(f"{base_url}/api/sim/pbp-v2/{season}/{week}", timeout=10)
            if response.status_code != 200:
                continue
            
            pbp_data = response.json()
            events = pbp_data.get('events', [])
            
            for event in events:
                if event.get('event_type') in ['td', 'turnover']:
                    event_desc = event.get('description', '{}')
                    try:
                        desc_data = json.loads(event_desc)
                        team = desc_data.get('team', '')
                        
                        # Get game info to check if this is Chiefs
                        game_id = event.get('game_id')
                        response = requests.get(f"{base_url}/api/sim/games/{season}/{week}", timeout=10)
                        if response.status_code != 200:
                            continue
                        
                        games_data = response.json()
                        games = games_data.get('games', [])
                        
                        chiefs_game = None
                        for game in games:
                            if game.get('id') == game_id and (game.get('home_team_id') == chiefs_team_id or game.get('away_team_id') == chiefs_team_id):
                                chiefs_game = game
                                break
                        
                        if not chiefs_game:
                            continue
                            
                        is_home = chiefs_game['home_team_id'] == chiefs_team_id
                        
                        if (team == 'home' and is_home) or (team == 'away' and not is_home):
                            if event.get('event_type') == 'td' and desc_data.get('type') == 'pass':
                                qb_touchdowns += 1
                            elif event.get('event_type') == 'turnover' and desc_data.get('type') == 'interception':
                                qb_interceptions += 1
                                
                    except:
                        pass
                        
        except Exception as e:
            print(f"WARNING: Week {week} TD/INT analysis error: {e}")
            continue
    
    # Display Chiefs QB stats
    print(f"\nCHIEFS STARTING QB STATS (Season {season})")
    print("=" * 50)
    print(f"Pass Attempts: {qb_pass_attempts}")
    print(f"Pass Completions: {qb_completions}")
    print(f"Passing Yards: {qb_passing_yards}")
    print(f"Passing Touchdowns: {qb_touchdowns}")
    print(f"Interceptions: {qb_interceptions}")
    print()
    
    # Calculate completion percentage
    if qb_pass_attempts > 0:
        completion_pct = (qb_completions / qb_pass_attempts) * 100
        yards_per_attempt = qb_passing_yards / qb_pass_attempts
        td_int_ratio = qb_touchdowns / max(1, qb_interceptions)
        
        print(f"DERIVED STATS:")
        print(f"Completion Percentage: {completion_pct:.1f}%")
        print(f"Yards per Attempt: {yards_per_attempt:.1f}")
        print(f"TD/INT Ratio: {td_int_ratio:.1f}")
        print()
    
    # Verify realism
    print("REALISM CHECK:")
    print(f"Pass Attempts: {qb_pass_attempts} (NFL Range: 500-700)")
    print(f"Passing Yards: {qb_passing_yards} (NFL Range: 3500-5000)")
    print(f"Touchdowns: {qb_touchdowns} (NFL Range: 20-40)")
    print(f"Interceptions: {qb_interceptions} (NFL Range: 8-20)")
    print()
    
    # Check if stats are realistic
    attempts_realistic = 500 <= qb_pass_attempts <= 700
    yards_realistic = 3500 <= qb_passing_yards <= 5000
    tds_realistic = 20 <= qb_touchdowns <= 40
    ints_realistic = 8 <= qb_interceptions <= 20
    
    print("REALISM VALIDATION:")
    print(f"Attempts Realistic: {attempts_realistic}")
    print(f"Yards Realistic: {yards_realistic}")
    print(f"TDs Realistic: {tds_realistic}")
    print(f"INTs Realistic: {ints_realistic}")
    print()
    
    all_realistic = attempts_realistic and yards_realistic and tds_realistic and ints_realistic
    print(f"OVERALL REALISM: {'PASS' if all_realistic else 'FAIL'}")
    
    return all_realistic

if __name__ == "__main__":
    try:
        success = analyze_player_stats()
        if success:
            print("\nPLAYER STATS VERIFICATION SUCCESSFUL!")
        else:
            print("\nPLAYER STATS VERIFICATION NEEDS REVIEW!")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Test failed with error: {e}")
        sys.exit(1)
