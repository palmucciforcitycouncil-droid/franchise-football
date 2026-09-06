#!/usr/bin/env python3
"""
Stratified Random Sample of NFL Game Logs
Display exactly 2 random games from each of the 3 simulated seasons (2024, 2025, 2026)
"""

import pandas as pd
import numpy as np
import random

def create_mock_team_game_log():
    """Create a mock DataFrame that closely matches the structure of DataFrame 4 from the NFL simulation"""
    
    # Set random seed for reproducible data
    np.random.seed(42)
    random.seed(42)
    
    # NFL team names
    teams = [
        "Bills", "Dolphins", "Patriots", "Jets", "Ravens", "Bengals", "Browns", "Steelers",
        "Texans", "Colts", "Jaguars", "Titans", "Broncos", "Chiefs", "Raiders", "Chargers",
        "Cowboys", "Giants", "Eagles", "Commanders", "Bears", "Lions", "Packers", "Vikings",
        "Falcons", "Panthers", "Saints", "Buccaneers", "Cardinals", "Rams", "49ers", "Seahawks"
    ]
    
    # Create mock data
    data = []
    game_id = 1
    
    # Generate balanced data across 3 seasons
    for season in [2024, 2025, 2026]:
        # Each season gets ~40 games (balanced distribution)
        games_per_season = 40
        
        for _ in range(games_per_season):
            # Randomly select two different teams
            home_team, away_team = random.sample(teams, 2)
            
            # Generate realistic game statistics
            home_score = np.random.randint(7, 45)  # Realistic NFL scoring range
            away_score = np.random.randint(7, 45)
            
            # Ensure games don't end in ties (simplified)
            if home_score == away_score:
                home_score += 1
            
            # Generate yards (realistic NFL range: 200-500 yards)
            home_yards = np.random.randint(200, 501)
            away_yards = np.random.randint(200, 501)
            
            # Generate turnovers (0-4 per game, realistic NFL range)
            home_turnovers = np.random.randint(0, 5)
            away_turnovers = np.random.randint(0, 5)
            
            # Add home team game log
            data.append({
                'Season': season,
                'Game_ID': game_id,
                'Team': home_team,
                'Opponent': away_team,
                'Points_Scored_Game': home_score,
                'Points_Allowed_Game': away_score,
                'Yards_Gained_Game': home_yards,
                'Yards_Allowed_Game': away_yards,
                'Turnovers_Game': home_turnovers,
                'Turnovers_Forced_Game': away_turnovers,
                'Weather': random.choice(['clear', 'rain', 'snow']),
                'Wind_MPH': round(np.random.uniform(5, 20), 1)
            })
            
            # Add away team game log
            data.append({
                'Season': season,
                'Game_ID': game_id,
                'Team': away_team,
                'Opponent': home_team,
                'Points_Scored_Game': away_score,
                'Points_Allowed_Game': home_score,
                'Yards_Gained_Game': away_yards,
                'Yards_Allowed_Game': home_yards,
                'Turnovers_Game': away_turnovers,
                'Turnovers_Forced_Game': home_turnovers,
                'Weather': random.choice(['clear', 'rain', 'snow']),
                'Wind_MPH': round(np.random.uniform(5, 20), 1)
            })
            
            game_id += 1
    
    # Create DataFrame
    df_team_game_log = pd.DataFrame(data)
    
    return df_team_game_log


def stratified_sample_games(df_team_game_log):
    """Perform stratified random sampling: 2 games from each season"""
    
    # Set random seed for reproducible sampling
    random.seed(42)
    np.random.seed(42)
    
    # Group by season and sample 2 unique games from each season
    sampled_games = []
    
    for season in [2024, 2025, 2026]:
        # Get all games for this season
        season_games = df_team_game_log[df_team_game_log['Season'] == season]
        
        # Get unique Game_IDs for this season
        unique_game_ids = season_games['Game_ID'].unique()
        
        # Randomly sample 2 unique games
        sampled_game_ids = random.sample(list(unique_game_ids), 2)
        
        # Get all rows (both teams) for the sampled games
        for game_id in sampled_game_ids:
            game_rows = season_games[season_games['Game_ID'] == game_id]
            sampled_games.append(game_rows)
    
    # Combine all sampled games
    sampled_games_df = pd.concat(sampled_games, ignore_index=True)
    
    return sampled_games_df


def main():
    """Main function to create mock data and perform stratified sampling"""
    
    print("NFL Game Log Stratified Random Sample")
    print("=" * 50)
    
    # Step 1: Create mock DataFrame
    print("Creating mock team game log DataFrame...")
    df_team_game_log = create_mock_team_game_log()
    
    print(f"Mock DataFrame created with shape: {df_team_game_log.shape}")
    print(f"Games per season:")
    print(df_team_game_log.groupby('Season')['Game_ID'].nunique())
    print()
    
    # Step 2: Perform stratified sampling
    print("Performing stratified random sampling (2 games per season)...")
    sampled_games = stratified_sample_games(df_team_game_log)
    
    # Step 3: Display results
    print("\n" + "=" * 80)
    print("STRATIFIED RANDOM SAMPLE: 6 GAME LOGS (2 per season)")
    print("=" * 80)
    
    # Select only the essential columns for play-by-play summary
    essential_columns = ['Season', 'Game_ID', 'Team', 'Opponent', 'Points_Scored_Game', 'Yards_Gained_Game', 'Turnovers_Game']
    sampled_games_display = sampled_games[essential_columns].copy()
    
    # Sort by Season and Game_ID for better readability
    sampled_games_display = sampled_games_display.sort_values(['Season', 'Game_ID'])
    
    print(f"Sample size: {len(sampled_games_display)} rows (6 games × 2 teams each)")
    print(f"Games sampled per season:")
    print(sampled_games_display.groupby('Season')['Game_ID'].nunique())
    print()
    
    print("SAMPLED GAME LOGS:")
    print("-" * 80)
    
    # Display each game with both teams
    current_game_id = None
    for _, row in sampled_games_display.iterrows():
        if row['Game_ID'] != current_game_id:
            if current_game_id is not None:
                print()  # Add blank line between games
            print(f"GAME {row['Game_ID']} (Season {row['Season']}):")
            current_game_id = row['Game_ID']
        
        print(f"  {row['Team']} vs {row['Opponent']}: "
              f"{row['Points_Scored_Game']} points, "
              f"{row['Yards_Gained_Game']} yards, "
              f"{row['Turnovers_Game']} turnovers")
    
    print("\n" + "=" * 80)
    print("COMPLETE SAMPLED GAMES DATAFRAME:")
    print("=" * 80)
    print(sampled_games_display.to_string(index=False))
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SAMPLE SUMMARY STATISTICS:")
    print("=" * 80)
    
    print(f"Total games sampled: {sampled_games_display['Game_ID'].nunique()}")
    print(f"Games per season: {sampled_games_display.groupby('Season')['Game_ID'].nunique().to_dict()}")
    
    print(f"\nAverage points per game: {sampled_games_display['Points_Scored_Game'].mean():.1f}")
    print(f"Average yards per game: {sampled_games_display['Yards_Gained_Game'].mean():.1f}")
    print(f"Average turnovers per game: {sampled_games_display['Turnovers_Game'].mean():.1f}")
    
    print(f"\nPoints range: {sampled_games_display['Points_Scored_Game'].min()}-{sampled_games_display['Points_Scored_Game'].max()}")
    print(f"Yards range: {sampled_games_display['Yards_Gained_Game'].min()}-{sampled_games_display['Yards_Gained_Game'].max()}")
    print(f"Turnovers range: {sampled_games_display['Turnovers_Game'].min()}-{sampled_games_display['Turnovers_Game'].max()}")
    
    return sampled_games_display


if __name__ == "__main__":
    sampled_games = main()
