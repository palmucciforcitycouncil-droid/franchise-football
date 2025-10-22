"""
Test Playoffs API and Page
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_playoffs_page():
    """Test that the playoffs page loads successfully"""
    response = client.get("/playoffs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Playoffs — 2025" in response.text
    assert "14-team bracket" in response.text

def test_playoffs_api():
    """Test the playoffs API endpoint"""
    response = client.get("/api/playoffs")
    assert response.status_code == 200
    
    data = response.json()
    assert "season_year" in data
    assert "bracket" in data
    assert "in_the_hunt" in data
    assert data["season_year"] == 2025
    
    # Check bracket structure
    assert "AFC" in data["bracket"]
    assert "NFC" in data["bracket"]
    assert "SB" in data["bracket"]
    
    # Check in the hunt structure
    assert "AFC" in data["in_the_hunt"]
    assert "NFC" in data["in_the_hunt"]

def test_playoffs_api_with_season():
    """Test playoffs API with specific season"""
    response = client.get("/api/playoffs?season=2024")
    assert response.status_code == 200
    
    data = response.json()
    assert data["season_year"] == 2024

def test_matchup_details():
    """Test getting specific matchup details"""
    response = client.get("/api/playoffs/matchup/1001")
    assert response.status_code == 200
    
    data = response.json()
    assert "game_id" in data
    assert data["game_id"] == 1001

def test_matchup_not_found():
    """Test matchup not found"""
    response = client.get("/api/playoffs/matchup/9999")
    assert response.status_code == 200  # Returns error object, not 404
    
    data = response.json()
    assert "error" in data

def test_playoffs_page_content():
    """Test that playoffs page contains expected content"""
    response = client.get("/playoffs")
    html_content = response.text
    
    # Check for key elements
    assert "Boston Patriots" in html_content
    assert "San Francisco 49ers" in html_content
    assert "Wild Card" in html_content
    assert "Divisional" in html_content
    assert "Conference" in html_content
    assert "Super Bowl" in html_content
    assert "AFC In the Hunt" in html_content
    assert "NFC In the Hunt" in html_content
