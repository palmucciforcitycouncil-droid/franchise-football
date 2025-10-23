#!/usr/bin/env python3
"""
Generate and display team and player stats for 4 weeks with 2 teams.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, create_engine, select
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp


def show_team_and_player_stats():
    """Generate and display team and player stats for 4 weeks with 2 teams."""
    print("Team and Player Stats - 4 Weeks, 2 Teams")
    print("=" * 50)
    
    with memory_db() as session:
        # Run mini season with 2 teams for 4 weeks
        print("Running mini season simulation...")
        out = run_mini_season(session, weeks=4, seed=2025)
        
        print(f"Generated {len(out['games'])} games")
        print(f"Teams: {out['teams']}")
        print(f"Schedule: {out['schedule']}")
        
        # Get aggregated stats from PBP
        print("\nAggregating stats from Play-by-Play events...")
        agg = aggregate_truth_from_pbp(session)
        
        # Show team season stats
        print("\n" + "="*20 + " TEAM SEASON STATS " + "="*20)
        for team_id, stats in agg["team_season"].items():
            print(f"\nTeam {team_id}:")
            print(f"  Games Played: {stats.get('plays', 0)}")
            print(f"  Points Scored: {stats.get('points', 0)}")
            print(f"  Points Allowed: {stats.get('points_allowed', 0)}")
            print(f"  Total Yards: {stats.get('yards_total', 0)}")
            print(f"  Rush Yards: {stats.get('rush_yards', 0)}")
            print(f"  Pass Yards: {stats.get('pass_yards', 0)}")
            print(f"  Rush TDs: {stats.get('rush_td', 0)}")
            print(f"  Pass TDs: {stats.get('pass_td', 0)}")
            print(f"  Sacks (Defense): {stats.get('sacks_def', 0)}")
            print(f"  Interceptions (Defense): {stats.get('interceptions_def', 0)}")
            print(f"  Punts: {stats.get('punts', 0)}")
            print(f"  FG Made: {stats.get('fgm', 0)}")
            print(f"  FG Attempted: {stats.get('fga', 0)}")
            print(f"  Penalty Yards: {stats.get('penalty_yards', 0)}")
        
        # Show team game stats
        print("\n" + "="*20 + " TEAM GAME STATS " + "="*20)
        for (team_id, game_id), stats in agg["team_game"].items():
            print(f"\nTeam {team_id}, Game {game_id}:")
            print(f"  Plays: {stats.get('plays', 0)}")
            print(f"  Points: {stats.get('points', 0)}")
            print(f"  Points Allowed: {stats.get('points_allowed', 0)}")
            print(f"  Total Yards: {stats.get('yards_total', 0)}")
            print(f"  Rush Yards: {stats.get('rush_yards', 0)}")
            print(f"  Pass Yards: {stats.get('pass_yards', 0)}")
            print(f"  Rush TDs: {stats.get('rush_td', 0)}")
            print(f"  Pass TDs: {stats.get('pass_td', 0)}")
            print(f"  Sacks (Defense): {stats.get('sacks_def', 0)}")
            print(f"  Interceptions (Defense): {stats.get('interceptions_def', 0)}")
            print(f"  Punts: {stats.get('punts', 0)}")
            print(f"  FG Made: {stats.get('fgm', 0)}")
            print(f"  FG Attempted: {stats.get('fga', 0)}")
            print(f"  Penalty Yards: {stats.get('penalty_yards', 0)}")
        
        # Show player season stats
        print("\n" + "="*20 + " PLAYER SEASON STATS " + "="*20)
        for player_id, stats in agg["player_season"].items():
            print(f"\nPlayer {player_id}:")
            print(f"  Pass Attempts: {stats.get('pass_attempts', 0)}")
            print(f"  Pass Yards: {stats.get('pass_yards', 0)}")
            print(f"  Pass TDs: {stats.get('pass_td', 0)}")
            print(f"  Interceptions: {stats.get('interceptions', 0)}")
            print(f"  Rush Attempts: {stats.get('rush_attempts', 0)}")
            print(f"  Rush Yards: {stats.get('rush_yards', 0)}")
            print(f"  Rush TDs: {stats.get('rush_td', 0)}")
            print(f"  Targets: {stats.get('targets', 0)}")
            print(f"  Rec Yards: {stats.get('rec_yards', 0)}")
            print(f"  Rec TDs: {stats.get('rec_td', 0)}")
            print(f"  Sacks: {stats.get('sacks', 0)}")
            print(f"  TFL: {stats.get('tfl', 0)}")
            print(f"  Pass Breakups: {stats.get('pass_breakups', 0)}")
            print(f"  Interceptions Caught: {stats.get('interceptions_caught', 0)}")
            print(f"  Field Goals Made: {stats.get('field_goals_made', 0)}")
            print(f"  Field Goals Attempted: {stats.get('field_goals_attempted', 0)}")
            print(f"  Punts: {stats.get('punts', 0)}")
            print(f"  Punt Net Yards: {stats.get('punt_net_yards', 0)}")
            print(f"  Return TDs: {stats.get('return_td', 0)}")
        
        # Show player game stats
        print("\n" + "="*20 + " PLAYER GAME STATS " + "="*20)
        for (player_id, game_id), stats in agg["player_game"].items():
            print(f"\nPlayer {player_id}, Game {game_id}:")
            print(f"  Pass Attempts: {stats.get('pass_attempts', 0)}")
            print(f"  Pass Yards: {stats.get('pass_yards', 0)}")
            print(f"  Pass TDs: {stats.get('pass_td', 0)}")
            print(f"  Interceptions: {stats.get('interceptions', 0)}")
            print(f"  Rush Attempts: {stats.get('rush_attempts', 0)}")
            print(f"  Rush Yards: {stats.get('rush_yards', 0)}")
            print(f"  Rush TDs: {stats.get('rush_td', 0)}")
            print(f"  Targets: {stats.get('targets', 0)}")
            print(f"  Rec Yards: {stats.get('rec_yards', 0)}")
            print(f"  Rec TDs: {stats.get('rec_td', 0)}")
            print(f"  Sacks: {stats.get('sacks', 0)}")
            print(f"  TFL: {stats.get('tfl', 0)}")
            print(f"  Pass Breakups: {stats.get('pass_breakups', 0)}")
            print(f"  Interceptions Caught: {stats.get('interceptions_caught', 0)}")
            print(f"  Field Goals Made: {stats.get('field_goals_made', 0)}")
            print(f"  Field Goals Attempted: {stats.get('field_goals_attempted', 0)}")
            print(f"  Punts: {stats.get('punts', 0)}")
            print(f"  Punt Net Yards: {stats.get('punt_net_yards', 0)}")
            print(f"  Return TDs: {stats.get('return_td', 0)}")
        
        # Show game scores
        print("\n" + "="*20 + " GAME SCORES " + "="*20)
        for game_id, score in agg["game_score"].items():
            print(f"Game {game_id}: Home {score.get('home_points', 0)} - Away {score.get('away_points', 0)}")


if __name__ == "__main__":
    show_team_and_player_stats()
