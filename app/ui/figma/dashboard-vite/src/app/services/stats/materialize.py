"""
Stats materialization service for aggregating game stats into season/career totals.
Creates materialized views for efficient querying.
"""

from typing import Dict, List, Optional
from sqlmodel import Session, select, func
from app.models.stats_models import (
    PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats
)
from app.models.sim_models import SimGame as Game, SimTeam as Team
from app.models.player_models import Player


def materialize_season(year: int, session: Session) -> Dict[str, int]:
    """
    Materialize season stats by aggregating all game stats for the year.
    Returns summary of records created/updated.
    """
    # Get all games for the season
    games = session.exec(
        select(Game).where(Game.season == year)
    ).all()
    
    if not games:
        raise ValueError(f"No games found for season {year}")
    
    game_ids = [game.id for game in games]
    
    # Aggregate player season stats
    player_season_stats = _aggregate_player_season_stats(game_ids, year, session)
    
    # Aggregate team season stats
    team_season_stats = _aggregate_team_season_stats(game_ids, year, session)
    
    # Save player season stats
    player_created = 0
    player_updated = 0
    
    for player_id, stats in player_season_stats.items():
        existing = session.exec(
            select(PlayerSeasonStats).where(
                PlayerSeasonStats.player_id == player_id,
                PlayerSeasonStats.season == year
            )
        ).first()
        
        if existing:
            # Update existing
            for field in stats.__fields__:
                if field not in ['id', 'created_at', 'updated_at']:
                    setattr(existing, field, getattr(stats, field))
            player_updated += 1
        else:
            # Create new
            session.add(stats)
            player_created += 1
    
    # Save team season stats
    team_created = 0
    team_updated = 0
    
    for team_id, stats in team_season_stats.items():
        existing = session.exec(
            select(TeamSeasonStats).where(
                TeamSeasonStats.team_id == team_id,
                TeamSeasonStats.season == year
            )
        ).first()
        
        if existing:
            # Update existing
            for field in stats.__fields__:
                if field not in ['id', 'created_at', 'updated_at']:
                    setattr(existing, field, getattr(stats, field))
            team_updated += 1
        else:
            # Create new
            session.add(stats)
            team_created += 1
    
    session.commit()
    
    return {
        "season": year,
        "games_processed": len(games),
        "player_season_stats_created": player_created,
        "player_season_stats_updated": player_updated,
        "team_season_stats_created": team_created,
        "team_season_stats_updated": team_updated
    }


def materialize_career(session: Session) -> Dict[str, int]:
    """
    Materialize career stats by aggregating all season stats.
    Returns summary of records created/updated.
    """
    # Get all seasons
    seasons = session.exec(
        select(func.distinct(PlayerSeasonStats.season))
        .order_by(PlayerSeasonStats.season)
    ).all()
    
    if not seasons:
        raise ValueError("No season stats found to aggregate")
    
    # Aggregate player career stats
    player_career_stats = _aggregate_player_career_stats(seasons, session)
    
    # Save career stats (simplified - would create PlayerCareerStats table)
    career_created = 0
    
    for player_id, stats in player_career_stats.items():
        # In a full implementation, you'd create PlayerCareerStats records
        # For now, just count them
        career_created += 1
    
    session.commit()
    
    return {
        "seasons_processed": len(seasons),
        "player_career_stats_created": career_created
    }


def _aggregate_player_season_stats(game_ids: List[int], year: int, 
                                  session: Session) -> Dict[int, PlayerSeasonStats]:
    """Aggregate player game stats into season totals."""
    # Get all player game stats for the season
    player_game_stats = session.exec(
        select(PlayerGameStats).where(PlayerGameStats.game_id.in_(game_ids))
    ).all()
    
    # Group by player
    player_stats: Dict[int, PlayerSeasonStats] = {}
    
    for pgs in player_game_stats:
        player_id = pgs.player_id
        
        if player_id not in player_stats:
            player_stats[player_id] = PlayerSeasonStats(
                player_id=player_id,
                team_id=pgs.team_id,
                season=year,
                games_played=0,
                games_started=0
            )
        
        ps = player_stats[player_id]
        
        # Count games played (simplified - assume 1 game per PlayerGameStats)
        ps.games_played += 1
        
        # Aggregate all stat fields
        ps.snaps_offense += pgs.snaps_offense
        ps.snaps_defense += pgs.snaps_defense
        ps.snaps_special_teams += pgs.snaps_special_teams
        
        # Passing stats
        ps.pass_attempts += pgs.pass_attempts
        ps.pass_completions += pgs.pass_completions
        ps.pass_yards += pgs.pass_yards
        ps.pass_touchdowns += pgs.pass_touchdowns
        ps.interceptions += pgs.interceptions
        ps.sacks_taken += pgs.sacks_taken
        ps.sack_yards += pgs.sack_yards
        ps.qb_hits += pgs.qb_hits
        ps.pressures_faced += pgs.pressures_faced
        
        # Rushing stats
        ps.rush_attempts += pgs.rush_attempts
        ps.rush_yards += pgs.rush_yards
        ps.rush_touchdowns += pgs.rush_touchdowns
        ps.fumbles += pgs.fumbles
        ps.fumbles_lost += pgs.fumbles_lost
        
        # Receiving stats
        ps.targets += pgs.targets
        ps.receptions += pgs.receptions
        ps.receiving_yards += pgs.receiving_yards
        ps.receiving_touchdowns += pgs.receiving_touchdowns
        ps.drops += pgs.drops
        ps.yards_after_catch += pgs.yards_after_catch
        
        # Defensive stats
        ps.tackles += pgs.tackles
        ps.tackles_for_loss += pgs.tackles_for_loss
        ps.sacks += pgs.sacks
        ps.quarterback_hits += pgs.quarterback_hits
        ps.pressures += pgs.pressures
        ps.pass_deflections += pgs.pass_deflections
        ps.interceptions_caught += pgs.interceptions_caught
        ps.forced_fumbles += pgs.forced_fumbles
        ps.fumble_recoveries += pgs.fumble_recoveries
        
        # Coverage stats
        ps.targets_against += pgs.targets_against
        ps.completions_allowed += pgs.completions_allowed
        ps.yards_allowed += pgs.yards_allowed
        ps.touchdowns_allowed += pgs.touchdowns_allowed
        ps.passes_defended += pgs.passes_defended
        
        # Special Teams stats
        ps.field_goals_made += pgs.field_goals_made
        ps.field_goals_attempted += pgs.field_goals_attempted
        ps.extra_points_made += pgs.extra_points_made
        ps.extra_points_attempted += pgs.extra_points_attempted
        ps.punts += pgs.punts
        ps.punt_yards += pgs.punt_yards
        ps.punt_net_yards += pgs.punt_net_yards
        ps.punts_in_20 += pgs.punts_in_20
        ps.kickoff_returns += pgs.kickoff_returns
        ps.kickoff_return_yards += pgs.kickoff_return_yards
        ps.punt_returns += pgs.punt_returns
        ps.punt_return_yards += pgs.punt_return_yards
        
        # Advanced OL stats
        ps.sacks_allowed += pgs.sacks_allowed
        ps.pressures_allowed += pgs.pressures_allowed
        ps.qb_hits_allowed += pgs.qb_hits_allowed
        
        # Situational splits
        ps.third_down_conversions += pgs.third_down_conversions
        ps.third_down_attempts += pgs.third_down_attempts
        ps.fourth_down_conversions += pgs.fourth_down_conversions
        ps.fourth_down_attempts += pgs.fourth_down_attempts
        ps.red_zone_touchdowns += pgs.red_zone_touchdowns
        ps.red_zone_attempts += pgs.red_zone_attempts
        ps.goal_to_go_touchdowns += pgs.goal_to_go_touchdowns
        ps.goal_to_go_attempts += pgs.goal_to_go_attempts
        ps.two_minute_touchdowns += pgs.two_minute_touchdowns
        ps.two_minute_attempts += pgs.two_minute_attempts
    
    return player_stats


def _aggregate_team_season_stats(game_ids: List[int], year: int, 
                                session: Session) -> Dict[int, TeamSeasonStats]:
    """Aggregate team game stats into season totals."""
    # Get all team game stats for the season
    team_game_stats = session.exec(
        select(TeamGameStats).where(TeamGameStats.game_id.in_(game_ids))
    ).all()
    
    # Group by team
    team_stats: Dict[int, TeamSeasonStats] = {}
    
    for tgs in team_game_stats:
        team_id = tgs.team_id
        
        if team_id not in team_stats:
            team_stats[team_id] = TeamSeasonStats(
                team_id=team_id,
                season=year,
                games_played=0,
                wins=0,
                losses=0,
                ties=0
            )
        
        ts = team_stats[team_id]
        
        # Count games played
        ts.games_played += 1
        
        # Aggregate team stats
        ts.points_scored += tgs.points_scored
        ts.total_yards += tgs.total_yards
        ts.passing_yards += tgs.passing_yards
        ts.rushing_yards += tgs.rushing_yards
        ts.turnovers_committed += tgs.turnovers_committed
        ts.turnovers_forced += tgs.turnovers_forced
        
        # Special teams
        ts.field_goals_made += tgs.field_goals_made
        ts.field_goals_attempted += tgs.field_goals_attempted
        ts.punts += tgs.punts
        ts.punt_net_yards += tgs.punt_net_yards
        ts.punts_in_20 += tgs.punts_in_20
        
        # Situational splits
        ts.third_down_conversions += tgs.third_down_conversions
        ts.third_down_attempts += tgs.third_down_attempts
        ts.fourth_down_conversions += tgs.fourth_down_conversions
        ts.fourth_down_attempts += tgs.fourth_down_attempts
        ts.red_zone_touchdowns += tgs.red_zone_touchdowns
        ts.red_zone_attempts += tgs.red_zone_attempts
    
    # Calculate wins/losses/ties from game results
    _calculate_team_record(game_ids, team_stats, session)
    
    return team_stats


def _calculate_team_record(game_ids: List[int], team_stats: Dict[int, TeamSeasonStats], 
                          session: Session):
    """Calculate team win/loss record from game results."""
    games = session.exec(
        select(Game).where(Game.id.in_(game_ids))
    ).all()
    
    for game in games:
        home_team_id = game.home_team_id
        away_team_id = game.away_team_id
        
        if game.home_score > game.away_score:
            # Home team wins
            if home_team_id in team_stats:
                team_stats[home_team_id].wins += 1
            if away_team_id in team_stats:
                team_stats[away_team_id].losses += 1
        elif game.away_score > game.home_score:
            # Away team wins
            if away_team_id in team_stats:
                team_stats[away_team_id].wins += 1
            if home_team_id in team_stats:
                team_stats[home_team_id].losses += 1
        else:
            # Tie
            if home_team_id in team_stats:
                team_stats[home_team_id].ties += 1
            if away_team_id in team_stats:
                team_stats[away_team_id].ties += 1


def _aggregate_player_career_stats(seasons: List[int], 
                                  session: Session) -> Dict[int, Dict]:
    """Aggregate player season stats into career totals."""
    # Get all player season stats
    player_season_stats = session.exec(
        select(PlayerSeasonStats).where(PlayerSeasonStats.season.in_(seasons))
    ).all()
    
    # Group by player
    career_stats: Dict[int, Dict] = {}
    
    for pss in player_season_stats:
        player_id = pss.player_id
        
        if player_id not in career_stats:
            career_stats[player_id] = {
                "player_id": player_id,
                "seasons_played": 0,
                "total_games": 0,
                "total_stats": {}
            }
        
        cs = career_stats[player_id]
        cs["seasons_played"] += 1
        cs["total_games"] += pss.games_played
        
        # Aggregate all stat fields (simplified)
        total_stats = cs["total_stats"]
        for field in pss.__fields__:
            if field not in ['id', 'player_id', 'team_id', 'season', 'created_at', 'updated_at']:
                if field not in total_stats:
                    total_stats[field] = 0
                total_stats[field] += getattr(pss, field)
    
    return career_stats
