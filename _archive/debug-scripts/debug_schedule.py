from app.core.db import session_scope
from app.models.sim_models import Team
from sqlmodel import select

# Import the scheduling functions
import sys
sys.path.append('.')
from app.routers.sim import _round_robin_round, _place_rounds_into_18_weeks, _assign_byes

with session_scope() as s:
    teams = s.exec(select(Team).order_by(Team.id)).all()
    team_ids = [t.id for t in teams]
    
    print(f"Total teams: {len(team_ids)}")
    
    # Generate 17 rounds
    rounds = [_round_robin_round(team_ids, r) for r in range(17)]
    print(f"Generated {len(rounds)} rounds")
    
    # Count total games in rounds
    total_games_in_rounds = sum(len(round) for round in rounds)
    print(f"Total games in rounds: {total_games_in_rounds}")
    
    # Place rounds into weeks
    weeks_plan = _place_rounds_into_18_weeks(team_ids, 2025, rounds)
    
    # Count games per week
    total_games_placed = 0
    for wk in range(1, 19):
        games_in_week = len(weeks_plan[wk])
        total_games_placed += games_in_week
        print(f"Week {wk}: {games_in_week} games")
    
    print(f"Total games placed: {total_games_placed}")
    print(f"Expected: 272 games")
    print(f"Missing: {272 - total_games_placed} games")
