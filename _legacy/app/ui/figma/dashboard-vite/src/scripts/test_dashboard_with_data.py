# scripts/test_dashboard_with_data.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session
from app.db import get_engine
from app.models.season_stats import TeamSeasonStats
from app.models.awards import AwardResult
from app.models.progression import PlayerProgression
from app.models.core_min import Player, Team
from app.services.analytics import league_summary_for, trend_summary, awards_recap, progression_risers_fallers
import json

def main():
    print("=== DASHBOARD ANALYTICS WITH DATA TEST ===")
    
    engine = get_engine()
    
    # Create test data
    print("\n1. Creating test data...")
    with Session(engine) as session:
        # Create teams
        team1 = Team(abbrev="KC", name="Kansas City Chiefs")
        team2 = Team(abbrev="BUF", name="Buffalo Bills")
        session.add(team1)
        session.add(team2)
        session.commit()
        
        # Create players
        player1 = Player(
            first_name="Patrick",
            last_name="Mahomes",
            pos="QB",
            name="Patrick Mahomes",
            team_id=team1.id,
            age=28,
            years_pro=6
        )
        player2 = Player(
            first_name="Josh",
            last_name="Allen",
            pos="QB", 
            name="Josh Allen",
            team_id=team2.id,
            age=27,
            years_pro=5
        )
        session.add(player1)
        session.add(player2)
        session.commit()
        
        # Create season stats
        stats1 = TeamSeasonStats(
            team_id=team1.id,
            season=2025,
            games=17,
            points_for=425,
            points_against=350,
            plays_offense=1050,
            pass_attempts=600,
            rush_attempts=450,
            pass_yards=4200,
            rush_yards=1800,
            wins=12,
            losses=5
        )
        stats2 = TeamSeasonStats(
            team_id=team2.id,
            season=2025,
            games=17,
            points_for=400,
            points_against=375,
            plays_offense=1020,
            pass_attempts=580,
            rush_attempts=440,
            pass_yards=4100,
            rush_yards=1750,
            wins=11,
            losses=6
        )
        session.add(stats1)
        session.add(stats2)
        session.commit()
        
        # Create awards
        award1 = AwardResult(
            season=2025,
            award="MVP",
            rank=1,
            player_id=player1.id,
            player_name="Patrick Mahomes",
            team_abbr="KC",
            position="QB",
            score=95.5
        )
        award2 = AwardResult(
            season=2025,
            award="OPOY",
            rank=1,
            player_id=player1.id,
            player_name="Patrick Mahomes",
            team_abbr="KC",
            position="QB",
            score=92.3
        )
        session.add(award1)
        session.add(award2)
        session.commit()
        
        # Create progression data
        prog1 = PlayerProgression(
            player_id=player1.id,
            season=2025,
            before_json=json.dumps({"awareness": 85, "throw_accuracy": 90, "throw_power": 95, "catching": 50, "tackling": 50, "speed": 80, "agility": 85, "strength": 75, "stamina": 80, "morale": 85}),
            after_json=json.dumps({"awareness": 87, "throw_accuracy": 92, "throw_power": 96, "catching": 50, "tackling": 50, "speed": 81, "agility": 86, "strength": 76, "stamina": 82, "morale": 87}),
            components_json=json.dumps({"age": 2, "potential": 3, "usage": 1, "awards": 2}),
            notes="Strong season performance"
        )
        prog2 = PlayerProgression(
            player_id=player2.id,
            season=2025,
            before_json=json.dumps({"awareness": 82, "throw_accuracy": 85, "throw_power": 90, "catching": 50, "tackling": 50, "speed": 85, "agility": 80, "strength": 80, "stamina": 75, "morale": 80}),
            after_json=json.dumps({"awareness": 83, "throw_accuracy": 86, "throw_power": 91, "catching": 50, "tackling": 50, "speed": 85, "agility": 80, "strength": 80, "stamina": 76, "morale": 81}),
            components_json=json.dumps({"age": 1, "potential": 2, "usage": 0, "awards": 0}),
            notes="Solid development"
        )
        session.add(prog1)
        session.add(prog2)
        session.commit()
        
        print("   Created teams, players, season stats, awards, and progression data")
    
    # Test analytics functions
    print("\n2. Testing analytics functions...")
    with Session(engine) as session:
        # Test league summary
        summary = league_summary_for(session, 2025)
        print(f"   League Summary: {summary}")
        
        # Test trend summary
        trends = trend_summary(session, 2025, 2025)
        print(f"   Trends: {trends}")
        
        # Test awards recap
        awards = awards_recap(session, 2025)
        print(f"   Awards: {awards}")
        
        # Test progression risers/fallers
        prog = progression_risers_fallers(session, 2025, top_n=2)
        print(f"   Progression: {prog}")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()
