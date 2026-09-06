# scripts/test_progression_simple.py
"""
Simple test script to verify progression persistence fix works
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.models.core_min import Player, Team
from app.models.progression import PlayerProgression
from app.services.progression import _apply_attr_deltas, _snapshot_player_ratings

def test_progression_persistence_simple():
    """Test that progression changes persist to Player attributes."""
    print("Creating test data...")
    engine = get_engine()
    
    with Session(engine) as session:
        # Create a test team
        team = Team(abbrev="TEST", name="Test Team", points=0)
        session.add(team)
        session.flush()
        
        # Create a test player with progression attributes
        player = Player(
            team_id=team.id,
            pos="QB",
            name="Test QB",
            rating=60,
            awareness=50,
            speed=50,
            strength=50,
            agility=50,
            throw_power=50,
            throw_accuracy=50,
            catching=50,
            tackling=50,
            stamina=50,
            morale=50,
            age=25,
            potential=50,
            injury_proneness=50
        )
        session.add(player)
        session.commit()
        
        print(f"Before progression - Player {player.id}: awareness={player.awareness}, throw_accuracy={player.throw_accuracy}")
        
        # Test the _apply_attr_deltas function directly
        attr_map = {
            "awareness": 5,
            "throw_accuracy": 3,
            "throw_power": 1
        }
        
        print(f"Applying deltas: {attr_map}")
        _apply_attr_deltas(session, player, attr_map)
        
        # Refresh the player to get updated values
        session.refresh(player)
        
        print(f"After progression - Player {player.id}: awareness={player.awareness}, throw_accuracy={player.throw_accuracy}, throw_power={player.throw_power}")
        
        # Verify the changes were applied
        if player.awareness == 55 and player.throw_accuracy == 53 and player.throw_power == 51:
            print("SUCCESS: Progression persistence fix works!")
            print("Player attributes were successfully updated and persisted to the database.")
        else:
            print("FAILURE: Progression persistence fix did not work")
            print(f"Expected: awareness=55, throw_accuracy=53, throw_power=51")
            print(f"Actual: awareness={player.awareness}, throw_accuracy={player.throw_accuracy}, throw_power={player.throw_power}")

if __name__ == "__main__":
    test_progression_persistence_simple()
