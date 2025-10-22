"""
Test Depth Chart Service with Persistence and Constraints
"""
import pytest
from datetime import datetime
from sqlmodel import Session, create_engine, SQLModel
from fastapi import HTTPException

from app.models.depthchart import DepthChartEntry, group_for_slot
from app.services.depthchart_service import DepthChartService

# Test database
engine = create_engine("sqlite:///:memory:", echo=False)

@pytest.fixture
def db_session():
    """Create a test database session"""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def service(db_session):
    """Create a depth chart service with test database"""
    return DepthChartService(db_session)

class TestDepthChartService:
    """Test cases for depth chart service"""

    def test_get_empty_depthchart(self, service):
        """Test getting depth chart when none exists"""
        chart = service.get_depthchart("NE", 2025)
        
        assert chart.team_id == "NE"
        assert chart.season == 2025
        assert len(chart.slots) > 0  # Should have all required slots
        
        # Check that all slots are empty
        for slot in chart.slots:
            assert slot.player_id is None
            assert slot.name is None

    def test_set_depth_slot_single(self, service):
        """Test setting a single depth slot"""
        # Set QB1
        chart = service.set_depth_slot("NE", 2025, "QB", "QB1", 212)
        
        assert chart.team_id == "NE"
        assert chart.season == 2025
        
        # Find QB1 slot
        qb1_slot = next((s for s in chart.slots if s.slot == "QB1"), None)
        assert qb1_slot is not None
        assert qb1_slot.player_id == 212
        assert qb1_slot.name == "J. Kingsley"
        assert qb1_slot.ovr == 84

    def test_set_depth_slot_duplicate_prevention(self, service):
        """Test that duplicate prevention works within position groups"""
        # Set QB1 first
        service.set_depth_slot("NE", 2025, "QB", "QB1", 212)
        
        # Try to set QB2 with same player - should fail
        with pytest.raises(HTTPException) as exc_info:
            service.set_depth_slot("NE", 2025, "QB", "QB2", 212)
        
        assert exc_info.value.status_code == 409
        assert "already assigned to QB1" in exc_info.value.detail

    def test_set_depth_slot_clear_existing(self, service):
        """Test that setting a slot to None clears it"""
        # Set QB1 first
        service.set_depth_slot("NE", 2025, "QB", "QB1", 212)
        
        # Clear QB1
        chart = service.set_depth_slot("NE", 2025, "QB", "QB1", None)
        
        qb1_slot = next((s for s in chart.slots if s.slot == "QB1"), None)
        assert qb1_slot is not None
        assert qb1_slot.player_id is None
        assert qb1_slot.name is None

    def test_set_depth_bulk_valid(self, service):
        """Test bulk setting with valid data"""
        slots = [
            {"position": "QB", "slot": "QB1", "player_id": 212},
            {"position": "QB", "slot": "QB2", "player_id": 213},
            {"position": "RB", "slot": "RB1", "player_id": 332},
            {"position": "RB", "slot": "RB2", "player_id": 411},
        ]
        
        chart = service.set_depth_bulk("NE", 2025, slots)
        
        # Verify assignments
        qb1 = next((s for s in chart.slots if s.slot == "QB1"), None)
        qb2 = next((s for s in chart.slots if s.slot == "QB2"), None)
        rb1 = next((s for s in chart.slots if s.slot == "RB1"), None)
        rb2 = next((s for s in chart.slots if s.slot == "RB2"), None)
        
        assert qb1.player_id == 212
        assert qb2.player_id == 213
        assert rb1.player_id == 332
        assert rb2.player_id == 411

    def test_set_depth_bulk_duplicate_prevention(self, service):
        """Test bulk setting with duplicates - should fail"""
        slots = [
            {"position": "QB", "slot": "QB1", "player_id": 212},
            {"position": "QB", "slot": "QB2", "player_id": 212},  # Duplicate!
        ]
        
        with pytest.raises(HTTPException) as exc_info:
            service.set_depth_bulk("NE", 2025, slots)
        
        assert exc_info.value.status_code == 409
        assert "cannot be assigned to both QB1 and QB2" in exc_info.value.detail

    def test_auto_fill_empty_slots_only(self, service):
        """Test that auto-fill only fills empty slots"""
        # Manually set QB1
        service.set_depth_slot("NE", 2025, "QB", "QB1", 212)
        
        # Auto-fill should leave QB1 alone and fill QB2
        chart, warnings = service.auto_fill("NE", 2025)
        
        qb1 = next((s for s in chart.slots if s.slot == "QB1"), None)
        qb2 = next((s for s in chart.slots if s.slot == "QB2"), None)
        
        # QB1 should remain unchanged
        assert qb1.player_id == 212
        assert qb1.name == "J. Kingsley"
        
        # QB2 should be auto-filled
        assert qb2.player_id == 213  # M. Sanders (second best QB)
        assert qb2.name == "M. Sanders"

    def test_auto_fill_all_empty_slots(self, service):
        """Test auto-fill when all slots are empty"""
        chart, warnings = service.auto_fill("NE", 2025)
        
        # Check that QB positions are filled with best available
        qb1 = next((s for s in chart.slots if s.slot == "QB1"), None)
        qb2 = next((s for s in chart.slots if s.slot == "QB2"), None)
        
        assert qb1.player_id == 212  # J. Kingsley (84 OVR)
        assert qb1.name == "J. Kingsley"
        assert qb2.player_id == 213  # M. Sanders (71 OVR)
        assert qb2.name == "M. Sanders"
        
        # Check RB positions
        rb1 = next((s for s in chart.slots if s.slot == "RB1"), None)
        rb2 = next((s for s in chart.slots if s.slot == "RB2"), None)
        
        assert rb1.player_id == 332  # T. Morrow (82 OVR)
        assert rb2.player_id == 411  # K. Carter (76 OVR)

    def test_auto_fill_preserves_manual_selections(self, service):
        """Test that auto-fill preserves all manual selections"""
        # Set multiple manual selections
        service.set_depth_slot("NE", 2025, "QB", "QB1", 212)
        service.set_depth_slot("NE", 2025, "RB", "RB1", 332)
        service.set_depth_slot("NE", 2025, "WR", "WR1", 101)
        
        # Auto-fill
        chart, warnings = service.auto_fill("NE", 2025)
        
        # Manual selections should be preserved
        qb1 = next((s for s in chart.slots if s.slot == "QB1"), None)
        rb1 = next((s for s in chart.slots if s.slot == "RB1"), None)
        wr1 = next((s for s in chart.slots if s.slot == "WR1"), None)
        
        assert qb1.player_id == 212  # Preserved
        assert rb1.player_id == 332  # Preserved
        assert wr1.player_id == 101  # Preserved
        
        # Empty slots should be filled
        qb2 = next((s for s in chart.slots if s.slot == "QB2"), None)
        rb2 = next((s for s in chart.slots if s.slot == "RB2"), None)
        wr2 = next((s for s in chart.slots if s.slot == "WR2"), None)
        
        assert qb2.player_id == 213  # Auto-filled
        assert rb2.player_id == 411  # Auto-filled
        assert wr2.player_id == 234  # Auto-filled

    def test_auto_fill_warnings(self, service):
        """Test that auto-fill generates appropriate warnings"""
        chart, warnings = service.auto_fill("NE", 2025)
        
        # Should have warnings about positions with no players
        assert len(warnings) > 0
        assert any("No" in warning and "players available" in warning for warning in warnings)

    def test_position_group_mapping(self):
        """Test position group mapping function"""
        assert group_for_slot("QB1") == "QB"
        assert group_for_slot("QB2") == "QB"
        assert group_for_slot("RB1") == "RB"
        assert group_for_slot("RB2") == "RB"
        assert group_for_slot("WR1") == "WR"
        assert group_for_slot("WR2") == "WR"
        assert group_for_slot("WR3") == "WR"
        assert group_for_slot("LT") == "LT"
        assert group_for_slot("MLB1") == "MLB"
        assert group_for_slot("MLB2") == "MLB"

    def test_persistence_across_calls(self, service):
        """Test that changes persist across service calls"""
        # Set a slot
        service.set_depth_slot("NE", 2025, "QB", "QB1", 212)
        
        # Create new service instance (simulating new request)
        from sqlmodel import Session
        with Session(engine) as new_session:
            new_service = DepthChartService(new_session)
            
            # Should still see the assignment
            chart = new_service.get_depthchart("NE", 2025)
            qb1 = next((s for s in chart.slots if s.slot == "QB1"), None)
            assert qb1.player_id == 212

    def test_different_teams_seasons(self, service):
        """Test that different teams and seasons are isolated"""
        # Set QB1 for NE 2025
        service.set_depth_slot("NE", 2025, "QB", "QB1", 212)
        
        # Set QB1 for BUF 2025 (should work - different team)
        service.set_depth_slot("BUF", 2025, "QB", "QB1", 212)
        
        # Set QB1 for NE 2024 (should work - different season)
        service.set_depth_slot("NE", 2024, "QB", "QB1", 212)
        
        # All should be independent
        ne_2025 = service.get_depthchart("NE", 2025)
        buf_2025 = service.get_depthchart("BUF", 2025)
        ne_2024 = service.get_depthchart("NE", 2024)
        
        qb1_ne_2025 = next((s for s in ne_2025.slots if s.slot == "QB1"), None)
        qb1_buf_2025 = next((s for s in buf_2025.slots if s.slot == "QB1"), None)
        qb1_ne_2024 = next((s for s in ne_2024.slots if s.slot == "QB1"), None)
        
        assert qb1_ne_2025.player_id == 212
        assert qb1_buf_2025.player_id == 212
        assert qb1_ne_2024.player_id == 212

    def test_auto_fill_after_manual_clearing(self, service):
        """Test auto-fill after manually clearing slots"""
        # Auto-fill first time
        chart1, _ = service.auto_fill("NE", 2025)
        qb1_initial = next((s for s in chart1.slots if s.slot == "QB1"), None)
        assert qb1_initial.player_id is not None
        
        # Clear QB1
        service.set_depth_slot("NE", 2025, "QB", "QB1", None)
        
        # Auto-fill again - should fill QB1
        chart2, _ = service.auto_fill("NE", 2025)
        qb1_after = next((s for s in chart2.slots if s.slot == "QB1"), None)
        assert qb1_after.player_id is not None

    def test_sorting_criteria(self, service):
        """Test that auto-fill sorts by OVR desc, POT desc, age asc"""
        # In mock data:
        # J. Kingsley: 84 OVR, 88 POT, 28 age
        # M. Sanders: 71 OVR, 82 POT, 24 age
        
        chart, _ = service.auto_fill("NE", 2025)
        
        qb1 = next((s for s in chart.slots if s.slot == "QB1"), None)
        qb2 = next((s for s in chart.slots if s.slot == "QB2"), None)
        
        # QB1 should be higher OVR
        assert qb1.player_id == 212  # J. Kingsley (84 OVR)
        assert qb2.player_id == 213  # M. Sanders (71 OVR)
