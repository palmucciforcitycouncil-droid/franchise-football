#!/usr/bin/env python3
"""
ROW OBJECT DEBUG TEST
Debug the Row object to see what fields are available.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_row_object():
    """Test the Row object to see what fields are available"""
    
    print("ROW OBJECT DEBUG TEST")
    print("=" * 25)
    
    try:
        from app.core.db import get_session
        from app.models.sim_models import Game
        from sqlalchemy import select
        
        # Get a session
        session_gen = get_session()
        s = next(session_gen)
        
        # Test querying games
        games = s.exec(select(Game).where(Game.season == 2025)).all()
        print(f"Found {len(games)} games for season 2025")
        
        if games:
            game = games[0]
            print(f"Row object type: {type(game)}")
            print(f"Row object fields: {game._fields}")
            print(f"Row object data: {game._data}")
            
            # Try to access fields by index
            try:
                print(f"Game[0]: {game[0]}")
            except Exception as e:
                print(f"Error accessing game[0]: {e}")
            
            # Try to access fields by name
            try:
                print(f"Game['id']: {game['id']}")
            except Exception as e:
                print(f"Error accessing game['id']: {e}")
            
            # Try to access fields by attribute
            try:
                print(f"Game.id: {game.id}")
            except Exception as e:
                print(f"Error accessing game.id: {e}")
        
        # Close session
        s.close()
        
    except Exception as e:
        print(f"ERROR: Row object test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_row_object()
