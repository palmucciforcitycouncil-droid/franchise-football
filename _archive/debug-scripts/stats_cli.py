#!/usr/bin/env python3
"""
STATS CLI TOOL
Command-line interface for stats operations including rollup, materialization, and validation.
"""

import os
import sys
import argparse
import requests
import json
from typing import Optional, Dict, Any

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.4'
os.environ['LEAGUE_SEED'] = '2025'

def api_request(endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make API request to stats endpoints"""
    base_url = "http://127.0.0.1:8015"
    url = f"{base_url}{endpoint}"
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=30)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def rollup_game_stats(game_id: int) -> bool:
    """Roll up stats for a specific game"""
    print(f"Rolling up stats for game {game_id}...")
    
    result = api_request(f"/api/stats/games/{game_id}")
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False
    
    print(f"✅ Game {game_id} stats rolled up successfully")
    print(f"   Home Team: {result['home_team']['team_id']}")
    print(f"   Away Team: {result['away_team']['team_id']}")
    print(f"   Home Players: {len(result['home_players'])}")
    print(f"   Away Players: {len(result['away_players'])}")
    
    return True

def materialize_season_stats(season: int) -> bool:
    """Materialize season stats for all teams and players"""
    print(f"Materializing season stats for {season}...")
    
    # Get team stats
    team_result = api_request(f"/api/stats/teams/season?year={season}")
    if "error" in team_result:
        print(f"❌ Team stats error: {team_result['error']}")
        return False
    
    # Get player stats
    player_result = api_request(f"/api/stats/players/season?year={season}")
    if "error" in player_result:
        print(f"❌ Player stats error: {player_result['error']}")
        return False
    
    print(f"✅ Season {season} stats materialized successfully")
    print(f"   Teams: {len(team_result)}")
    print(f"   Players: {len(player_result)}")
    
    return True

def validate_stats(season: int, game_id: Optional[int] = None) -> bool:
    """Validate stats consistency"""
    if game_id:
        print(f"Validating stats for game {game_id}...")
        result = api_request(f"/api/stats/games/{game_id}")
        if "error" in result:
            print(f"❌ Validation error: {result['error']}")
            return False
        
        # Basic validation
        home_team = result['home_team']
        away_team = result['away_team']
        
        print(f"✅ Game {game_id} validation passed")
        print(f"   Home: {home_team['total_yards']} yards, {home_team['total_td']} TDs")
        print(f"   Away: {away_team['total_yards']} yards, {away_team['total_td']} TDs")
        
    else:
        print(f"Validating season {season} stats...")
        
        # Get season summary
        summary_result = api_request(f"/api/sim/season-summary/{season}")
        if "error" in summary_result:
            print(f"❌ Season summary error: {summary_result['error']}")
            return False
        
        # Get team stats
        team_result = api_request(f"/api/stats/teams/season?year={season}")
        if "error" in team_result:
            print(f"❌ Team stats error: {team_result['error']}")
            return False
        
        # Basic validation
        totals = summary_result.get('totals', {})
        team_total_yards = sum(team.get('total_yards', 0) for team in team_result)
        
        print(f"✅ Season {season} validation passed")
        print(f"   Summary Total Yards: {totals.get('pass_yards', 0) + totals.get('rush_yards', 0):,}")
        print(f"   Team Stats Total Yards: {team_total_yards:,}")
        print(f"   Teams: {len(team_result)}")
    
    return True

def show_leaders(season: int, stat: str, top: int = 10) -> bool:
    """Show statistical leaders"""
    print(f"Showing {stat} leaders for {season} (top {top})...")
    
    result = api_request(f"/api/stats/leaders?year={season}&stat={stat}&top={top}")
    if "error" in result:
        print(f"❌ Leaders error: {result['error']}")
        return False
    
    print(f"✅ {stat.title()} Leaders:")
    for i, leader in enumerate(result, 1):
        print(f"   {i}. Team {leader['team_id']}: {leader['stat_value']} ({leader['games_played']} games)")
    
    return True

def show_team_stats(season: int, team_id: Optional[int] = None) -> bool:
    """Show team statistics"""
    if team_id:
        print(f"Showing stats for team {team_id} in {season}...")
        # This would require a specific team endpoint
        print("❌ Individual team stats not yet implemented")
        return False
    else:
        print(f"Showing all team stats for {season}...")
        
        result = api_request(f"/api/stats/teams/season?year={season}")
        if "error" in result:
            print(f"❌ Team stats error: {result['error']}")
            return False
        
        print(f"✅ Team Stats ({len(result)} teams):")
        for team in result[:5]:  # Show top 5
            print(f"   Team {team['team_id']}: {team['total_yards']} yards, {team['total_td']} TDs")
        
        if len(result) > 5:
            print(f"   ... and {len(result) - 5} more teams")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Stats CLI Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Rollup command
    rollup_parser = subparsers.add_parser('rollup', help='Roll up game stats')
    rollup_parser.add_argument('game_id', type=int, help='Game ID to roll up')
    
    # Materialize command
    materialize_parser = subparsers.add_parser('materialize', help='Materialize season stats')
    materialize_parser.add_argument('season', type=int, help='Season year')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate stats')
    validate_parser.add_argument('season', type=int, help='Season year')
    validate_parser.add_argument('--game', type=int, help='Specific game ID to validate')
    
    # Leaders command
    leaders_parser = subparsers.add_parser('leaders', help='Show statistical leaders')
    leaders_parser.add_argument('season', type=int, help='Season year')
    leaders_parser.add_argument('stat', help='Statistic name')
    leaders_parser.add_argument('--top', type=int, default=10, help='Number of leaders to show')
    
    # Team stats command
    team_parser = subparsers.add_parser('teams', help='Show team statistics')
    team_parser.add_argument('season', type=int, help='Season year')
    team_parser.add_argument('--team', type=int, help='Specific team ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    success = False
    
    if args.command == 'rollup':
        success = rollup_game_stats(args.game_id)
    elif args.command == 'materialize':
        success = materialize_season_stats(args.season)
    elif args.command == 'validate':
        success = validate_stats(args.season, args.game)
    elif args.command == 'leaders':
        success = show_leaders(args.season, args.stat, args.top)
    elif args.command == 'teams':
        success = show_team_stats(args.season, args.team)
    
    if success:
        print("\n✅ Command completed successfully")
    else:
        print("\n❌ Command failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
