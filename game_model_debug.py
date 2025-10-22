#!/usr/bin/env python3
"""
GAME MODEL DEBUG TEST
Debug the Game model to see what fields are available.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_game_model():
    """Test the Game model to see what fields are available"""
    
    print("GAME MODEL DEBUG TEST")
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
            print(f"Game object type: {type(game)}")
            print(f"Game object attributes: {dir(game)}")
            
            # Try to access different fields
            try:
                print(f"Game ID: {game.id}")
            except Exception as e:
                print(f"Error accessing game.id: {e}")
            
            try:
                print(f"Game season: {game.season}")
            except Exception as e:
                print(f"Error accessing game.season: {e}")
            
            try:
                print(f"Game home_team_id: {game.home_team_id}")
            except Exception as e:
                print(f"Error accessing game.home_team_id: {e}")
            
            try:
                print(f"Game away_team_id: {game.away_team_id}")
            except Exception as e:
                print(f"Error accessing game.away_team_id: {e}")
        
        # Close session
        s.close()
        
    except Exception as e:
        print(f"ERROR: Game model test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_game_model()
