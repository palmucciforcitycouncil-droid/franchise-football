#!/usr/bin/env python3
"""
Test Runner for Season Stats Test Harness.
Runs the mini season simulation and validates invariants.
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_mini_season_runner():
    """Test the mini season runner."""
    try:
        print("Testing mini season runner...")
        
        from app.testing.mini_season_runner import memory_db, run_mini_season
        
        with memory_db() as session:
            result = run_mini_season(session, weeks=2)
            
            print(f"+ Generated {len(result['teams'])} teams")
            print(f"+ Created {len(result['schedule'])} games in schedule")
            print(f"+ Simulated {len(result['games'])} games")
            
            # Check that we have games
            assert len(result['games']) > 0, "No games were simulated"
            assert len(result['teams']) > 0, "No teams were created"
            
            print("+ Mini season runner test passed!")
            return True
            
    except Exception as e:
        print(f"ERROR: Mini season runner test failed: {e}")
        return False


def test_pbp_aggregation():
    """Test PBP aggregation."""
    try:
        print("\nTesting PBP aggregation...")
        
        from app.testing.mini_season_runner import memory_db, run_mini_season
        from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
        
        with memory_db() as session:
            # Run mini season
            run_mini_season(session, weeks=1)
            
            # Aggregate stats
            agg = aggregate_truth_from_pbp(session)
            
            print(f"+ Aggregated {len(agg['team_game'])} team-game combinations")
            print(f"+ Aggregated {len(agg['team_season'])} team season totals")
            print(f"+ Aggregated {len(agg['player_game'])} player-game combinations")
            print(f"+ Aggregated {len(agg['player_season'])} player season totals")
            
            # Check that we have data
            assert len(agg['team_game']) > 0, "No team game stats"
            assert len(agg['team_season']) > 0, "No team season stats"
            
            print("+ PBP aggregation test passed!")
            return True
            
    except Exception as e:
        print(f"ERROR: PBP aggregation test failed: {e}")
        return False


def test_invariants():
    """Test basic invariants."""
    try:
        print("\nTesting invariants...")
        
        from app.testing.mini_season_runner import memory_db, run_mini_season
        from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
        
        with memory_db() as session:
            # Run mini season
            run_mini_season(session, weeks=2)
            
            # Aggregate stats
            agg = aggregate_truth_from_pbp(session)
            
            # Test points conservation
            total_pf = sum(row.get("points", 0) for row in agg["team_game"].values())
            total_pa = sum(row.get("points_allowed", 0) for row in agg["team_game"].values())
            
            print(f"+ Total points for: {total_pf}")
            print(f"+ Total points against: {total_pa}")
            
            assert total_pf == total_pa, f"Points for {total_pf} != points against {total_pa}"
            
            # Test yardage consistency
            total_yards = sum(row.get("yards_total", 0) for row in agg["team_game"].values())
            print(f"+ Total yards: {total_yards}")
            
            assert total_yards > 0, f"No yards generated: {total_yards}"
            
            # Test sack balance
            total_sacks_taken = sum(row.get("sacks_taken", 0) for row in agg["team_game"].values())
            total_sacks_made = sum(row.get("sacks_def", 0) for row in agg["team_game"].values())
            
            print(f"+ Total sacks taken: {total_sacks_taken}")
            print(f"+ Total sacks made: {total_sacks_made}")
            
            assert abs(total_sacks_taken - total_sacks_made) <= 1.0, f"Sacks taken {total_sacks_taken} != sacks made {total_sacks_made}"
            
            print("+ Invariants test passed!")
            return True
            
    except Exception as e:
        print(f"ERROR: Invariants test failed: {e}")
        return False


def test_advanced_stats():
    """Test advanced stats fields."""
    try:
        print("\nTesting advanced stats fields...")
        
        from app.testing.mini_season_runner import memory_db, run_mini_season
        from sqlmodel import select
        from app.models.pbp_event import PBPEvent
        
        with memory_db() as session:
            # Run mini season
            run_mini_season(session, weeks=1)
            
            # Check PBP events
            events = session.exec(select(PBPEvent)).all()
            print(f"+ Generated {len(events)} PBP events")
            
            assert len(events) > 0, "No PBP events generated"
            
            # Check for advanced fields
            has_sack_split = False
            has_coverage = False
            has_situational = False
            has_special_teams = False
            
            for event in events:
                if event.sack_split:
                    has_sack_split = True
                    total_share = sum(share for _, share in event.sack_split)
                    assert abs(total_share - 1.0) <= 0.01, f"Sack split doesn't sum to 1.0: {total_share}"
                
                if event.targeted_db_id or event.pass_breakup_by_id:
                    has_coverage = True
                
                if event.is_third_down or event.is_red_zone or event.is_goal_to_go:
                    has_situational = True
                
                if event.play_type in ["punt", "fg"] and (event.net_yards is not None or event.in_20):
                    has_special_teams = True
            
            print(f"+ Sack splits present: {has_sack_split}")
            print(f"+ Coverage stats present: {has_coverage}")
            print(f"+ Situational splits present: {has_situational}")
            print(f"+ Special teams stats present: {has_special_teams}")
            
            # At least some advanced fields should be present
            assert has_sack_split or has_coverage or has_situational or has_special_teams, "No advanced stats fields found"
            
            print("+ Advanced stats test passed!")
            return True
            
    except Exception as e:
        print(f"ERROR: Advanced stats test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Season Stats Test Harness")
    print("=" * 50)
    
    tests = [
        test_mini_season_runner,
        test_pbp_aggregation,
        test_invariants,
        test_advanced_stats
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All tests passed! Season stats test harness is working.")
        return 0
    else:
        print("FAILED: Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
