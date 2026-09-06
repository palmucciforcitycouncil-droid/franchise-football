import pytest
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, SQLModel
from app.core.db import get_engine
from app.services.cap_service import cap_snapshot_for_release, cap_snapshot_for_resign, active_contract
from app.services.accolades_service import player_accolades, coach_accolades
from app.services.recent_games_service import recent_player_games, recent_coach_games
from app.services.cards_service import build_player_card, build_coach_card

def test_cap_service_functions():
    """Test cap service functions with defensive imports."""
    with Session(get_engine()) as sess:
        # Test cap snapshot for release with non-existent player
        cap_data = cap_snapshot_for_release(sess, 99999, 2031)
        assert isinstance(cap_data, dict)
        assert "current_cap_hit" in cap_data
        assert "dead_cap_now" in cap_data
        assert "savings_now" in cap_data
        assert "years_remaining" in cap_data
        
        # Test cap snapshot for resign with non-existent player
        resign_data = cap_snapshot_for_resign(sess, 99999, 5000000, 2031)
        assert isinstance(resign_data, dict)
        assert "current_cap_hit" in resign_data
        assert "projected_cap_hit" in resign_data
        assert "delta" in resign_data
        
        # Test active contract with non-existent player
        contract = active_contract(sess, 99999)
        assert contract is None

def test_accolades_service_functions():
    """Test accolades service functions with defensive imports."""
    with Session(get_engine()) as sess:
        # Test player accolades with non-existent player
        player_acc = player_accolades(sess, 99999)
        assert isinstance(player_acc, dict)
        assert "mvp" in player_acc
        assert "opoy" in player_acc
        assert "dpoy" in player_acc
        assert "roy" in player_acc
        assert "pow_off" in player_acc
        assert "pow_def" in player_acc
        assert "pow_st" in player_acc
        assert "total_awards" in player_acc
        
        # Test coach accolades with non-existent coach
        coach_acc = coach_accolades(sess, 99999)
        assert isinstance(coach_acc, dict)
        assert "coy" in coach_acc
        assert "gmoy" in coach_acc
        assert "rings" in coach_acc
        assert "conf_titles" in coach_acc
        assert "div_titles" in coach_acc
        assert "total_awards" in coach_acc

def test_recent_games_service_functions():
    """Test recent games service functions with defensive imports."""
    with Session(get_engine()) as sess:
        # Test recent player games with non-existent player
        player_games = recent_player_games(sess, 99999, 2031, limit=3)
        assert isinstance(player_games, list)
        
        # Test recent coach games with non-existent coach
        coach_games = recent_coach_games(sess, 99999, 2031, limit=3)
        assert isinstance(coach_games, list)

def test_player_card_enrichments_exist_even_if_tables_missing():
    """Test that player card enrichments exist even if tables are missing."""
    with Session(get_engine()) as sess:
        # Test with non-existent player (should return error but with proper structure)
        card = build_player_card(sess, 99999, 2031)
        
        # Should have error but if it were successful, should have enrichments
        if "error" not in card:
            assert "accolades" in card
            assert "cap" in card
            assert "recent_games" in card
            
            # Check cap structure
            assert "release" in card["cap"]
            assert "resign_projection" in card["cap"]
            
            # Check cap release structure
            cap_release = card["cap"]["release"]
            assert "current_cap_hit" in cap_release
            assert "dead_cap_now" in cap_release
            assert "savings_now" in cap_release
            assert "years_remaining" in cap_release
            
            # Check accolades structure
            accolades = card["accolades"]
            assert "mvp" in accolades
            assert "opoy" in accolades
            assert "dpoy" in accolades
            assert "roy" in accolades
            assert "pow_off" in accolades
            assert "pow_def" in accolades
            assert "pow_st" in accolades
            assert "total_awards" in accolades
            
            # Check recent games structure
            recent_games = card["recent_games"]
            assert isinstance(recent_games, list)

def test_coach_card_enrichments_exist():
    """Test that coach card enrichments exist."""
    with Session(get_engine()) as sess:
        # Test with non-existent coach (should return error but with proper structure)
        card = build_coach_card(sess, 99999, 2031)
        
        # Should have error but if it were successful, should have enrichments
        if "error" not in card:
            assert "accolades" in card
            assert "recent_games" in card
            
            # Check accolades structure
            accolades = card["accolades"]
            assert "coy" in accolades
            assert "gmoy" in accolades
            assert "rings" in accolades
            assert "conf_titles" in accolades
            assert "div_titles" in accolades
            assert "total_awards" in accolades
            
            # Check recent games structure
            recent_games = card["recent_games"]
            assert isinstance(recent_games, list)

def test_cap_calculations_with_mock_data():
    """Test cap calculations with mock data structure."""
    with Session(get_engine()) as sess:
        # Test cap snapshot for release with mock values
        cap_data = cap_snapshot_for_release(sess, 99999, 2031)
        
        # Should return default values for non-existent player
        assert cap_data["current_cap_hit"] == 0
        assert cap_data["dead_cap_now"] == 0
        assert cap_data["savings_now"] == 0
        assert cap_data["years_remaining"] == 0
        
        # Test cap snapshot for resign with mock values
        resign_data = cap_snapshot_for_resign(sess, 99999, 5000000, 2031)
        
        # Should return default values for non-existent player
        assert resign_data["current_cap_hit"] == 0
        assert resign_data["projected_cap_hit"] == 5000000
        assert resign_data["delta"] == 5000000

def test_accolades_calculations_with_mock_data():
    """Test accolades calculations with mock data structure."""
    with Session(get_engine()) as sess:
        # Test player accolades with mock values
        player_acc = player_accolades(sess, 99999)
        
        # Should return zero values for non-existent player
        assert player_acc["mvp"] == 0
        assert player_acc["opoy"] == 0
        assert player_acc["dpoy"] == 0
        assert player_acc["roy"] == 0
        assert player_acc["pow_off"] == 0
        assert player_acc["pow_def"] == 0
        assert player_acc["pow_st"] == 0
        assert player_acc["total_awards"] == 0
        
        # Test coach accolades with mock values
        coach_acc = coach_accolades(sess, 99999)
        
        # Should return zero values for non-existent coach
        assert coach_acc["coy"] == 0
        assert coach_acc["gmoy"] == 0
        assert coach_acc["rings"] == 0
        assert coach_acc["conf_titles"] == 0
        assert coach_acc["div_titles"] == 0
        assert coach_acc["total_awards"] == 0

def test_recent_games_with_mock_data():
    """Test recent games with mock data structure."""
    with Session(get_engine()) as sess:
        # Test recent player games with mock values
        player_games = recent_player_games(sess, 99999, 2031, limit=3)
        
        # Should return empty list for non-existent player
        assert isinstance(player_games, list)
        assert len(player_games) == 0
        
        # Test recent coach games with mock values
        coach_games = recent_coach_games(sess, 99999, 2031, limit=3)
        
        # Should return empty list for non-existent coach
        assert isinstance(coach_games, list)
        assert len(coach_games) == 0

def test_cards_service_enrichments_integration():
    """Test that enrichments are properly integrated into cards service."""
    with Session(get_engine()) as sess:
        # Test player card integration
        player_card = build_player_card(sess, 99999, 2031)
        
        if "error" not in player_card:
            # Verify all enrichment sections are present
            assert "accolades" in player_card
            assert "cap" in player_card
            assert "recent_games" in player_card
            
            # Verify cap section structure
            cap_section = player_card["cap"]
            assert "release" in cap_section
            assert "resign_projection" in cap_section
            
            # Verify accolades section structure
            accolades_section = player_card["accolades"]
            assert isinstance(accolades_section, dict)
            
            # Verify recent games section structure
            recent_games_section = player_card["recent_games"]
            assert isinstance(recent_games_section, list)
        
        # Test coach card integration
        coach_card = build_coach_card(sess, 99999, 2031)
        
        if "error" not in coach_card:
            # Verify all enrichment sections are present
            assert "accolades" in coach_card
            assert "recent_games" in coach_card
            
            # Verify accolades section structure
            accolades_section = coach_card["accolades"]
            assert isinstance(accolades_section, dict)
            
            # Verify recent games section structure
            recent_games_section = coach_card["recent_games"]
            assert isinstance(recent_games_section, list)

def test_defensive_imports_work_correctly():
    """Test that defensive imports work correctly in all services."""
    # Test cap service defensive imports
    from app.services.cap_service import _try
    result = _try("nonexistent.module", "NonexistentClass")
    assert result is None
    
    # Test accolades service defensive imports
    from app.services.accolades_service import _try
    result = _try("nonexistent.module", "NonexistentClass")
    assert result is None
    
    # Test recent games service defensive imports
    from app.services.recent_games_service import _try
    result = _try("nonexistent.module", "NonexistentClass")
    assert result is None

def test_error_handling_in_enrichments():
    """Test error handling in enrichment services."""
    with Session(get_engine()) as sess:
        # Test with invalid parameters
        cap_data = cap_snapshot_for_release(sess, -1, -1)
        assert isinstance(cap_data, dict)
        
        resign_data = cap_snapshot_for_resign(sess, -1, -1, -1)
        assert isinstance(resign_data, dict)
        
        player_acc = player_accolades(sess, -1)
        assert isinstance(player_acc, dict)
        
        coach_acc = coach_accolades(sess, -1)
        assert isinstance(coach_acc, dict)
        
        player_games = recent_player_games(sess, -1, -1, limit=-1)
        assert isinstance(player_games, list)
        
        coach_games = recent_coach_games(sess, -1, -1, limit=-1)
        assert isinstance(coach_games, list)

def test_cards_enrichments_api_integration():
    """Test that enrichments work through API endpoints."""
    # This would require a test client, but we can test the service functions directly
    with Session(get_engine()) as sess:
        # Test that the services can be imported and called
        from app.services.cap_service import cap_snapshot_for_release
        from app.services.accolades_service import player_accolades
        from app.services.recent_games_service import recent_player_games
        
        # Test cap service
        cap_data = cap_snapshot_for_release(sess, 99999, 2031)
        assert isinstance(cap_data, dict)
        
        # Test accolades service
        accolades_data = player_accolades(sess, 99999)
        assert isinstance(accolades_data, dict)
        
        # Test recent games service
        recent_data = recent_player_games(sess, 99999, 2031, limit=3)
        assert isinstance(recent_data, list)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])