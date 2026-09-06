#!/usr/bin/env python3
"""
Test script to simulate three seasons and analyze statistics.
This bypasses the server issues and directly tests the simulation logic.
"""

import os
import sys
import random
import statistics
from typing import Dict, List, Any

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set environment variables
os.environ['USE_PBP_V2'] = 'true'
os.environ['HFA_POINTS'] = '1.6'
os.environ['LEAGUE_SEED'] = '2025'

def test_yardage_targets():
    """Test the yardage targeting system"""
    from app.routers.sim import _yardage_targets_v2
    
    # Test multiple seasons
    seasons_data = []
    
    for season in range(2025, 2028):
        print(f"\n=== Testing Season {season} ===")
        
        # Generate yardage targets for all teams
        team_yardage = {}
        for team_id in range(1, 33):  # 32 teams
            h_total, h_pass, a_total, a_pass = _yardage_targets_v2(season, team_id, team_id + 1)
            team_yardage[team_id] = {
                'home_total': h_total,
                'home_pass': h_pass,
                'away_total': a_total,
                'away_pass': a_pass
            }
        
        # Calculate averages
        home_totals = [data['home_total'] for data in team_yardage.values()]
        home_passes = [data['home_pass'] for data in team_yardage.values()]
        away_totals = [data['away_total'] for data in team_yardage.values()]
        away_passes = [data['away_pass'] for data in team_yardage.values()]
        
        season_stats = {
            'season': season,
            'home_total_avg': statistics.mean(home_totals),
            'home_total_range': (min(home_totals), max(home_totals)),
            'home_pass_avg': statistics.mean(home_passes),
            'home_pass_range': (min(home_passes), max(home_passes)),
            'away_total_avg': statistics.mean(away_totals),
            'away_total_range': (min(away_totals), max(away_totals)),
            'away_pass_avg': statistics.mean(away_passes),
            'away_pass_range': (min(away_passes), max(away_passes)),
        }
        
        seasons_data.append(season_stats)
        
        print(f"Home Total Yards: {season_stats['home_total_avg']:.1f} (range: {season_stats['home_total_range'][0]}-{season_stats['home_total_range'][1]})")
        print(f"Home Pass Yards: {season_stats['home_pass_avg']:.1f} (range: {season_stats['home_pass_range'][0]}-{season_stats['home_pass_range'][1]})")
        print(f"Away Total Yards: {season_stats['away_total_avg']:.1f} (range: {season_stats['away_total_range'][0]}-{season_stats['away_total_range'][1]})")
        print(f"Away Pass Yards: {season_stats['away_pass_avg']:.1f} (range: {season_stats['away_pass_range'][0]}-{season_stats['away_pass_range'][1]})")
    
    # Calculate overall averages across all seasons
    print(f"\n=== THREE-SEASON SUMMARY ===")
    
    all_home_totals = []
    all_home_passes = []
    all_away_totals = []
    all_away_passes = []
    
    for season_data in seasons_data:
        all_home_totals.extend([season_data['home_total_avg']])
        all_home_passes.extend([season_data['home_pass_avg']])
        all_away_totals.extend([season_data['away_total_avg']])
        all_away_passes.extend([season_data['away_pass_avg']])
    
    print(f"AVERAGE HOME TOTAL YARDS: {statistics.mean(all_home_totals):.1f}")
    print(f"AVERAGE HOME PASS YARDS: {statistics.mean(all_home_passes):.1f}")
    print(f"AVERAGE AWAY TOTAL YARDS: {statistics.mean(all_away_totals):.1f}")
    print(f"AVERAGE AWAY PASS YARDS: {statistics.mean(all_away_passes):.1f}")
    
    # Calculate ranges
    home_total_min = min(season['home_total_range'][0] for season in seasons_data)
    home_total_max = max(season['home_total_range'][1] for season in seasons_data)
    home_pass_min = min(season['home_pass_range'][0] for season in seasons_data)
    home_pass_max = max(season['home_pass_range'][1] for season in seasons_data)
    away_total_min = min(season['away_total_range'][0] for season in seasons_data)
    away_total_max = max(season['away_total_range'][1] for season in seasons_data)
    away_pass_min = min(season['away_pass_range'][0] for season in seasons_data)
    away_pass_max = max(season['away_pass_range'][1] for season in seasons_data)
    
    print(f"\nRANGES ACROSS ALL SEASONS:")
    print(f"Home Total Yards: {home_total_min}-{home_total_max}")
    print(f"Home Pass Yards: {home_pass_min}-{home_pass_max}")
    print(f"Away Total Yards: {away_total_min}-{away_total_max}")
    print(f"Away Pass Yards: {away_pass_min}-{away_pass_max}")

def test_scoring_system():
    """Test the scoring system"""
    from app.routers.sim import _points_from_yards_v2
    
    print(f"\n=== TESTING SCORING SYSTEM ===")
    
    # Test with different team combinations
    test_cases = [
        ("KC", "BUF"),  # High-rated teams
        ("NE", "NYJ"),  # Lower-rated teams
        ("KC", "NE"),   # Mixed ratings
    ]
    
    for home_team, away_team in test_cases:
        home_score, away_score = _points_from_yards_v2(home_team, away_team)
        margin = home_score - away_score
        
        print(f"{home_team} vs {away_team}: {home_score}-{away_score} (margin: {margin:+.1f})")

if __name__ == "__main__":
    try:
        test_yardage_targets()
        test_scoring_system()
        print(f"\n=== TEST COMPLETED SUCCESSFULLY ===")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
