import pytest
from sqlmodel import Session, SQLModel
from app.core.db import engine
from app.services.cards_service import build_player_card, build_coach_card, build_team_card

def test_cards_service_defensive_imports():
    """Test that cards service handles missing models gracefully."""
    # Test with minimal data - should not crash even if models are missing
    with Session(engine) as sess:
        # Test player card with non-existent player
        card = build_player_card(sess, 99999, 2031)
        assert "error" in card
        assert card["error"] == "Player not found"
        
        # Test coach card with non-existent coach
        card = build_coach_card(sess, 99999, 2031)
        assert "error" in card
        assert card["error"] == "Coach model missing"
        
        # Test team card with non-existent team
        card = build_team_card(sess, 99999, 2031)
        assert "error" in card
        assert card["error"] == "Team not found"

def test_cards_service_structure():
    """Test that cards service returns proper structure even with missing models."""
    with Session(engine) as sess:
        # Test player card structure
        card = build_player_card(sess, 99999, 2031)
        assert isinstance(card, dict)
        assert "error" in card
        
        # Test coach card structure
        card = build_coach_card(sess, 99999, 2031)
        assert isinstance(card, dict)
        assert "error" in card
        
        # Test team card structure
        card = build_team_card(sess, 99999, 2031)
        assert isinstance(card, dict)
        assert "error" in card

def test_cards_service_imports():
    """Test that defensive imports work correctly."""
    from app.services.cards_service import _try
    
    # Test defensive import helper
    result = _try("nonexistent.module", "NonexistentClass")
    assert result is None
    
    # Test defensive import with existing module but nonexistent class
    result = _try("sqlmodel", "NonexistentClass")
    assert result is None
    
    # Test defensive import with existing module and class
    result = _try("sqlmodel", "SQLModel")
    assert result is not None
    assert result == SQLModel

def test_cards_service_helpers():
    """Test helper functions in cards service."""
    from app.services.cards_service import _team_name, _active_contract, _contract_ask
    
    with Session(engine) as sess:
        # Test _team_name with None team_id
        name = _team_name(sess, None)
        assert name == ""
        
        # Test _team_name with non-existent team_id
        name = _team_name(sess, 99999)
        assert name == ""
        
        # Test _active_contract with None model
        contract = _active_contract(sess, None, 1)
        assert contract is None
        
        # Test _contract_ask with None model
        ask = _contract_ask(sess, None, 1)
        assert ask is None

def test_cards_service_error_handling():
    """Test error handling in cards service."""
    with Session(engine) as sess:
        # Test with invalid parameters
        card = build_player_card(sess, -1, -1)
        assert "error" in card
        
        card = build_coach_card(sess, -1, -1)
        assert "error" in card
        
        card = build_team_card(sess, -1, -1)
        assert "error" in card

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
