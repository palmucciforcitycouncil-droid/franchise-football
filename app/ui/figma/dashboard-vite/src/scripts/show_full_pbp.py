#!/usr/bin/env python3
"""
Show full Play-by-Play (PBP) data for two games.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.models.pbp_event import PBPEvent


def show_full_pbp():
    """Show full Play-by-Play data for two games."""
    print("Full Play-by-Play Data - Two Games")
    print("=" * 50)
    
    with memory_db() as session:
        # Run mini season with 2 teams for 4 weeks
        print("Running mini season simulation...")
        out = run_mini_season(session, weeks=4, seed=2025)
        
        print(f"Generated {len(out['games'])} games")
        print(f"Games: {out['games']}")
        
        # Get PBP events for the first two games
        game_ids = out['games'][:2]
        
        for game_id in game_ids:
            print(f"\n{'='*60}")
            print(f"GAME {game_id} - FULL PLAY-BY-PLAY")
            print(f"{'='*60}")
            
            # Get all PBP events for this game
            events = session.exec(
                select(PBPEvent).where(PBPEvent.game_id == game_id)
                .order_by(PBPEvent.play_id)
            ).all()
            
            print(f"Total plays: {len(events)}")
            print()
            
            for i, event in enumerate(events, 1):
                print(f"Play {i:2d}: ", end="")
                
                # Basic play info
                play_type = getattr(event, 'play_type', 'UNKNOWN')
                down = getattr(event, 'down', 0)
                distance = getattr(event, 'distance', 0)
                yardline = getattr(event, 'yardline', 0)
                yards_gained = getattr(event, 'yards_gained', 0)
                quarter = getattr(event, 'quarter', 1)
                clock = getattr(event, 'clock', '15:00')
                
                print(f"Q{quarter} {clock} - {down} & {distance} at {yardline} - ", end="")
                
                # Play description based on type
                if play_type == 'pass':
                    passer_id = getattr(event, 'passer_id', None)
                    receiver_id = getattr(event, 'receiver_id', None)
                    completed = getattr(event, 'completed', False)
                    
                    if completed:
                        print(f"PASS COMPLETE: Player {passer_id} to Player {receiver_id} for {yards_gained} yards")
                    else:
                        print(f"PASS INCOMPLETE: Player {passer_id} to Player {receiver_id}")
                        
                elif play_type == 'run':
                    rusher_id = getattr(event, 'rusher_id', None)
                    print(f"RUSH: Player {rusher_id} for {yards_gained} yards")
                    
                elif play_type == 'punt':
                    punter_id = getattr(event, 'punter_id', None)
                    print(f"PUNT: Player {punter_id} for {yards_gained} yards")
                    
                elif play_type == 'fg':
                    kicker_id = getattr(event, 'kicker_id', None)
                    fg_good = getattr(event, 'fg_good', False)
                    if fg_good:
                        print(f"FIELD GOAL GOOD: Player {kicker_id}")
                    else:
                        print(f"FIELD GOAL MISSED: Player {kicker_id}")
                        
                elif play_type == 'kickoff':
                    kicker_id = getattr(event, 'kicker_id', None)
                    print(f"KICKOFF: Player {kicker_id}")
                    
                else:
                    print(f"{play_type.upper()}: {yards_gained} yards")
                
                # Additional details
                details = []
                
                # Points scored
                points_offense = getattr(event, 'points_offense', 0)
                if points_offense > 0:
                    details.append(f"{points_offense} points")
                
                # Turnovers
                interception = getattr(event, 'interception', False)
                if interception:
                    intercepted_by = getattr(event, 'intercepted_by_id', None)
                    details.append(f"INTERCEPTION by Player {intercepted_by}")
                
                # Sacks
                sack = getattr(event, 'sack', False)
                if sack:
                    details.append("SACK")
                
                # Print additional details if any
                if details:
                    print(f"         Details: {' | '.join(details)}")
                
                print()


if __name__ == "__main__":
    show_full_pbp()
