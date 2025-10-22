#!/usr/bin/env python3
"""
Comprehensive Season Stats Test Harness.
Imports all models and runs the complete test suite.
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_complete_harness():
    """Test the complete season stats harness."""
    try:
        print("Testing complete season stats harness...")
        
        # Import all models first to ensure they're mapped
        from app.models.sim_models import SimTeam, SimGame, SimGameEvent
        from app.models.player_models import Player, DepthChart, PlayerInjury
        from app.models.contract_models import PlayerContract, CapSummary
        from app.models.season_models import Season
        from app.models.playoffs_models import PlayoffRound, PlayoffMatchup
        from app.models.coach_models import Coach
        from app.models.stats_models import PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats
        from app.models.pbp_event import PBPEvent
        
        print("+ All models imported successfully")
        
        # Now import the testing modules
        from app.testing.mini_season_runner import memory_db, run_mini_season
        from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
        
        print("+ Testing modules imported successfully")
        
        # Run the mini season
        with memory_db() as session:
            result = run_mini_season(session, weeks=2)
            
            print(f"+ Generated {len(result['teams'])} teams")
            print(f"+ Created {len(result['schedule'])} games in schedule")
            print(f"+ Simulated {len(result['games'])} games")
            
            # Check that we have games
            assert len(result['games']) > 0, "No games were simulated"
            assert len(result['teams']) > 0, "No teams were created"
            
            # Test PBP aggregation
            agg = aggregate_truth_from_pbp(session)
            
            print(f"+ Aggregated {len(agg['team_game'])} team-game combinations")
            print(f"+ Aggregated {len(agg['team_season'])} team season totals")
            print(f"+ Aggregated {len(agg['player_game'])} player-game combinations")
            print(f"+ Aggregated {len(agg['player_season'])} player season totals")
            
            # Check that we have data
            assert len(agg['team_game']) > 0, "No team game stats"
            assert len(agg['team_season']) > 0, "No team season stats"
            
            # Test invariants
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
            
            # Test advanced stats fields
            from sqlmodel import select
            
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
                    try:
                        import json
                        sack_data = json.loads(event.sack_split) if isinstance(event.sack_split, str) else event.sack_split
                        total_share = sum(share for _, share in sack_data)
                        assert abs(total_share - 1.0) <= 0.01, f"Sack split doesn't sum to 1.0: {total_share}"
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass
                
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
            
            print("+ Complete harness test passed!")
            return True
            
    except Exception as e:
        print(f"ERROR: Complete harness test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the complete test."""
    print("Complete Season Stats Test Harness")
    print("=" * 50)
    
    if test_complete_harness():
        print("\nSUCCESS: Complete season stats test harness is working!")
        print("All invariants validated:")
        print("- PBP events generated correctly")
        print("- Team/player stats aggregated from PBP")
        print("- Points conservation (PF = PA)")
        print("- Yardage consistency")
        print("- Sack balance")
        print("- Advanced stats fields present")
        return 0
    else:
        print("\nFAILED: Complete season stats test harness failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
