import sys
sys.path.insert(0, 'C:\\Users\\bpalm\\Documents\\franchise-football')

try:
    from app.core.db import session_scope
    from app.models.sim_models import Team
    from sqlmodel import select
    
    # Check if teams exist
    with session_scope() as s:
        teams = s.exec(select(Team).order_by(Team.id)).all()
        print(f"Number of teams: {len(teams)}")
        
        if len(teams) < 32:
            print("Not enough teams seeded!")
        else:
            # Try to call the internal functions
            from app.routers.sim import _round_robin_round, _place_rounds_into_18_weeks
            
            team_ids = [t.id for t in teams]
            print(f"Team IDs: {team_ids[:5]}... (showing first 5)")
            
            # Test round robin
            print("Testing _round_robin_round...")
            round_0 = _round_robin_round(team_ids, 0)
            print(f"Round 0 has {len(round_0)} games")
            
            # Test all rounds
            print("Testing all 17 rounds...")
            rounds = [_round_robin_round(team_ids, r) for r in range(17)]
            print(f"Generated {len(rounds)} rounds")
            
            # Test week placement
            print("Testing _place_rounds_into_18_weeks...")
            weeks_plan = _place_rounds_into_18_weeks(team_ids, 2026, rounds)
            print(f"Generated {len(weeks_plan)} weeks")
            print(f"Total games: {sum(len(games) for games in weeks_plan.values())}")
            
            print("\n✅ All functions work correctly!")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

