#!/usr/bin/env python3
"""
CRITICAL: Play Count Verification Analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.testing.mini_season_runner import memory_db
from app.models.pbp_event import PBPEvent
from app.models.player_models import Player
import random
import json


def verify_play_count_scope():
    """CRITICAL: Verify if play counts are for both teams or one team."""
    print("CRITICAL PLAY COUNT VERIFICATION")
    print("=" * 50)
    
    with memory_db() as session:
        # Run the ORIGINAL simulation (not calibrated)
        from app.testing.mini_season_runner import run_mini_season
        out = run_mini_season(session, weeks=4, seed=2025)
        
        print(f"Generated {len(out['games'])} games")
        print(f"Teams: {out['teams']}")
        
        # Get all PBP events
        all_events = session.exec(select(PBPEvent)).all()
        print(f"Total PBP Events: {len(all_events)}")
        
        # Analyze by game
        print(f"\nGAME-BY-GAME ANALYSIS:")
        games = {}
        for event in all_events:
            game_id = event.game_id
            if game_id not in games:
                games[game_id] = []
            games[game_id].append(event)
        
        for game_id in sorted(games.keys()):
            game_events = games[game_id]
            print(f"\nGame {game_id}: {len(game_events)} total plays")
            
            # Analyze by team
            team_plays = {}
            for event in game_events:
                team_id = event.offense_team_id
                team_plays[team_id] = team_plays.get(team_id, 0) + 1
            
            print(f"  Team breakdown: {dict(team_plays)}")
            
            # Calculate total offensive plays for both teams
            total_offensive_plays = sum(team_plays.values())
            print(f"  Total offensive plays (both teams): {total_offensive_plays}")
            
            # Show first few plays to verify team assignment
            print(f"  First 5 plays:")
            for i, event in enumerate(game_events[:5]):
                print(f"    Play {i+1}: Team {event.offense_team_id} - {event.play_type}")
        
        # Now run the CALIBRATED simulation for comparison
        print(f"\n" + "="*50)
        print("CALIBRATED SIMULATION COMPARISON")
        print("="*50)
        
        # Clear and run calibrated
        events_to_delete = session.exec(select(PBPEvent)).all()
        for event in events_to_delete:
            session.delete(event)
        players_to_delete = session.exec(select(Player)).all()
        for player in players_to_delete:
            session.delete(player)
        session.commit()
        
        from scripts.calibrated_nfl_sim import run_calibrated_mini_season
        out_cal = run_calibrated_mini_season(session, weeks=4, seed=2025)
        
        all_events_cal = session.exec(select(PBPEvent)).all()
        print(f"Calibrated Total PBP Events: {len(all_events_cal)}")
        
        # Analyze calibrated by game
        games_cal = {}
        for event in all_events_cal:
            game_id = event.game_id
            if game_id not in games_cal:
                games_cal[game_id] = []
            games_cal[game_id].append(event)
        
        for game_id in sorted(games_cal.keys()):
            game_events = games_cal[game_id]
            print(f"\nCalibrated Game {game_id}: {len(game_events)} total plays")
            
            # Analyze by team
            team_plays = {}
            for event in game_events:
                team_id = event.offense_team_id
                team_plays[team_id] = team_plays.get(team_id, 0) + 1
            
            print(f"  Team breakdown: {dict(team_plays)}")
            total_offensive_plays = sum(team_plays.values())
            print(f"  Total offensive plays (both teams): {total_offensive_plays}")
        
        # VERIFICATION RESULT
        print(f"\n" + "="*60)
        print("VERIFICATION RESULT")
        print("="*60)
        
        # Calculate averages
        original_avg_plays = len(all_events) / len(games) if games else 0
        calibrated_avg_plays = len(all_events_cal) / len(games_cal) if games_cal else 0
        
        print(f"ORIGINAL SIMULATION:")
        print(f"  Average plays per game: {original_avg_plays:.1f}")
        print(f"  Games with 67-77 plays: {[g for g in games.values() if 60 <= len(g) <= 80]}")
        
        print(f"\nCALIBRATED SIMULATION:")
        print(f"  Average plays per game: {calibrated_avg_plays:.1f}")
        
        print(f"\nCONCLUSION:")
        if original_avg_plays < 100:
            print(f"  The 67-77 play counts were for BOTH TEAMS COMBINED")
            print(f"  This indicates games are terminating prematurely")
            print(f"  Target should be 130-140 plays per game (both teams)")
        else:
            print(f"  The 67-77 play counts were for ONE TEAM ONLY")
            print(f"  This indicates normal game length but poor efficiency")
            print(f"  Target should be 65-70 plays per team (130-140 total)")


if __name__ == "__main__":
    verify_play_count_scope()
