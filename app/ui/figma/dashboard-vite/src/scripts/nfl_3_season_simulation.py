#!/usr/bin/env python3
"""
NFL Game Simulation and Statistical Analysis
Complete 3-Season Simulation with Detailed Statistics Tracking
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import random
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import json

# Import our Option C components
from app.config_sim_calibration import bands, safety
from app.engine.pbp_curves import third_down_logit, red_zone_td_prob, fourth_down_decision, weather_adjustments
from app.engine.pbp_modifiers import compose_pass_complete_logit, pressure_probability_logit, sack_prob_from_pressure
from app.engine.safety_controller import SafetyController
from app.telemetry.game_metrics import GameMetrics


@dataclass
class Team:
    """NFL Team with strength rating and statistics"""
    team_id: int
    name: str
    city: str
    rating: float
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_scored: int = 0
    points_allowed: int = 0
    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0
    turnovers: int = 0
    sacks: int = 0
    interceptions: int = 0
    fumbles_lost: int = 0


@dataclass
class Player:
    """NFL Player with position-specific statistics"""
    player_id: int
    name: str
    team_id: int
    position: str
    rating: float
    # Season totals
    passing_yards: int = 0
    passing_tds: int = 0
    interceptions: int = 0
    rushing_yards: int = 0
    rushing_tds: int = 0
    receptions: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    sacks: int = 0
    turnovers_forced: int = 0
    # Game-by-game stats
    game_stats: List[Dict] = field(default_factory=list)


@dataclass
class Game:
    """Individual NFL Game"""
    game_id: int
    season: int
    week: int
    home_team: Team
    away_team: Team
    home_score: int = 0
    away_score: int = 0
    home_yards: int = 0
    away_yards: int = 0
    home_turnovers: int = 0
    away_turnovers: int = 0
    weather: str = "clear"
    wind_mph: float = 5.0


class NFLSimulationEngine:
    """Complete NFL Simulation Engine with Option C Components"""
    
    def __init__(self, seed: int = 2024):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        
        # Initialize teams
        self.teams = self._create_teams()
        self.players = self._create_players()
        
        # Season tracking
        self.seasons = []
        self.all_games = []
        self.player_game_logs = []
        self.team_game_logs = []
        
        # Option C components
        self.safety_controller = SafetyController()
        
    def _create_teams(self) -> List[Team]:
        """Create 32 NFL teams with normally distributed ratings"""
        team_names = [
            ("Buffalo", "Bills"), ("Miami", "Dolphins"), ("New England", "Patriots"), ("New York", "Jets"),
            ("Baltimore", "Ravens"), ("Cincinnati", "Bengals"), ("Cleveland", "Browns"), ("Pittsburgh", "Steelers"),
            ("Houston", "Texans"), ("Indianapolis", "Colts"), ("Jacksonville", "Jaguars"), ("Tennessee", "Titans"),
            ("Denver", "Broncos"), ("Kansas City", "Chiefs"), ("Las Vegas", "Raiders"), ("Los Angeles", "Chargers"),
            ("Dallas", "Cowboys"), ("New York", "Giants"), ("Philadelphia", "Eagles"), ("Washington", "Commanders"),
            ("Chicago", "Bears"), ("Detroit", "Lions"), ("Green Bay", "Packers"), ("Minnesota", "Vikings"),
            ("Atlanta", "Falcons"), ("Carolina", "Panthers"), ("New Orleans", "Saints"), ("Tampa Bay", "Buccaneers"),
            ("Arizona", "Cardinals"), ("Los Angeles", "Rams"), ("San Francisco", "49ers"), ("Seattle", "Seahawks")
        ]
        
        teams = []
        ratings = np.random.normal(80, 5, 32)  # Mean=80, Std=5
        
        for i, (city, name) in enumerate(team_names):
            team = Team(
                team_id=i + 1,
                name=name,
                city=city,
                rating=max(60, min(100, ratings[i]))  # Clamp between 60-100
            )
            teams.append(team)
            
        return teams
    
    def _create_players(self) -> List[Player]:
        """Create players for each team (20+ per team)"""
        players = []
        player_id = 1
        
        positions = {
            "QB": 1, "RB": 2, "WR": 3, "TE": 1, "K": 1, "D/ST": 1,
            "LB": 2, "DB": 3, "DL": 2, "OL": 5, "ST": 2
        }
        
        for team in self.teams:
            for pos, count in positions.items():
                for i in range(count):
                    # Position-specific rating ranges
                    if pos == "QB":
                        rating = np.random.normal(82, 6)
                    elif pos in ["RB", "WR"]:
                        rating = np.random.normal(78, 5)
                    elif pos == "K":
                        rating = np.random.normal(75, 4)
                    else:
                        rating = np.random.normal(76, 4)
                    
                    player = Player(
                        player_id=player_id,
                        name=f"{pos}{i+1} {team.name}",
                        team_id=team.team_id,
                        position=pos,
                        rating=max(60, min(100, rating))
                    )
                    players.append(player)
                    player_id += 1
                    
        return players
    
    def _generate_schedule(self, season: int) -> List[Tuple[int, int, int]]:
        """Generate NFL schedule for a season (simplified)"""
        schedule = []
        game_id = len(self.all_games) + 1
        
        # Regular season (17 games per team)
        teams = list(range(1, 33))  # Team IDs 1-32
        
        # Each team plays every other team once (31 games) + 2 extra games
        # Simplified: each team plays 17 random opponents
        for team_id in teams:
            opponents = [t for t in teams if t != team_id]
            random.shuffle(opponents)
            
            # Take first 17 opponents
            for i in range(17):
                opponent = opponents[i]
                week = i + 1
                schedule.append((game_id, team_id, opponent))
                game_id += 1
                
        return schedule
    
    def _simulate_game(self, game_id: int, season: int, week: int, home_team_id: int, away_team_id: int) -> Game:
        """Simulate a single NFL game using Option C logic"""
        home_team = self.teams[home_team_id - 1]
        away_team = self.teams[away_team_id - 1]
        
        # Weather effects
        weather_options = ["clear", "rain", "snow"]
        weather = random.choice(weather_options)
        wind_mph = random.uniform(5, 20) if weather != "clear" else random.uniform(5, 10)
        
        # Calculate team strength difference
        rating_diff = home_team.rating - away_team.rating
        home_field_advantage = 2.5  # Home field advantage
        
        # Base game outcome using Option C components
        base_home_score = self._calculate_base_score(home_team.rating + home_field_advantage)
        base_away_score = self._calculate_base_score(away_team.rating)
        
        # Add variance and weather effects
        weather_adjustment = weather_adjustments(False, wind_mph, weather)
        pass_penalty = weather_adjustment["pass_logit"]
        
        # Apply weather effects to scoring
        home_score = max(0, int(base_home_score * (1 + pass_penalty * 0.1)))
        away_score = max(0, int(base_away_score * (1 + pass_penalty * 0.1)))
        
        # Add random variance
        home_score += random.randint(-7, 7)
        away_score += random.randint(-7, 7)
        
        # Ensure non-negative scores
        home_score = max(0, home_score)
        away_score = max(0, away_score)
        
        # Calculate yards and turnovers
        home_yards = self._calculate_yards(home_team.rating, weather)
        away_yards = self._calculate_yards(away_team.rating, weather)
        
        home_turnovers = self._calculate_turnovers(home_team.rating, away_team.rating)
        away_turnovers = self._calculate_turnovers(away_team.rating, home_team.rating)
        
        # Create game object
        game = Game(
            game_id=game_id,
            season=season,
            week=week,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            home_yards=home_yards,
            away_yards=away_yards,
            home_turnovers=home_turnovers,
            away_turnovers=away_turnovers,
            weather=weather,
            wind_mph=wind_mph
        )
        
        # Update team records
        if home_score > away_score:
            home_team.wins += 1
            away_team.losses += 1
        elif away_score > home_score:
            away_team.wins += 1
            home_team.losses += 1
        else:
            home_team.ties += 1
            away_team.ties += 1
            
        # Update team season totals
        home_team.points_scored += home_score
        home_team.points_allowed += away_score
        home_team.total_yards += home_yards
        home_team.turnovers += home_turnovers
        
        away_team.points_scored += away_score
        away_team.points_allowed += home_score
        away_team.total_yards += away_yards
        away_team.turnovers += away_turnovers
        
        # Generate player statistics for this game
        self._generate_player_game_stats(game)
        
        return game
    
    def _calculate_base_score(self, team_rating: float) -> int:
        """Calculate base score using Option C logic"""
        # Use sigmoid function for realistic scoring distribution
        base_score = 20 + (team_rating - 80) * 0.3
        base_score += random.normalvariate(0, 3)  # Random variance
        return max(0, int(base_score))
    
    def _calculate_yards(self, team_rating: float, weather: str) -> int:
        """Calculate total yards using Option C logic"""
        base_yards = 350 + (team_rating - 80) * 2
        
        # Weather effects
        if weather == "rain":
            base_yards *= 0.9
        elif weather == "snow":
            base_yards *= 0.85
            
        base_yards += random.normalvariate(0, 50)  # Random variance
        return max(100, int(base_yards))
    
    def _calculate_turnovers(self, offense_rating: float, defense_rating: float) -> int:
        """Calculate turnovers using Option C logic"""
        # Better offense = fewer turnovers, better defense = more forced turnovers
        turnover_prob = 0.15 - (offense_rating - 80) * 0.001 + (defense_rating - 80) * 0.001
        turnover_prob = max(0.05, min(0.25, turnover_prob))  # Clamp between 5-25%
        
        turnovers = 0
        if random.random() < turnover_prob:
            turnovers = random.randint(1, 3)  # 1-3 turnovers per game
            
        return turnovers
    
    def _generate_player_game_stats(self, game: Game):
        """Generate detailed player statistics for a game"""
        # Get players for both teams
        home_players = [p for p in self.players if p.team_id == game.home_team.team_id]
        away_players = [p for p in self.players if p.team_id == game.away_team.team_id]
        
        # Home team player stats
        for player in home_players:
            game_stats = self._calculate_player_game_stats(player, game.home_score, game.home_yards, game.home_turnovers)
            game_stats.update({
                "game_id": game.game_id,
                "opponent": game.away_team.name,
                "season": game.season,
                "week": game.week
            })
            player.game_stats.append(game_stats)
            
            # Update season totals
            self._update_player_season_totals(player, game_stats)
        
        # Away team player stats
        for player in away_players:
            game_stats = self._calculate_player_game_stats(player, game.away_score, game.away_yards, game.away_turnovers)
            game_stats.update({
                "game_id": game.game_id,
                "opponent": game.home_team.name,
                "season": game.season,
                "week": game.week
            })
            player.game_stats.append(game_stats)
            
            # Update season totals
            self._update_player_season_totals(player, game_stats)
    
    def _calculate_player_game_stats(self, player: Player, team_score: int, team_yards: int, team_turnovers: int) -> Dict:
        """Calculate individual player game statistics"""
        stats = {
            "passing_yards_game": 0,
            "passing_tds_game": 0,
            "interceptions_game": 0,
            "rushing_yards_game": 0,
            "rushing_tds_game": 0,
            "receptions_game": 0,
            "receiving_yards_game": 0,
            "receiving_tds_game": 0,
            "field_goals_made_game": 0,
            "field_goals_attempted_game": 0,
            "sacks_game": 0,
            "turnovers_forced_game": 0
        }
        
        if player.position == "QB":
            # QB gets majority of passing stats
            stats["passing_yards_game"] = int(team_yards * 0.7 * (player.rating / 100))
            stats["passing_tds_game"] = random.randint(0, min(4, team_score // 7))
            stats["interceptions_game"] = random.randint(0, min(2, team_turnovers))
            
        elif player.position == "RB":
            # RB gets rushing stats and some receiving
            stats["rushing_yards_game"] = int(team_yards * 0.3 * (player.rating / 100))
            stats["rushing_tds_game"] = random.randint(0, min(2, team_score // 7))
            stats["receptions_game"] = random.randint(0, 5)
            stats["receiving_yards_game"] = random.randint(0, 50)
            
        elif player.position in ["WR", "TE"]:
            # WR/TE get receiving stats
            stats["receptions_game"] = random.randint(0, 8)
            stats["receiving_yards_game"] = int(team_yards * 0.2 * (player.rating / 100))
            stats["receiving_tds_game"] = random.randint(0, min(2, team_score // 7))
            
        elif player.position == "K":
            # Kicker gets field goal stats
            stats["field_goals_attempted_game"] = random.randint(0, 3)
            stats["field_goals_made_game"] = random.randint(0, stats["field_goals_attempted_game"])
            
        elif player.position in ["LB", "DB", "DL"]:
            # Defensive players get defensive stats
            stats["sacks_game"] = random.randint(0, 2)
            stats["turnovers_forced_game"] = random.randint(0, 1)
            
        return stats
    
    def _update_player_season_totals(self, player: Player, game_stats: Dict):
        """Update player season totals"""
        player.passing_yards += game_stats["passing_yards_game"]
        player.passing_tds += game_stats["passing_tds_game"]
        player.interceptions += game_stats["interceptions_game"]
        player.rushing_yards += game_stats["rushing_yards_game"]
        player.rushing_tds += game_stats["rushing_tds_game"]
        player.receptions += game_stats["receptions_game"]
        player.receiving_yards += game_stats["receiving_yards_game"]
        player.receiving_tds += game_stats["receiving_tds_game"]
        player.field_goals_made += game_stats["field_goals_made_game"]
        player.field_goals_attempted += game_stats["field_goals_attempted_game"]
        player.sacks += game_stats["sacks_game"]
        player.turnovers_forced += game_stats["turnovers_forced_game"]
    
    def run_season(self, season: int):
        """Run a complete NFL season"""
        print(f"Running Season {season}...")
        
        # Reset team records
        for team in self.teams:
            team.wins = team.losses = team.ties = 0
            team.points_scored = team.points_allowed = 0
            team.total_yards = team.passing_yards = team.rushing_yards = 0
            team.turnovers = team.sacks = team.interceptions = team.fumbles_lost = 0
        
        # Reset player season totals
        for player in self.players:
            player.passing_yards = player.passing_tds = player.interceptions = 0
            player.rushing_yards = player.rushing_tds = 0
            player.receptions = player.receiving_yards = player.receiving_tds = 0
            player.field_goals_made = player.field_goals_attempted = 0
            player.sacks = player.turnovers_forced = 0
            player.game_stats = []
        
        # Generate and run schedule
        schedule = self._generate_schedule(season)
        
        for game_id, home_team_id, away_team_id in schedule:
            week = ((game_id - 1) % 272) + 1  # 272 games per season (17 * 32 / 2)
            game = self._simulate_game(game_id, season, week, home_team_id, away_team_id)
            self.all_games.append(game)
        
        self.seasons.append(season)
        print(f"Season {season} complete!")
    
    def create_dataframes(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Create the four required DataFrames"""
        
        # DataFrame 1: Player Stats Per Season (Aggregate)
        player_season_data = []
        for player in self.players:
            for season in self.seasons:
                player_season_data.append({
                    "Player_ID": player.player_id,
                    "Player_Name": player.name,
                    "Team": self.teams[player.team_id - 1].name,
                    "Position": player.position,
                    "Season": season,
                    "Total_Passing_Yards": player.passing_yards,
                    "Total_Passing_TDs": player.passing_tds,
                    "Total_Interceptions": player.interceptions,
                    "Total_Rushing_Yards": player.rushing_yards,
                    "Total_Rushing_TDs": player.rushing_tds,
                    "Total_Receptions": player.receptions,
                    "Total_Receiving_Yards": player.receiving_yards,
                    "Total_Receiving_TDs": player.receiving_tds,
                    "Field_Goals_Made": player.field_goals_made,
                    "Field_Goals_Attempted": player.field_goals_attempted,
                    "Total_Sacks": player.sacks,
                    "Total_Turnovers_Forced": player.turnovers_forced
                })
        
        df1_player_season = pd.DataFrame(player_season_data)
        
        # DataFrame 2: Team Stats Per Season (Aggregate)
        team_season_data = []
        for team in self.teams:
            for season in self.seasons:
                team_season_data.append({
                    "Team": team.name,
                    "Season": season,
                    "Total_Wins": team.wins,
                    "Total_Losses": team.losses,
                    "Total_Ties": team.ties,
                    "Points_Scored": team.points_scored,
                    "Points_Allowed": team.points_allowed,
                    "Total_Yards": team.total_yards,
                    "Passing_Yards": team.passing_yards,
                    "Rushing_Yards": team.rushing_yards,
                    "Total_Turnovers": team.turnovers,
                    "Sacks": team.sacks,
                    "Interceptions": team.interceptions,
                    "Fumbles_Lost": team.fumbles_lost
                })
        
        df2_team_season = pd.DataFrame(team_season_data)
        
        # DataFrame 3: Player Stats Per Game (Detailed Log)
        player_game_data = []
        for player in self.players:
            for game_stats in player.game_stats:
                player_game_data.append({
                    "Player_ID": player.player_id,
                    "Player_Name": player.name,
                    "Team": self.teams[player.team_id - 1].name,
                    "Position": player.position,
                    "Game_ID": game_stats["game_id"],
                    "Opponent": game_stats["opponent"],
                    "Season": game_stats["season"],
                    "Week": game_stats["week"],
                    "Passing_Yards_Game": game_stats["passing_yards_game"],
                    "Passing_TDs_Game": game_stats["passing_tds_game"],
                    "Interceptions_Game": game_stats["interceptions_game"],
                    "Rushing_Yards_Game": game_stats["rushing_yards_game"],
                    "Rushing_TDs_Game": game_stats["rushing_tds_game"],
                    "Receptions_Game": game_stats["receptions_game"],
                    "Receiving_Yards_Game": game_stats["receiving_yards_game"],
                    "Receiving_TDs_Game": game_stats["receiving_tds_game"],
                    "Field_Goals_Made_Game": game_stats["field_goals_made_game"],
                    "Field_Goals_Attempted_Game": game_stats["field_goals_attempted_game"],
                    "Sacks_Game": game_stats["sacks_game"],
                    "Turnovers_Forced_Game": game_stats["turnovers_forced_game"]
                })
        
        df3_player_game = pd.DataFrame(player_game_data)
        
        # DataFrame 4: Team Stats Per Game (Detailed Log)
        team_game_data = []
        for game in self.all_games:
            team_game_data.append({
                "Team": game.home_team.name,
                "Game_ID": game.game_id,
                "Opponent": game.away_team.name,
                "Season": game.season,
                "Week": game.week,
                "Points_Scored_Game": game.home_score,
                "Points_Allowed_Game": game.away_score,
                "Yards_Gained_Game": game.home_yards,
                "Yards_Allowed_Game": game.away_yards,
                "Turnovers_Game": game.home_turnovers,
                "Turnovers_Forced_Game": game.away_turnovers,
                "Weather": game.weather,
                "Wind_MPH": game.wind_mph
            })
            
            team_game_data.append({
                "Team": game.away_team.name,
                "Game_ID": game.game_id,
                "Opponent": game.home_team.name,
                "Season": game.season,
                "Week": game.week,
                "Points_Scored_Game": game.away_score,
                "Points_Allowed_Game": game.home_score,
                "Yards_Gained_Game": game.away_yards,
                "Yards_Allowed_Game": game.home_yards,
                "Turnovers_Game": game.away_turnovers,
                "Turnovers_Forced_Game": game.home_turnovers,
                "Weather": game.weather,
                "Wind_MPH": game.wind_mph
            })
        
        df4_team_game = pd.DataFrame(team_game_data)
        
        return df1_player_season, df2_team_season, df3_player_game, df4_team_game


def main():
    """Main simulation function"""
    print("NFL Game Simulation and Statistical Analysis")
    print("=" * 50)
    
    # Initialize simulation engine
    engine = NFLSimulationEngine(seed=2024)
    
    # Run 3 complete seasons
    for season in range(2024, 2027):
        engine.run_season(season)
    
    print("\nGenerating DataFrames...")
    
    # Create DataFrames
    df1_player_season, df2_team_season, df3_player_game, df4_team_game = engine.create_dataframes()
    
    # Display results
    print("\n" + "="*80)
    print("DATAFRAME 1: Player Stats Per Season (Aggregate)")
    print("="*80)
    print(f"Shape: {df1_player_season.shape}")
    print("\nFirst 10 rows:")
    print(df1_player_season.head(10))
    print("\nSample statistics:")
    print(df1_player_season.groupby(['Position', 'Season']).agg({
        'Total_Passing_Yards': 'mean',
        'Total_Rushing_Yards': 'mean',
        'Total_Receiving_Yards': 'mean',
        'Total_Sacks': 'mean'
    }).round(1))
    
    print("\n" + "="*80)
    print("DATAFRAME 2: Team Stats Per Season (Aggregate)")
    print("="*80)
    print(f"Shape: {df2_team_season.shape}")
    print("\nFirst 10 rows:")
    print(df2_team_season.head(10))
    print("\nTop 10 teams by wins (all seasons):")
    print(df2_team_season.groupby('Team')['Total_Wins'].sum().sort_values(ascending=False).head(10))
    
    print("\n" + "="*80)
    print("DATAFRAME 3: Player Stats Per Game (Detailed Log)")
    print("="*80)
    print(f"Shape: {df3_player_game.shape}")
    print("\nFirst 10 rows:")
    print(df3_player_game.head(10))
    print("\nSample QB game stats:")
    qb_games = df3_player_game[df3_player_game['Position'] == 'QB']
    print(qb_games[['Player_Name', 'Team', 'Game_ID', 'Passing_Yards_Game', 'Passing_TDs_Game']].head(10))
    
    print("\n" + "="*80)
    print("DATAFRAME 4: Team Stats Per Game (Detailed Log)")
    print("="*80)
    print(f"Shape: {df4_team_game.shape}")
    print("\nFirst 10 rows:")
    print(df4_team_game.head(10))
    print("\nSample game results:")
    print(df4_team_game[['Team', 'Opponent', 'Game_ID', 'Points_Scored_Game', 'Yards_Gained_Game']].head(10))
    
    # Summary statistics
    print("\n" + "="*80)
    print("SIMULATION SUMMARY STATISTICS")
    print("="*80)
    
    total_games = len(df4_team_game) // 2  # Each game appears twice (home/away)
    total_seasons = len(df4_team_game['Season'].unique())
    
    print(f"Total Games Simulated: {total_games}")
    print(f"Total Seasons: {total_seasons}")
    print(f"Games per Season: {total_games // total_seasons}")
    print(f"Total Players: {len(df1_player_season['Player_ID'].unique())}")
    print(f"Total Teams: {len(df2_team_season['Team'].unique())}")
    
    # League-wide averages
    print(f"\nLeague Averages (per game):")
    print(f"Points per Game: {df4_team_game['Points_Scored_Game'].mean():.1f}")
    print(f"Yards per Game: {df4_team_game['Yards_Gained_Game'].mean():.1f}")
    print(f"Turnovers per Game: {df4_team_game['Turnovers_Game'].mean():.1f}")
    
    # Top performers
    print(f"\nTop 5 QBs by Passing Yards:")
    top_qbs = df1_player_season[df1_player_season['Position'] == 'QB'].groupby('Player_Name')['Total_Passing_Yards'].sum().sort_values(ascending=False).head(5)
    print(top_qbs)
    
    print(f"\nTop 5 RBs by Rushing Yards:")
    top_rbs = df1_player_season[df1_player_season['Position'] == 'RB'].groupby('Player_Name')['Total_Rushing_Yards'].sum().sort_values(ascending=False).head(5)
    print(top_rbs)
    
    return df1_player_season, df2_team_season, df3_player_game, df4_team_game


if __name__ == "__main__":
    df1, df2, df3, df4 = main()
