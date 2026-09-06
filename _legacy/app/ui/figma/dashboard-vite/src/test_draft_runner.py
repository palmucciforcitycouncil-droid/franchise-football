#!/usr/bin/env python3
"""
Simple test runner for draft functionality
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work"""
    try:
        from app.models.draft import Prospect, DraftPick, DraftState, PickStatus
        print("✅ Draft models imported successfully")
        
        from app.api.dto_draft import ProspectDTO, PickRowDTO, DraftResultsDTO, DraftBoardDTO, ActionResult
        print("✅ Draft DTOs imported successfully")
        
        from app.services.draft_service import (
            get_draft_results, get_prospects, get_draft_board, add_to_board,
            reorder_board, make_pick, sim_until_next_user_pick, advance_clock
        )
        print("✅ Draft services imported successfully")
        
        from app.api.draft import router
        print("✅ Draft API imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic draft functionality"""
    try:
        from sqlmodel import Session, create_engine, select
        from app.models.draft import Prospect, DraftPick, DraftState, PickStatus
        from app.services.draft_service import get_prospects
        
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:", echo=False)
        
        # Import all models to ensure they're registered
        from app.models.draft import Prospect, DraftPick, DraftState  # noqa: F401
        from app.models.sim_models import Team, Game, GameEvent  # noqa: F401
        from app.models.results import TeamGameStats, PlayerBox  # noqa: F401
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(engine)
        
        with Session(engine) as session:
            # Create a test prospect
            prospect = Prospect(
                first_name="Test",
                last_name="Player",
                position="QB",
                college="Test U",
                ovr=85,
                draft_grade=7.5
            )
            session.add(prospect)
            session.commit()
            session.refresh(prospect)
            
            # Test getting prospects
            prospects = get_prospects(session)
            assert len(prospects) == 1
            assert prospects[0].name == "Test Player"
            
            print("✅ Basic draft functionality works")
            return True
            
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Draft System...")
    print("=" * 50)
    
    success = True
    success &= test_imports()
    success &= test_basic_functionality()
    
    print("=" * 50)
    if success:
        print("🎉 All tests passed! Draft system is working correctly.")
    else:
        print("❌ Some tests failed. Check the errors above.")
        sys.exit(1)

