#!/usr/bin/env python3
"""
Simple debug test for the season harness.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_test():
    """Debug the mini season runner."""
    try:
        print("Debug: Testing imports...")
        
        from app.testing.mini_season_runner import memory_db, _get_position
        from app.models.player_models import Player
        from app.models.sim_models import SimTeam as Team
        
        print("+ Imports successful")
        
        print("Debug: Testing position function...")
        pos = _get_position(0)
        print(f"+ Position function works: {pos}")
        
        print("Debug: Testing database...")
        with memory_db() as session:
            print("+ Database session created")
            
            # Test creating a team
            team = Team(
                name="Test Team",
                city="Test City",
                conference="AFC",
                division="East"
            )
            session.add(team)
            session.flush()
            print(f"+ Team created with ID: {team.id}")
            
            # Test creating a player
            player = Player(
                name="Test Player",
                position="QB",
                team_id=team.id,
                age=25
            )
            session.add(player)
            session.flush()
            print(f"+ Player created with ID: {player.id}")
            
            session.commit()
            print("+ Database operations successful")
        
        print("Debug: All tests passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: Debug test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_test()
