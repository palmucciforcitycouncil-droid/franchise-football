"""
Test Depth Chart API endpoints with Persistence and Constraints
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from app.main import app
from app.models.depthchart import DepthChartEntry

# Create test database
engine = create_engine("sqlite:///:memory:", echo=False)

# Create tables
SQLModel.metadata.create_all(engine)

# Override the database dependency
def get_test_db():
    from sqlmodel import Session
    with Session(engine) as session:
        yield session

# Patch the dependency
from app.api.routers.depthchart import get_db
app.dependency_overrides[get_db] = get_test_db

client = TestClient(app)

class TestDepthChartAPI:
    """Test cases for depth chart API endpoints"""

    def test_get_depth_chart_empty(self):
        """Test getting depth chart when none exists"""
        response = client.get("/api/teams/NE/depthchart?season=2025")
        assert response.status_code == 200
        
        data = response.json()
        assert data["team_id"] == "NE"
        assert data["season"] == 2025
        assert "slots" in data
        assert len(data["slots"]) > 0
        
        # All slots should be empty initially
        for slot in data["slots"]:
            assert slot["player_id"] is None
            assert slot["name"] is None

    def test_patch_single_slot(self):
        """Test updating a single slot"""
        response = client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": 212
        })
        
        assert response.status_code == 200
        data = response.json()
        
        qb1_slot = next((s for s in data["slots"] if s["slot"] == "QB1"), None)
        assert qb1_slot is not None
        assert qb1_slot["player_id"] == 212
        assert qb1_slot["name"] == "J. Kingsley"
        assert qb1_slot["ovr"] == 84

    def test_patch_slot_duplicate_prevention(self):
        """Test that duplicate prevention returns 409"""
        # Set QB1 first
        client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": 212
        })
        
        # Try to set QB2 with same player - should fail
        response = client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB2",
            "player_id": 212
        })
        
        assert response.status_code == 409
        data = response.json()
        assert "already assigned to QB1" in data["detail"]

    def test_patch_clear_slot(self):
        """Test clearing a slot by setting player_id to null"""
        # Set QB1 first
        client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": 212
        })
        
        # Clear QB1
        response = client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": None
        })
        
        assert response.status_code == 200
        data = response.json()
        
        qb1_slot = next((s for s in data["slots"] if s["slot"] == "QB1"), None)
        assert qb1_slot is not None
        assert qb1_slot["player_id"] is None
        assert qb1_slot["name"] is None

    def test_put_bulk_update(self):
        """Test bulk updating depth chart"""
        slots = [
            {"position": "QB", "slot": "QB1", "player_id": 212},
            {"position": "QB", "slot": "QB2", "player_id": 213},
            {"position": "RB", "slot": "RB1", "player_id": 332},
            {"position": "RB", "slot": "RB2", "player_id": 411},
        ]
        
        response = client.put("/api/teams/NE/depthchart", json={
            "season": 2025,
            "slots": slots
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify assignments
        qb1 = next((s for s in data["slots"] if s["slot"] == "QB1"), None)
        qb2 = next((s for s in data["slots"] if s["slot"] == "QB2"), None)
        rb1 = next((s for s in data["slots"] if s["slot"] == "RB1"), None)
        rb2 = next((s for s in data["slots"] if s["slot"] == "RB2"), None)
        
        assert qb1["player_id"] == 212
        assert qb2["player_id"] == 213
        assert rb1["player_id"] == 332
        assert rb2["player_id"] == 411

    def test_put_bulk_duplicate_prevention(self):
        """Test bulk update with duplicates - should return 409"""
        slots = [
            {"position": "QB", "slot": "QB1", "player_id": 212},
            {"position": "QB", "slot": "QB2", "player_id": 212},  # Duplicate!
        ]
        
        response = client.put("/api/teams/NE/depthchart", json={
            "season": 2025,
            "slots": slots
        })
        
        assert response.status_code == 409
        data = response.json()
        assert "cannot be assigned to both QB1 and QB2" in data["detail"]

    def test_auto_fill_empty_slots_only(self):
        """Test that auto-fill only fills empty slots"""
        # Manually set QB1
        client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": 212
        })
        
        # Auto-fill should leave QB1 alone and fill QB2
        response = client.post("/api/teams/NE/depthchart/auto_fill", json={
            "season": 2025
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        chart = data["depth_chart"]
        
        qb1 = next((s for s in chart["slots"] if s["slot"] == "QB1"), None)
        qb2 = next((s for s in chart["slots"] if s["slot"] == "QB2"), None)
        
        # QB1 should remain unchanged
        assert qb1["player_id"] == 212
        assert qb1["name"] == "J. Kingsley"
        
        # QB2 should be auto-filled
        assert qb2["player_id"] == 213  # M. Sanders (second best QB)
        assert qb2["name"] == "M. Sanders"

    def test_auto_fill_all_empty_slots(self):
        """Test auto-fill when all slots are empty"""
        response = client.post("/api/teams/NE/depthchart/auto_fill", json={
            "season": 2025
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        chart = data["depth_chart"]
        
        # Check that QB positions are filled with best available
        qb1 = next((s for s in chart["slots"] if s["slot"] == "QB1"), None)
        qb2 = next((s for s in chart["slots"] if s["slot"] == "QB2"), None)
        
        assert qb1["player_id"] == 212  # J. Kingsley (84 OVR)
        assert qb1["name"] == "J. Kingsley"
        assert qb2["player_id"] == 213  # M. Sanders (71 OVR)
        assert qb2["name"] == "M. Sanders"

    def test_auto_fill_preserves_manual_selections(self):
        """Test that auto-fill preserves all manual selections"""
        # Set multiple manual selections
        client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": 212
        })
        
        client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "RB",
            "slot": "RB1",
            "player_id": 332
        })
        
        # Auto-fill
        response = client.post("/api/teams/NE/depthchart/auto_fill", json={
            "season": 2025
        })
        
        assert response.status_code == 200
        data = response.json()
        
        chart = data["depth_chart"]
        
        # Manual selections should be preserved
        qb1 = next((s for s in chart["slots"] if s["slot"] == "QB1"), None)
        rb1 = next((s for s in chart["slots"] if s["slot"] == "RB1"), None)
        
        assert qb1["player_id"] == 212  # Preserved
        assert rb1["player_id"] == 332  # Preserved
        
        # Empty slots should be filled
        qb2 = next((s for s in chart["slots"] if s["slot"] == "QB2"), None)
        rb2 = next((s for s in chart["slots"] if s["slot"] == "RB2"), None)
        
        assert qb2["player_id"] == 213  # Auto-filled
        assert rb2["player_id"] == 411  # Auto-filled

    def test_get_roster(self):
        """Test getting team roster for dropdowns"""
        response = client.get("/api/teams/NE/roster?season=2025")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["team_id"] == "NE"
        assert data["season"] == 2025
        assert "players" in data
        assert len(data["players"]) > 0
        
        # Check player structure
        player = data["players"][0]
        assert "id" in player
        assert "name" in player
        assert "position" in player
        assert "overall_rating" in player

    def test_position_requirements(self):
        """Test getting position requirements"""
        response = client.get("/api/teams/NE/depthchart/positions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["team_id"] == "NE"
        assert "position_requirements" in data
        
        requirements = data["position_requirements"]
        assert requirements["QB"] == 2
        assert requirements["RB"] == 2
        assert requirements["WR"] == 3

    def test_persistence_across_requests(self):
        """Test that changes persist across different API requests"""
        # Set QB1 via PATCH
        client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": 212
        })
        
        # Get depth chart - should see the assignment
        response = client.get("/api/teams/NE/depthchart?season=2025")
        
        assert response.status_code == 200
        data = response.json()
        
        qb1_slot = next((s for s in data["slots"] if s["slot"] == "QB1"), None)
        assert qb1_slot is not None
        assert qb1_slot["player_id"] == 212

    def test_different_teams_seasons(self):
        """Test that different teams and seasons are isolated"""
        # Set QB1 for NE 2025
        client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": 212
        })
        
        # Set QB1 for BUF 2025 (should work - different team)
        client.patch("/api/teams/BUF/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": 212
        })
        
        # Set QB1 for NE 2024 (should work - different season)
        client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2024,
            "position": "QB",
            "slot": "QB1",
            "player_id": 212
        })
        
        # All should be independent
        ne_2025 = client.get("/api/teams/NE/depthchart?season=2025").json()
        buf_2025 = client.get("/api/teams/BUF/depthchart?season=2025").json()
        ne_2024 = client.get("/api/teams/NE/depthchart?season=2024").json()
        
        qb1_ne_2025 = next((s for s in ne_2025["slots"] if s["slot"] == "QB1"), None)
        qb1_buf_2025 = next((s for s in buf_2025["slots"] if s["slot"] == "QB1"), None)
        qb1_ne_2024 = next((s for s in ne_2024["slots"] if s["slot"] == "QB1"), None)
        
        assert qb1_ne_2025["player_id"] == 212
        assert qb1_buf_2025["player_id"] == 212
        assert qb1_ne_2024["player_id"] == 212

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "depth_chart"
        assert "timestamp" in data

    def test_invalid_team_id(self):
        """Test with invalid team ID"""
        response = client.get("/api/teams/INVALID/depthchart?season=2025")
        
        # Should still work, just return empty slots
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == "INVALID"

    def test_missing_season_parameter(self):
        """Test that missing season defaults to current year"""
        response = client.get("/api/teams/NE/depthchart")
        
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == "NE"
        # Season should default to current year (2025 in tests)

    def test_auto_fill_after_manual_clearing(self):
        """Test auto-fill after manually clearing slots"""
        # Auto-fill first time
        response1 = client.post("/api/teams/NE/depthchart/auto_fill", json={
            "season": 2025
        })
        assert response1.status_code == 200
        
        # Clear QB1
        client.patch("/api/teams/NE/depthchart/slot", json={
            "season": 2025,
            "position": "QB",
            "slot": "QB1",
            "player_id": None
        })
        
        # Auto-fill again - should fill QB1
        response2 = client.post("/api/teams/NE/depthchart/auto_fill", json={
            "season": 2025
        })
        
        assert response2.status_code == 200
        data = response2.json()
        
        chart = data["depth_chart"]
        qb1_after = next((s for s in chart["slots"] if s["slot"] == "QB1"), None)
        assert qb1_after["player_id"] is not None