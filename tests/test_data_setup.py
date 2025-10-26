"""
Test Data Setup for Trade Engine Testing
Creates teams, players, and draft picks for testing
"""

from sqlmodel import Session
from app.models.database import get_engine
from app.models.team import Team
from app.models.player import Player
from app.models.draft import DraftPickInventory

def create_test_data():
    """Create test data for Trade Engine"""
    engine = get_engine()
    
    with Session(engine) as session:
        # Create test teams
        team1 = Team(id=1, location_name="New York", nickname="Jets", abbr="NYJ", conference="AFC", division="East")
        team2 = Team(id=2, location_name="Miami", nickname="Dolphins", abbr="MIA", conference="AFC", division="East")
        team3 = Team(id=3, location_name="Buffalo", nickname="Bills", abbr="BUF", conference="AFC", division="East")
        
        session.add(team1)
        session.add(team2)
        session.add(team3)
        
        # Create test players for Team 1
        player1 = Player(id=1, first_name="Aaron", last_name="Rodgers", position="QB", overall=95, age=40, team_id=1, season=2025)
        player2 = Player(id=2, first_name="Sauce", last_name="Gardner", position="CB", overall=93, age=24, team_id=1, season=2025)
        player3 = Player(id=3, first_name="Quinnen", last_name="Williams", position="DT", overall=92, age=26, team_id=1, season=2025)
        
        session.add(player1)
        session.add(player2)
        session.add(player3)
        
        # Create test players for Team 2
        player4 = Player(id=4, first_name="Tua", last_name="Tagovailoa", position="QB", overall=88, age=25, team_id=2, season=2025)
        player5 = Player(id=5, first_name="Tyreek", last_name="Hill", position="WR", overall=97, age=30, team_id=2, season=2025)
        player6 = Player(id=6, first_name="Jaylen", last_name="Waddle", position="WR", overall=87, age=25, team_id=2, season=2025)
        
        session.add(player4)
        session.add(player5)
        session.add(player6)
        
        # Create test players for Team 3
        player7 = Player(id=7, first_name="Josh", last_name="Allen", position="QB", overall=96, age=28, team_id=3, season=2025)
        player8 = Player(id=8, first_name="Stefon", last_name="Diggs", position="WR", overall=94, age=31, team_id=3, season=2025)
        player9 = Player(id=9, first_name="Von", last_name="Miller", position="OLB", overall=89, age=35, team_id=3, season=2025)
        
        session.add(player7)
        session.add(player8)
        session.add(player9)
        
        # Create test draft picks for Team 1
        pick1 = DraftPickInventory(id=1, season=2025, round=1, slot=1, owning_team_id=1, original_team_id=1)
        pick2 = DraftPickInventory(id=2, season=2025, round=2, slot=33, owning_team_id=1, original_team_id=1)
        pick3 = DraftPickInventory(id=3, season=2025, round=3, slot=65, owning_team_id=1, original_team_id=1)
        
        session.add(pick1)
        session.add(pick2)
        session.add(pick3)
        
        # Create test draft picks for Team 2
        pick4 = DraftPickInventory(id=4, season=2025, round=1, slot=21, owning_team_id=2, original_team_id=2)
        pick5 = DraftPickInventory(id=5, season=2025, round=2, slot=53, owning_team_id=2, original_team_id=2)
        pick6 = DraftPickInventory(id=6, season=2025, round=3, slot=85, owning_team_id=2, original_team_id=2)
        
        session.add(pick4)
        session.add(pick5)
        session.add(pick6)
        
        # Create test draft picks for Team 3
        pick7 = DraftPickInventory(id=7, season=2025, round=1, slot=28, owning_team_id=3, original_team_id=3)
        pick8 = DraftPickInventory(id=8, season=2025, round=2, slot=60, owning_team_id=3, original_team_id=3)
        pick9 = DraftPickInventory(id=9, season=2025, round=3, slot=92, owning_team_id=3, original_team_id=3)
        
        session.add(pick7)
        session.add(pick8)
        session.add(pick9)
        
        session.commit()
        print("Success! Test data created successfully!")
        print("  - 3 teams (NYJ, MIA, BUF)")
        print("  - 9 players (3 per team)")
        print("  - 9 draft picks (3 per team)")

if __name__ == "__main__":
    create_test_data()
