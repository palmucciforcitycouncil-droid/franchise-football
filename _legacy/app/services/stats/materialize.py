from __future__ import annotations
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func
from app.core.db import session_scope
from app.models.stats import (
    PlayerGameStats, TeamGameStats, 
    PlayerSeasonStats, TeamSeasonStats, PlayerCareerStats
)
from app.models.sim_models import Game
import logging

logger = logging.getLogger(__name__)

def materialize_season(year: int | None = None) -> None:
    """
    Materialize season statistics from game-level stats.
    
    Args:
        year: Season year to process. If None, processes all seasons.
    """
    with session_scope() as session:
        # Get all games for the season(s)
        query = select(Game)
        if year is not None:
            query = query.where(Game.season == year)
        
        games = session.exec(query).all()
        
        if not games:
            logger.warning(f"No games found for season {year}")
            return
        
        # Get unique seasons from games
        seasons = list(set(game.season for game in games))
        
        for season in seasons:
            logger.info(f"Materializing season {season}")
            
            # Materialize team season stats
            _materialize_team_season_stats(session, season)
            
            # Materialize player season stats
            _materialize_player_season_stats(session, season)
        
        session.commit()
        logger.info(f"Successfully materialized season {year}")

def materialize_career() -> None:
    """Materialize career statistics from season-level stats."""
    with session_scope() as session:
        logger.info("Materializing career statistics")
        
        # Get all players who have season stats
        player_seasons = session.exec(
            select(PlayerSeasonStats.player_id).distinct()
        ).all()
        
        for player_id in player_seasons:
            _materialize_player_career_stats(session, player_id)
        
        session.commit()
        logger.info("Successfully materialized career statistics")

def _materialize_team_season_stats(session: Session, season: int) -> None:
    """Materialize team season statistics for a given season."""
    
    # Delete existing season stats
    session.exec(
        delete(TeamSeasonStats).where(TeamSeasonStats.season == season)
    )
    
    # Get all team game stats for the season
    team_game_stats = session.exec(
        select(TeamGameStats)
        .join(Game, TeamGameStats.game_id == Game.id)
        .where(Game.season == season)
    ).all()
    
    # Group by team
    team_stats_map: Dict[int, List[TeamGameStats]] = {}
    for stat in team_game_stats:
        if stat.team_id not in team_stats_map:
            team_stats_map[stat.team_id] = []
        team_stats_map[stat.team_id].append(stat)
    
    # Aggregate for each team
    for team_id, game_stats_list in team_stats_map.items():
        season_stat = TeamSeasonStats(
            team_id=team_id,
            season=season,
            gp=len(game_stats_list)
        )
        
        # Sum all stats
        for game_stat in game_stats_list:
            season_stat.snaps_offense += game_stat.snaps_offense
            season_stat.snaps_defense += game_stat.snaps_defense
            season_stat.snaps_st += game_stat.snaps_st
            
            # Offensive stats
            season_stat.pass_attempts += game_stat.pass_attempts
            season_stat.pass_completions += game_stat.pass_completions
            season_stat.pass_yards += game_stat.pass_yards
            season_stat.pass_td += game_stat.pass_td
            season_stat.pass_int += game_stat.pass_int
            season_stat.sacks_allowed += game_stat.sacks_allowed
            season_stat.sack_yards_allowed += game_stat.sack_yards_allowed
            season_stat.qb_hits_allowed += game_stat.qb_hits_allowed
            season_stat.pressures_allowed += game_stat.pressures_allowed
            
            season_stat.rush_attempts += game_stat.rush_attempts
            season_stat.rush_yards += game_stat.rush_yards
            season_stat.rush_td += game_stat.rush_td
            
            season_stat.total_yards += game_stat.total_yards
            season_stat.total_td += game_stat.total_td
            season_stat.turnovers += game_stat.turnovers
            
            # Defensive stats
            season_stat.tackles_solo += game_stat.tackles_solo
            season_stat.tackles_assist += game_stat.tackles_assist
            season_stat.tfl += game_stat.tfl
            season_stat.sacks += game_stat.sacks
            season_stat.qb_hits += game_stat.qb_hits
            season_stat.pressures += game_stat.pressures
            season_stat.interceptions += game_stat.interceptions
            season_stat.int_yards += game_stat.int_yards
            season_stat.int_td += game_stat.int_td
            season_stat.pbus += game_stat.pbus
            season_stat.forced_fumbles += game_stat.forced_fumbles
            season_stat.fumble_recoveries += game_stat.fumble_recoveries
            season_stat.fr_yards += game_stat.fr_yards
            season_stat.fr_td += game_stat.fr_td
            
            # Special teams
            season_stat.kickoffs += game_stat.kickoffs
            season_stat.kickoff_touchbacks += game_stat.kickoff_touchbacks
            season_stat.punts += game_stat.punts
            season_stat.punt_yards += game_stat.punt_yards
            season_stat.punts_in_20 += game_stat.punts_in_20
            season_stat.punt_touchbacks += game_stat.punt_touchbacks
            season_stat.punt_returns += game_stat.punt_returns
            season_stat.punt_return_yards += game_stat.punt_return_yards
            season_stat.punt_return_td += game_stat.punt_return_td
            season_stat.kickoff_returns += game_stat.kickoff_returns
            season_stat.kickoff_return_yards += game_stat.kickoff_return_yards
            season_stat.kickoff_return_td += game_stat.kickoff_return_td
            
            # Kicking
            season_stat.fg_attempts += game_stat.fg_attempts
            season_stat.fg_made += game_stat.fg_made
            season_stat.fg_yards += game_stat.fg_yards
            season_stat.xp_attempts += game_stat.xp_attempts
            season_stat.xp_made += game_stat.xp_made
            
            # Penalties
            season_stat.penalties += game_stat.penalties
            season_stat.penalty_yards += game_stat.penalty_yards
            
            # Advanced metrics
            season_stat.epa += game_stat.epa
            season_stat.explosives += game_stat.explosives
            season_stat.third_down_conversions += game_stat.third_down_conversions
            season_stat.third_down_attempts += game_stat.third_down_attempts
        
        # Calculate derived metrics
        if season_stat.gp > 0:
            season_stat.success_rate = season_stat.epa / max(1, season_stat.snaps_offense + season_stat.snaps_defense)
        
        session.add(season_stat)

def _materialize_player_season_stats(session: Session, season: int) -> None:
    """Materialize player season statistics for a given season."""
    
    # Delete existing season stats
    session.exec(
        delete(PlayerSeasonStats).where(PlayerSeasonStats.season == season)
    )
    
    # Get all player game stats for the season
    player_game_stats = session.exec(
        select(PlayerGameStats)
        .join(Game, PlayerGameStats.game_id == Game.id)
        .where(Game.season == season)
    ).all()
    
    # Group by player
    player_stats_map: Dict[int, List[PlayerGameStats]] = {}
    for stat in player_game_stats:
        if stat.player_id not in player_stats_map:
            player_stats_map[stat.player_id] = []
        player_stats_map[stat.player_id].append(stat)
    
    # Aggregate for each player
    for player_id, game_stats_list in player_stats_map.items():
        # Get team_id from first game stat
        team_id = game_stats_list[0].team_id
        
        season_stat = PlayerSeasonStats(
            player_id=player_id,
            team_id=team_id,
            season=season,
            gp=len(game_stats_list),
            gs=sum(1 for stat in game_stats_list if stat.gs)
        )
        
        # Sum all stats
        for game_stat in game_stats_list:
            season_stat.snaps_offense += game_stat.snaps_offense
            season_stat.snaps_defense += game_stat.snaps_defense
            season_stat.snaps_st += game_stat.snaps_st
            
            # Passing stats
            season_stat.pass_attempts += game_stat.pass_attempts
            season_stat.pass_completions += game_stat.pass_completions
            season_stat.pass_yards += game_stat.pass_yards
            season_stat.pass_td += game_stat.pass_td
            season_stat.pass_int += game_stat.pass_int
            season_stat.sacks += game_stat.sacks
            season_stat.sack_yards += game_stat.sack_yards
            season_stat.qb_hits += game_stat.qb_hits
            season_stat.pressures += game_stat.pressures
            
            # Rushing stats
            season_stat.rush_attempts += game_stat.rush_attempts
            season_stat.rush_yards += game_stat.rush_yards
            season_stat.rush_td += game_stat.rush_td
            season_stat.broken_tackle += game_stat.broken_tackle
            
            # Receiving stats
            season_stat.targets += game_stat.targets
            season_stat.receptions += game_stat.receptions
            season_stat.receiving_yards += game_stat.receiving_yards
            season_stat.receiving_td += game_stat.receiving_td
            season_stat.yac += game_stat.yac
            
            # Defense stats
            season_stat.tackles_solo += game_stat.tackles_solo
            season_stat.tackles_assist += game_stat.tackles_assist
            season_stat.tfl += game_stat.tfl
            season_stat.sacks_defense += game_stat.sacks_defense
            season_stat.qb_hits_defense += game_stat.qb_hits_defense
            season_stat.pressures_defense += game_stat.pressures_defense
            season_stat.interceptions += game_stat.interceptions
            season_stat.int_yards += game_stat.int_yards
            season_stat.int_td += game_stat.int_td
            season_stat.pbus += game_stat.pbus
            season_stat.forced_fumbles += game_stat.forced_fumbles
            season_stat.fumble_recoveries += game_stat.fumble_recoveries
            season_stat.fr_yards += game_stat.fr_yards
            season_stat.fr_td += game_stat.fr_td
            
            # Special teams
            season_stat.kickoffs += game_stat.kickoffs
            season_stat.kickoff_touchbacks += game_stat.kickoff_touchbacks
            season_stat.punts += game_stat.punts
            season_stat.punt_yards += game_stat.punt_yards
            season_stat.punts_in_20 += game_stat.punts_in_20
            season_stat.punt_touchbacks += game_stat.punt_touchbacks
            season_stat.punt_returns += game_stat.punt_returns
            season_stat.punt_return_yards += game_stat.punt_return_yards
            season_stat.punt_return_td += game_stat.punt_return_td
            season_stat.kickoff_returns += game_stat.kickoff_returns
            season_stat.kickoff_return_yards += game_stat.kickoff_return_yards
            season_stat.kickoff_return_td += game_stat.kickoff_return_td
            
            # Kicking
            season_stat.fg_attempts += game_stat.fg_attempts
            season_stat.fg_made += game_stat.fg_made
            season_stat.fg_yards += game_stat.fg_yards
            season_stat.xp_attempts += game_stat.xp_attempts
            season_stat.xp_made += game_stat.xp_made
            
            # Turnovers
            season_stat.fumbles += game_stat.fumbles
            season_stat.fumbles_lost += game_stat.fumbles_lost
            
            # Penalties
            season_stat.penalties += game_stat.penalties
            season_stat.penalty_yards += game_stat.penalty_yards
            
            # Advanced metrics
            season_stat.epa += game_stat.epa
            season_stat.explosives += game_stat.explosives
            season_stat.third_down_conversions += game_stat.third_down_conversions
            season_stat.third_down_attempts += game_stat.third_down_attempts
        
        # Calculate derived metrics
        total_snaps = season_stat.snaps_offense + season_stat.snaps_defense + season_stat.snaps_st
        if total_snaps > 0:
            season_stat.success_rate = season_stat.epa / total_snaps
        
        session.add(season_stat)

def _materialize_player_career_stats(session: Session, player_id: int) -> None:
    """Materialize career statistics for a single player."""
    
    # Delete existing career stats
    session.exec(
        delete(PlayerCareerStats).where(PlayerCareerStats.player_id == player_id)
    )
    
    # Get all season stats for the player
    season_stats = session.exec(
        select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == player_id)
    ).all()
    
    if not season_stats:
        return
    
    # Get team_id from most recent season
    team_id = season_stats[-1].team_id
    
    career_stat = PlayerCareerStats(
        player_id=player_id,
        team_id=team_id
    )
    
    # Sum all season stats
    for season_stat in season_stats:
        career_stat.gp += season_stat.gp
        career_stat.gs += season_stat.gs
        career_stat.snaps_offense += season_stat.snaps_offense
        career_stat.snaps_defense += season_stat.snaps_defense
        career_stat.snaps_st += season_stat.snaps_st
        
        # Passing stats
        career_stat.pass_attempts += season_stat.pass_attempts
        career_stat.pass_completions += season_stat.pass_completions
        career_stat.pass_yards += season_stat.pass_yards
        career_stat.pass_td += season_stat.pass_td
        career_stat.pass_int += season_stat.pass_int
        career_stat.sacks += season_stat.sacks
        career_stat.sack_yards += season_stat.sack_yards
        career_stat.qb_hits += season_stat.qb_hits
        career_stat.pressures += season_stat.pressures
        
        # Rushing stats
        career_stat.rush_attempts += season_stat.rush_attempts
        career_stat.rush_yards += season_stat.rush_yards
        career_stat.rush_td += season_stat.rush_td
        career_stat.broken_tackle += season_stat.broken_tackle
        
        # Receiving stats
        career_stat.targets += season_stat.targets
        career_stat.receptions += season_stat.receptions
        career_stat.receiving_yards += season_stat.receiving_yards
        career_stat.receiving_td += season_stat.receiving_td
        career_stat.yac += season_stat.yac
        
        # Defense stats
        career_stat.tackles_solo += season_stat.tackles_solo
        career_stat.tackles_assist += season_stat.tackles_assist
        career_stat.tfl += season_stat.tfl
        career_stat.sacks_defense += season_stat.sacks_defense
        career_stat.qb_hits_defense += season_stat.qb_hits_defense
        career_stat.pressures_defense += season_stat.pressures_defense
        career_stat.interceptions += season_stat.interceptions
        career_stat.int_yards += season_stat.int_yards
        career_stat.int_td += season_stat.int_td
        career_stat.pbus += season_stat.pbus
        career_stat.forced_fumbles += season_stat.forced_fumbles
        career_stat.fumble_recoveries += season_stat.fumble_recoveries
        career_stat.fr_yards += season_stat.fr_yards
        career_stat.fr_td += season_stat.fr_td
        
        # Special teams
        career_stat.kickoffs += season_stat.kickoffs
        career_stat.kickoff_touchbacks += season_stat.kickoff_touchbacks
        career_stat.punts += season_stat.punts
        career_stat.punt_yards += season_stat.punt_yards
        career_stat.punts_in_20 += season_stat.punts_in_20
        career_stat.punt_touchbacks += season_stat.punt_touchbacks
        career_stat.punt_returns += season_stat.punt_returns
        career_stat.punt_return_yards += season_stat.punt_return_yards
        career_stat.punt_return_td += season_stat.punt_return_td
        career_stat.kickoff_returns += season_stat.kickoff_returns
        career_stat.kickoff_return_yards += season_stat.kickoff_return_yards
        career_stat.kickoff_return_td += season_stat.kickoff_return_td
        
        # Kicking
        career_stat.fg_attempts += season_stat.fg_attempts
        career_stat.fg_made += season_stat.fg_made
        career_stat.fg_yards += season_stat.fg_yards
        career_stat.xp_attempts += season_stat.xp_attempts
        career_stat.xp_made += season_stat.xp_made
        
        # Turnovers
        career_stat.fumbles += season_stat.fumbles
        career_stat.fumbles_lost += season_stat.fumbles_lost
        
        # Penalties
        career_stat.penalties += season_stat.penalties
        career_stat.penalty_yards += season_stat.penalty_yards
        
        # Advanced metrics
        career_stat.epa += season_stat.epa
        career_stat.explosives += season_stat.explosives
        career_stat.third_down_conversions += season_stat.third_down_conversions
        career_stat.third_down_attempts += season_stat.third_down_attempts
    
    # Calculate derived metrics
    total_snaps = career_stat.snaps_offense + career_stat.snaps_defense + career_stat.snaps_st
    if total_snaps > 0:
        career_stat.success_rate = career_stat.epa / total_snaps
    
    session.add(career_stat)
