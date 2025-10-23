#!/usr/bin/env python3
"""
NFL Simulation Engine Calibration Report
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


def run_calibration_analysis():
    """Run calibration analysis and provide detailed report."""
    print("NFL SIMULATION ENGINE CALIBRATION ANALYSIS")
    print("=" * 60)
    
    with memory_db() as session:
        # Run the calibrated simulation
        from scripts.calibrated_nfl_sim import run_calibrated_mini_season
        out = run_calibrated_mini_season(session, weeks=4, seed=2025)
        
        print(f"Generated {len(out['games'])} games")
        print(f"Teams: {out['teams']}")
        
        # Get all PBP events
        all_events = session.exec(select(PBPEvent)).all()
        print(f"Total PBP Events: {len(all_events)}")
        
        # Analyze play types
        play_types = {}
        for event in all_events:
            play_type = event.play_type
            play_types[play_type] = play_types.get(play_type, 0) + 1
        
        print(f"\nPLAY TYPE DISTRIBUTION:")
        for play_type, count in sorted(play_types.items()):
            percentage = (count / len(all_events)) * 100
            print(f"  {play_type}: {count} plays ({percentage:.1f}%)")
        
        # Analyze by team
        print(f"\nTEAM-SPECIFIC ANALYSIS:")
        for team_id in out['teams']:
            team_events = [e for e in all_events if e.offense_team_id == team_id]
            print(f"\nTeam {team_id} (Offensive Plays): {len(team_events)}")
            
            team_play_types = {}
            total_yards = 0
            total_points = 0
            punts = 0
            fg_attempts = 0
            fg_made = 0
            
            for event in team_events:
                play_type = event.play_type
                team_play_types[play_type] = team_play_types.get(play_type, 0) + 1
                total_yards += event.yards_gained
                total_points += event.points_offense
                
                if play_type == "punt":
                    punts += 1
                elif play_type == "fg":
                    fg_attempts += 1
                    if event.points_offense > 0:
                        fg_made += 1
            
            print(f"  Play Types: {dict(team_play_types)}")
            print(f"  Total Yards: {total_yards}")
            print(f"  Total Points: {total_points}")
            print(f"  Punts: {punts}")
            print(f"  FG Attempts: {fg_attempts} (Made: {fg_made})")
        
        # Analyze defensive stats
        print(f"\nDEFENSIVE STATS ANALYSIS:")
        for team_id in out['teams']:
            def_events = [e for e in all_events if e.defense_team_id == team_id]
            sacks = sum(1 for e in def_events if e.sack)
            ints = sum(1 for e in def_events if e.interception)
            
            print(f"Team {team_id} Defense: {sacks} sacks, {ints} interceptions")
        
        # Analyze drive progression
        print(f"\nDRIVE PROGRESSION ANALYSIS:")
        drives = {}
        for event in all_events:
            drive_key = (event.game_id, event.drive_id, event.offense_team_id)
            if drive_key not in drives:
                drives[drive_key] = []
            drives[drive_key].append(event)
        
        print(f"Total Drives: {len(drives)}")
        
        # Analyze drive outcomes
        drive_outcomes = {}
        for drive_key, drive_events in drives.items():
            last_event = drive_events[-1]
            outcome = last_event.play_type
            drive_outcomes[outcome] = drive_outcomes.get(outcome, 0) + 1
        
        print(f"Drive Outcomes: {dict(drive_outcomes)}")
        
        # Calculate averages per game
        games_per_team = len(out['games']) // len(out['teams'])
        print(f"\nPER-GAME AVERAGES (4 games):")
        print(f"Games per team: {games_per_team}")
        
        for team_id in out['teams']:
            team_events = [e for e in all_events if e.offense_team_id == team_id]
            total_yards = sum(e.yards_gained for e in team_events)
            total_points = sum(e.points_offense for e in team_events)
            punts = sum(1 for e in team_events if e.play_type == "punt")
            fg_attempts = sum(1 for e in team_events if e.play_type == "fg")
            
            avg_yards = total_yards / games_per_team
            avg_points = total_points / games_per_team
            avg_punts = punts / games_per_team
            avg_fg_attempts = fg_attempts / games_per_team
            
            print(f"\nTeam {team_id}:")
            print(f"  Avg Yards/Game: {avg_yards:.1f} (Target: 325-375)")
            print(f"  Avg Points/Game: {avg_points:.1f} (Target: 22.5-30)")
            print(f"  Avg Punts/Game: {avg_punts:.1f} (Target: 3.5-4.5)")
            print(f"  Avg FG Attempts/Game: {avg_fg_attempts:.1f} (Target: 2-3)")
        
        # Identify issues
        print(f"\nCALIBRATION ISSUES IDENTIFIED:")
        print("=" * 40)
        
        total_punts = sum(1 for e in all_events if e.play_type == "punt")
        total_fg_attempts = sum(1 for e in all_events if e.play_type == "fg")
        
        if total_punts == 0:
            print("CRITICAL: No punts generated - punt logic broken")
        elif total_punts < 50:  # Should be ~60-80 punts for 8 games
            print("MAJOR: Too few punts - drive logic needs fixing")
        
        if total_fg_attempts > 100:  # Should be ~20-30 for 8 games
            print("CRITICAL: Too many FG attempts - red zone logic broken")
        elif total_fg_attempts < 10:
            print("MAJOR: Too few FG attempts - scoring logic needs work")
        
        total_sacks = sum(1 for e in all_events if e.sack)
        if total_sacks < 20:  # Should be ~40-60 sacks for 8 games
            print("MAJOR: Too few sacks - pass rush logic needs improvement")
        
        print(f"\nSUMMARY:")
        print(f"Total Punts: {total_punts} (Target: ~60-80)")
        print(f"Total FG Attempts: {total_fg_attempts} (Target: ~20-30)")
        print(f"Total Sacks: {total_sacks} (Target: ~40-60)")


if __name__ == "__main__":
    run_calibration_analysis()
