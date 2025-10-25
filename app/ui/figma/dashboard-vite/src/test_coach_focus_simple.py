import pytest
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.coach_focus import (
    CoachFocusAssignment, TeamWeeklyCoachEffects, TeamSeasonFocusTally,
    CoachFocus, CoachRole
)
from app.services.coach_focus_service import (
    set_coach_focus, aggregate_weekly_effects, development_progression_bonus
)

def test_basic_coach_focus_functionality():
    """Test basic coach focus functionality."""
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Test setting coach focus
        set_coach_focus(session, coach_id=101, team_id=1, season=2024, week=1, 
                       role=CoachRole.HC, focus=CoachFocus.OF_GAMEPLAN)
        
        # Test aggregation
        bundle = aggregate_weekly_effects(session, 1, 2024, 1)
        
        # Should have some offensive effects
        assert bundle.run_pass_tendency_delta > 0
        assert bundle.offensive_aggression_delta > 0
        
        # Test development bonus (should be 0 with no development focus)
        bonus = development_progression_bonus(session, 1, 2024)
        assert bonus == 0.0
        
        print("✅ Basic coach focus functionality test passed!")

if __name__ == "__main__":
    test_basic_coach_focus_functionality()

