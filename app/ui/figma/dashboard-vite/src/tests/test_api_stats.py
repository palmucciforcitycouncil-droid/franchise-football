"""
Unit tests for Advanced Stats API and services.
Tests API endpoints, rollup logic, and validation.
"""

import pytest
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from app.ui.api_stats import router
from app.services.stats.rollup import rollup_game_stats
from app.services.stats.validators import validate_game_totals, validate_sack_shares
from app.services.stats.read import get_game_box
from app.models.pbp_event import PBPEvent
from app.models.stats_models import PlayerGameStats, TeamGameStats


@pytest.fixture
def test_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_pbp_events():
    """Load sample PBP events from fixture."""
    with open("tests/fixtures/pbp_sample_advanced.json", "r") as f:
        return json.load(f)


@pytest.fixture
def expected_rollup():
    """Load expected rollup snapshot."""
    with open("tests/fixtures/expected_rollup_snapshot.json", "r") as f:
        return json.load(f)


class TestStatsRollup:
    """Test stats rollup functionality."""
    
    def test_rollup_game_stats_basic(self, test_session, sample_pbp_events):
        """Test basic game stats rollup."""
        # Insert sample PBP events
        for event_data in sample_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        result = rollup_game_stats(1001, test_session)
        
        assert result["game_id"] == 1001
        assert result["events_processed"] == len(sample_pbp_events)
        assert result["player_stats_created"] > 0
        assert result["team_stats_created"] > 0
    
    def test_sack_attribution(self, test_session, sample_pbp_events):
        """Test sack attribution with shared sacks."""
        # Insert events
        for event_data in sample_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        rollup_game_stats(1001, test_session)
        
        # Check sack attribution
        sack_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.sacks > 0
            )
        ).all()
        
        # Should have 2 players with 0.5 sacks each
        assert len(sack_stats) == 2
        total_sacks = sum(ps.sacks for ps in sack_stats)
        assert abs(total_sacks - 1.0) < 0.01
    
    def test_coverage_stats(self, test_session, sample_pbp_events):
        """Test coverage stats consistency."""
        # Insert events
        for event_data in sample_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        rollup_game_stats(1001, test_session)
        
        # Check interception stats
        int_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.interceptions_caught > 0
            )
        ).all()
        
        assert len(int_stats) == 1
        assert int_stats[0].interceptions_caught == 1
    
    def test_special_teams_stats(self, test_session, sample_pbp_events):
        """Test special teams stats."""
        # Insert events
        for event_data in sample_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        rollup_game_stats(1001, test_session)
        
        # Check punt stats
        punt_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.punts > 0
            )
        ).all()
        
        assert len(punt_stats) == 1
        assert punt_stats[0].punts == 1
        assert punt_stats[0].punts_in_20 == 1
        assert punt_stats[0].punt_net_yards == 35
        
        # Check FG stats
        fg_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.field_goals_made > 0
            )
        ).all()
        
        assert len(fg_stats) == 1
        assert fg_stats[0].field_goals_made == 1
        assert fg_stats[0].field_goals_attempted == 1


class TestStatsValidation:
    """Test stats validation functionality."""
    
    def test_validate_sack_shares(self, test_session, sample_pbp_events):
        """Test sack share validation."""
        # Insert events
        for event_data in sample_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Validate sack shares
        messages = validate_sack_shares(1001, test_session)
        
        # Should have no errors for valid sack shares
        errors = [m for m in messages if m.level == "error"]
        assert len(errors) == 0
    
    def test_validate_coverage_consistency(self, test_session, sample_pbp_events):
        """Test coverage consistency validation."""
        # Insert events
        for event_data in sample_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Validate coverage
        from app.services.stats.validators import validate_coverage_consistency
        messages = validate_coverage_consistency(1001, test_session)
        
        # Should have no errors for consistent coverage
        errors = [m for m in messages if m.level == "error"]
        assert len(errors) == 0
    
    def test_validate_special_teams_consistency(self, test_session, sample_pbp_events):
        """Test special teams consistency validation."""
        # Insert events
        for event_data in sample_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Validate special teams
        from app.services.stats.validators import validate_special_teams_consistency
        messages = validate_special_teams_consistency(1001, test_session)
        
        # Should have no errors for consistent ST stats
        errors = [m for m in messages if m.level == "error"]
        assert len(errors) == 0


class TestStatsAPI:
    """Test stats API endpoints."""
    
    def test_get_game_box_endpoint(self):
        """Test game box endpoint."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        
        client = TestClient(app)
        
        # Mock the get_game_box function
        with patch('app.ui.api_stats.get_game_box') as mock_get_box:
            mock_box = Mock()
            mock_box.dict.return_value = {
                "game_id": 1001,
                "home_team_name": "Team A",
                "away_team_name": "Team B",
                "final_score_home": 21,
                "final_score_away": 14
            }
            mock_get_box.return_value = mock_box
            
            response = client.get("/api/stats/games/1001")
            assert response.status_code == 200
            data = response.json()
            assert data["game_id"] == 1001
    
    def test_get_leaders_endpoint(self):
        """Test leaders endpoint."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        
        client = TestClient(app)
        
        # Mock the get_leaders function
        with patch('app.ui.api_stats.get_leaders') as mock_get_leaders:
            mock_leaders = Mock()
            mock_leaders.dict.return_value = {
                "stat": "passing_yards",
                "leaders": [
                    {"player_name": "QB1", "value": 300}
                ]
            }
            mock_get_leaders.return_value = mock_leaders
            
            response = client.get("/api/stats/leaders?stat=passing_yards&top=10")
            assert response.status_code == 200
            data = response.json()
            assert data["stat"] == "passing_yards"
    
    def test_get_player_season_endpoint(self):
        """Test player season endpoint."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        
        client = TestClient(app)
        
        # Mock the get_player_season_lines function
        with patch('app.ui.api_stats.get_player_season_lines') as mock_get_lines:
            mock_lines = [Mock()]
            mock_lines[0].dict.return_value = {
                "player_id": 101,
                "player_name": "QB1",
                "season": 2025,
                "pass_yards": 3000
            }
            mock_get_lines.return_value = mock_lines
            
            response = client.get("/api/stats/players/season?year=2025")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["season"] == 2025
    
    def test_get_team_season_endpoint(self):
        """Test team season endpoint."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        
        client = TestClient(app)
        
        # Mock the get_team_season_lines function
        with patch('app.ui.api_stats.get_team_season_lines') as mock_get_lines:
            mock_lines = [Mock()]
            mock_lines[0].dict.return_value = {
                "team_id": 1,
                "team_name": "Team A",
                "season": 2025,
                "wins": 10,
                "losses": 6
            }
            mock_get_lines.return_value = mock_lines
            
            response = client.get("/api/stats/teams/season?year=2025")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["season"] == 2025
    
    def test_rollup_endpoint(self):
        """Test rollup endpoint."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        
        client = TestClient(app)
        
        # Mock the rollup_game_stats function
        with patch('app.ui.api_stats.rollup_game_stats') as mock_rollup:
            mock_rollup.return_value = {
                "game_id": 1001,
                "events_processed": 8,
                "player_stats_created": 10
            }
            
            response = client.post("/api/stats/rollup/game/1001")
            assert response.status_code == 200
            data = response.json()
            assert data["result"]["game_id"] == 1001
    
    def test_validate_endpoint(self):
        """Test validate endpoint."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        
        client = TestClient(app)
        
        # Mock the validate_game_totals function
        with patch('app.ui.api_stats.validate_game_totals') as mock_validate:
            mock_validate.return_value = []
            
            response = client.get("/api/stats/validate?game_id=1001")
            assert response.status_code == 200
            data = response.json()
            assert data["total_messages"] == 0
            assert data["errors"] == 0
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        
        client = TestClient(app)
        
        response = client.get("/api/stats/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "advanced_stats_api"


class TestStatsHelpers:
    """Test helper functions."""
    
    def test_safe_divide(self):
        """Test safe division function."""
        from app.services.stats.helpers import safe_divide
        
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=1.0) == 1.0
        assert safe_divide(0, 5) == 0.0
    
    def test_completion_percentage(self):
        """Test completion percentage calculation."""
        from app.services.stats.helpers import calculate_completion_percentage
        
        assert calculate_completion_percentage(20, 30) == pytest.approx(66.67, 0.01)
        assert calculate_completion_percentage(0, 0) == 0.0
        assert calculate_completion_percentage(10, 0) == 0.0
    
    def test_passer_rating(self):
        """Test passer rating calculation."""
        from app.services.stats.helpers import calculate_passer_rating
        
        # Test perfect passer rating scenario
        rating = calculate_passer_rating(77, 77, 770, 7, 0)
        assert rating > 150.0  # Should be very high
        
        # Test zero attempts
        rating = calculate_passer_rating(0, 0, 0, 0, 0)
        assert rating == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
