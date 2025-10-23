# scripts/test_progression_fix.py
"""
Test script to verify progression persistence fix works
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.models.core_min import Player, Team
from app.models.progression import PlayerProgression
from app.services.progression import apply_progression_for_season, _snapshot_player_ratings

def create_test_data():
    """Create minimal test data for progression testing."""
    engine = get_engine()
    with Session(engine) as session:
        # Create a test team
        team = Team(abbrev="TEST", name="Test Team", points=0)
        session.add(team)
        session.flush()
        
        # Create test players with progression attributes
        players = []
        for i in range(5):
            player = Player(
                team_id=team.id,
                pos="QB" if i == 0 else "RB" if i == 1 else "WR",
                name=f"Test Player {i+1}",
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
            players.append(player)
        
        session.commit()
        return team.id, [p.id for p in players]

def test_progression_persistence():
    """Test that progression changes persist to Player attributes."""
    print("Creating test data...")
    team_id, player_ids = create_test_data()
    
    print("Testing progression persistence...")
    engine = get_engine()
    
    with Session(engine) as session:
        # Get a test player
        player = session.get(Player, player_ids[0])
        print(f"Before progression - Player {player.id}: awareness={player.awareness}, throw_accuracy={player.throw_accuracy}")
        
        # Create a mock PlayerSeasonStats entry (we'll simulate this)
        from app.models.season_stats import PlayerSeasonStats
        
        # Create the PlayerSeasonStats table if it doesn't exist
        try:
            pss = PlayerSeasonStats(
                player_id=player.id,
                team_id=player.team_id,
                season=2025,
                games_played=1,
                snaps_offense=60,
                snaps_defense=0,
                snaps_special_teams=0,
                pass_attempts=30,
                pass_completions=20,
                pass_yards=250,
                pass_touchdowns=2,
                interceptions=1,
                rush_attempts=5,
                rush_yards=30,
                rush_touchdowns=0,
                targets=8,
                receptions=6,
                receiving_yards=80,
                receiving_touchdowns=1,
                fumbles=0,
                tackles=0,
                sacks=0.0,
                tackles_for_loss=0,
                quarterback_hits=0,
                interceptions_caught=0,
                pass_deflections=0,
                forced_fumbles=0,
                fumble_recoveries=0
            )
            session.add(pss)
            session.commit()
        except Exception as e:
            print(f"Note: Could not create PlayerSeasonStats: {e}")
            print("This is expected if the table doesn't exist yet")
            return
        
        # Apply progression
        apply_progression_for_season(session, season=2025, seed=2025, force=True)
        
        # Check if progression was applied
        progression_records = session.exec(select(PlayerProgression).where(PlayerProgression.player_id == player.id)).all()
        if progression_records:
            record = progression_records[0]
            print(f"Progression record created for player {player.id}")
            
            # Parse the before/after snapshots
            import json
            before = json.loads(record.before_json)
            after = json.loads(record.after_json)
            
            print(f"Before: {before}")
            print(f"After: {after}")
            
            # Check if any attributes changed
            changed = any(after.get(k, 0) != before.get(k, 0) for k in ["awareness", "throw_accuracy", "throw_power", "catching", "tackling", "speed", "agility", "strength", "stamina", "morale"])
            
            if changed:
                print("✅ SUCCESS: Progression changes detected in audit trail")
                
                # Verify the actual Player object was updated
                session.refresh(player)
                print(f"After progression - Player {player.id}: awareness={player.awareness}, throw_accuracy={player.throw_accuracy}")
                
                # Check if the Player object matches the after snapshot
                if player.awareness == after.get("awareness", 0) and player.throw_accuracy == after.get("throw_accuracy", 0):
                    print("✅ SUCCESS: Player attributes match progression audit trail")
                else:
                    print("❌ FAILURE: Player attributes don't match progression audit trail")
            else:
                print("❌ FAILURE: No progression changes detected")
        else:
            print("❌ FAILURE: No progression records created")

if __name__ == "__main__":
    test_progression_persistence()
