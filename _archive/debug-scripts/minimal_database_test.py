#!/usr/bin/env python3
"""
MINIMAL DATABASE TEST
Test basic database operations to debug the rollup issue.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_database_operations():
    """Test basic database operations"""
    
    print("MINIMAL DATABASE TEST")
    print("=" * 25)
    
    try:
        print("Testing database connection...")
        from app.core.db import get_session
        from app.models.sim_models import Game, GameEvent
        from sqlalchemy import select
        
        # Get a session
        session_gen = get_session()
        s = next(session_gen)
        
        print("SUCCESS: Database session created")
        
        # Test querying games
        print("Testing games query...")
        games = s.exec(select(Game).where(Game.season == 2025)).all()
        print(f"SUCCESS: Found {len(games)} games for season 2025")
        
        if games:
            game = games[0]
            print(f"Sample game: ID {game.id}, Home {game.home_team_id}, Away {game.away_team_id}")
        
        # Test querying events
        print("Testing events query...")
        events = s.exec(select(GameEvent).where(GameEvent.game_id == 1)).all()
        print(f"SUCCESS: Found {len(events)} events for game 1")
        
        # Close session
        s.close()
        
        print("\nAll database operations successful!")
        return True
        
    except Exception as e:
        print(f"ERROR: Database operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_database_operations()
