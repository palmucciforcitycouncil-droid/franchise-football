"""
Read-side functions for stats queries.
Thin read functions querying materialized stats tables.
"""

from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, func, and_, or_
from app.models.stats_models import PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats
from app.models.sim_models import SimGame as Game, SimTeam as Team
from app.models.player_models import Player
from app.ui.dto import (
    GameBoxDTO, PlayerSeasonLineDTO, TeamSeasonLineDTO, LeadersDTO, LeaderEntry,
    PlayerStatLine, TeamStatLine
)


def get_game_box(game_id: int, session: Session) -> Optional[GameBoxDTO]:
    """Get complete game box score with advanced stats."""
    # Get game info
    game = session.exec(select(Game).where(Game.id == game_id)).first()
    if not game:
        return None
    
    # Get team info
    home_team = session.exec(select(Team).where(Team.id == game.home_team_id)).first()
    away_team = session.exec(select(Team).where(Team.id == game.away_team_id)).first()
    
    if not home_team or not away_team:
        return None
    
    # Get team game stats
    home_team_stats = session.exec(
        select(TeamGameStats).where(
            TeamGameStats.game_id == game_id,
            TeamGameStats.team_id == game.home_team_id
        )
    ).first()
    
    away_team_stats = session.exec(
        select(TeamGameStats).where(
            TeamGameStats.game_id == game_id,
            TeamGameStats.team_id == game.away_team_id
        )
    ).first()
    
    # Get player stats
    home_player_stats = _get_player_game_stats(game_id, game.home_team_id, session)
    away_player_stats = _get_player_game_stats(game_id, game.away_team_id, session)
    
    return GameBoxDTO(
        game_id=game_id,
        home_team_id=game.home_team_id,
        away_team_id=game.away_team_id,
        home_team_name=home_team.name,
        away_team_name=away_team.name,
        season=game.season,
        week=game.week,
        game_type=game.game_type,
        final_score_home=game.home_score,
        final_score_away=game.away_score,
        home_team_stats=_convert_team_stats(home_team_stats, home_team.name),
        away_team_stats=_convert_team_stats(away_team_stats, away_team.name),
        home_player_stats=home_player_stats,
        away_player_stats=away_player_stats
    )


def get_leaders(year: Optional[int] = None, stat: str = "passing_yards", top: int = 10,
               split: Optional[str] = None, role: Optional[str] = None,
               scope: str = "regular", session: Session = None) -> LeadersDTO:
    """Get statistical leaders with advanced filtering."""
    
    # Build query based on stat type
    if stat.startswith("passing_"):
        leaders = _get_passing_leaders(year, stat, top, split, role, scope, session)
    elif stat.startswith("rushing_"):
        leaders = _get_rushing_leaders(year, stat, top, split, role, scope, session)
    elif stat.startswith("receiving_"):
        leaders = _get_receiving_leaders(year, stat, top, split, role, scope, session)
    elif stat.startswith("defensive_"):
        leaders = _get_defensive_leaders(year, stat, top, split, role, scope, session)
    elif stat.startswith("special_"):
        leaders = _get_special_teams_leaders(year, stat, top, split, role, scope, session)
    else:
        leaders = []
    
    return LeadersDTO(
        stat=stat,
        year=year,
        split=split,
        role=role,
        scope=scope,
        leaders=leaders,
        total_qualified=len(leaders)
    )


def get_player_season_lines(year: int, team_id: Optional[int] = None,
                          position: Optional[str] = None, split: Optional[str] = None,
                          session: Session = None) -> List[PlayerSeasonLineDTO]:
    """Get player season stat lines with filtering."""
    
    query = select(PlayerSeasonStats).where(PlayerSeasonStats.season == year)
    
    if team_id:
        query = query.where(PlayerSeasonStats.team_id == team_id)
    
    if position:
        # Would need to join with Player table to filter by position
        pass
    
    player_season_stats = session.exec(query).all()
    
    # Convert to DTOs
    result = []
    for pss in player_season_stats:
        # Get player and team info
        player = session.exec(select(Player).where(Player.id == pss.player_id)).first()
        team = session.exec(select(Team).where(Team.id == pss.team_id)).first()
        
        if player and team:
            result.append(PlayerSeasonLineDTO(
                player_id=pss.player_id,
                player_name=player.name,
                position=player.position,
                team_id=pss.team_id,
                team_name=team.name,
                season=year,
                games_played=pss.games_played,
                games_started=pss.games_started,
                snaps_offense=pss.snaps_offense,
                snaps_defense=pss.snaps_defense,
                snaps_special_teams=pss.snaps_special_teams,
                pass_attempts=pss.pass_attempts,
                pass_completions=pss.pass_completions,
                pass_yards=pss.pass_yards,
                pass_touchdowns=pss.pass_touchdowns,
                interceptions=pss.interceptions,
                sacks_taken=pss.sacks_taken,
                sack_yards=pss.sack_yards,
                qb_hits=pss.qb_hits,
                pressures_faced=pss.pressures_faced,
                rush_attempts=pss.rush_attempts,
                rush_yards=pss.rush_yards,
                rush_touchdowns=pss.rush_touchdowns,
                fumbles=pss.fumbles,
                fumbles_lost=pss.fumbles_lost,
                targets=pss.targets,
                receptions=pss.receptions,
                receiving_yards=pss.receiving_yards,
                receiving_touchdowns=pss.receiving_touchdowns,
                drops=pss.drops,
                yards_after_catch=pss.yards_after_catch,
                tackles=pss.tackles,
                tackles_for_loss=pss.tackles_for_loss,
                sacks=pss.sacks,
                quarterback_hits=pss.quarterback_hits,
                pressures=pss.pressures,
                pass_deflections=pss.pass_deflections,
                interceptions_caught=pss.interceptions_caught,
                forced_fumbles=pss.forced_fumbles,
                fumble_recoveries=pss.fumble_recoveries,
                targets_against=pss.targets_against,
                completions_allowed=pss.completions_allowed,
                yards_allowed=pss.yards_allowed,
                touchdowns_allowed=pss.touchdowns_allowed,
                passes_defended=pss.passes_defended,
                field_goals_made=pss.field_goals_made,
                field_goals_attempted=pss.field_goals_attempted,
                extra_points_made=pss.extra_points_made,
                extra_points_attempted=pss.extra_points_attempted,
                punts=pss.punts,
                punt_yards=pss.punt_yards,
                punt_net_yards=pss.punt_net_yards,
                punts_in_20=pss.punts_in_20,
                kickoff_returns=pss.kickoff_returns,
                kickoff_return_yards=pss.kickoff_return_yards,
                punt_returns=pss.punt_returns,
                punt_return_yards=pss.punt_return_yards,
                sacks_allowed=pss.sacks_allowed,
                pressures_allowed=pss.pressures_allowed,
                qb_hits_allowed=pss.qb_hits_allowed,
                third_down_conversions=pss.third_down_conversions,
                third_down_attempts=pss.third_down_attempts,
                fourth_down_conversions=pss.fourth_down_conversions,
                fourth_down_attempts=pss.fourth_down_attempts,
                red_zone_touchdowns=pss.red_zone_touchdowns,
                red_zone_attempts=pss.red_zone_attempts,
                goal_to_go_touchdowns=pss.goal_to_go_touchdowns,
                goal_to_go_attempts=pss.goal_to_go_attempts,
                two_minute_touchdowns=pss.two_minute_touchdowns,
                two_minute_attempts=pss.two_minute_attempts
            ))
    
    return result


def get_team_season_lines(year: int, conference: Optional[str] = None,
                         division: Optional[str] = None, split: Optional[str] = None,
                         session: Session = None) -> List[TeamSeasonLineDTO]:
    """Get team season stat lines with filtering."""
    
    query = select(TeamSeasonStats).where(TeamSeasonStats.season == year)
    
    if conference:
        # Would need to join with Team table to filter by conference
        pass
    
    if division:
        # Would need to join with Team table to filter by division
        pass
    
    team_season_stats = session.exec(query).all()
    
    # Convert to DTOs
    result = []
    for tss in team_season_stats:
        team = session.exec(select(Team).where(Team.id == tss.team_id)).first()
        
        if team:
            result.append(TeamSeasonLineDTO(
                team_id=tss.team_id,
                team_name=team.name,
                season=year,
                games_played=tss.games_played,
                wins=tss.wins,
                losses=tss.losses,
                ties=tss.ties,
                total_yards=tss.total_yards,
                passing_yards=tss.passing_yards,
                rushing_yards=tss.rushing_yards,
                points_scored=tss.points_scored,
                turnovers_committed=tss.turnovers_committed,
                yards_allowed=tss.yards_allowed,
                passing_yards_allowed=tss.passing_yards_allowed,
                rushing_yards_allowed=tss.rushing_yards_allowed,
                points_allowed=tss.points_allowed,
                turnovers_forced=tss.turnovers_forced,
                field_goals_made=tss.field_goals_made,
                field_goals_attempted=tss.field_goals_attempted,
                punts=tss.punts,
                punt_net_yards=tss.punt_net_yards,
                punts_in_20=tss.punts_in_20,
                third_down_conversions=tss.third_down_conversions,
                third_down_attempts=tss.third_down_attempts,
                fourth_down_conversions=tss.fourth_down_conversions,
                fourth_down_attempts=tss.fourth_down_attempts,
                red_zone_touchdowns=tss.red_zone_touchdowns,
                red_zone_attempts=tss.red_zone_attempts
            ))
    
    return result


def _get_player_game_stats(game_id: int, team_id: int, session: Session) -> List[PlayerStatLine]:
    """Get player game stats for a team."""
    player_stats = session.exec(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game_id,
            PlayerGameStats.team_id == team_id
        )
    ).all()
    
    result = []
    for ps in player_stats:
        player = session.exec(select(Player).where(Player.id == ps.player_id)).first()
        team = session.exec(select(Team).where(Team.id == ps.team_id)).first()
        
        if player and team:
            result.append(PlayerStatLine(
                player_id=ps.player_id,
                player_name=player.name,
                position=player.position,
                team_id=ps.team_id,
                team_name=team.name,
                snaps_offense=ps.snaps_offense,
                snaps_defense=ps.snaps_defense,
                snaps_special_teams=ps.snaps_special_teams,
                pass_attempts=ps.pass_attempts,
                pass_completions=ps.pass_completions,
                pass_yards=ps.pass_yards,
                pass_touchdowns=ps.pass_touchdowns,
                interceptions=ps.interceptions,
                sacks_taken=ps.sacks_taken,
                sack_yards=ps.sack_yards,
                qb_hits=ps.qb_hits,
                pressures_faced=ps.pressures_faced,
                rush_attempts=ps.rush_attempts,
                rush_yards=ps.rush_yards,
                rush_touchdowns=ps.rush_touchdowns,
                fumbles=ps.fumbles,
                fumbles_lost=ps.fumbles_lost,
                targets=ps.targets,
                receptions=ps.receptions,
                receiving_yards=ps.receiving_yards,
                receiving_touchdowns=ps.receiving_touchdowns,
                drops=ps.drops,
                yards_after_catch=ps.yards_after_catch,
                tackles=ps.tackles,
                tackles_for_loss=ps.tackles_for_loss,
                sacks=ps.sacks,
                quarterback_hits=ps.quarterback_hits,
                pressures=ps.pressures,
                pass_deflections=ps.pass_deflections,
                interceptions_caught=ps.interceptions_caught,
                forced_fumbles=ps.forced_fumbles,
                fumble_recoveries=ps.fumble_recoveries,
                targets_against=ps.targets_against,
                completions_allowed=ps.completions_allowed,
                yards_allowed=ps.yards_allowed,
                touchdowns_allowed=ps.touchdowns_allowed,
                passes_defended=ps.passes_defended,
                field_goals_made=ps.field_goals_made,
                field_goals_attempted=ps.field_goals_attempted,
                extra_points_made=ps.extra_points_made,
                extra_points_attempted=ps.extra_points_attempted,
                punts=ps.punts,
                punt_yards=ps.punt_yards,
                punt_net_yards=ps.punt_net_yards,
                punts_in_20=ps.punts_in_20,
                kickoff_returns=ps.kickoff_returns,
                kickoff_return_yards=ps.kickoff_return_yards,
                punt_returns=ps.punt_returns,
                punt_return_yards=ps.punt_return_yards,
                sacks_allowed=ps.sacks_allowed,
                pressures_allowed=ps.pressures_allowed,
                qb_hits_allowed=ps.qb_hits_allowed,
                third_down_conversions=ps.third_down_conversions,
                third_down_attempts=ps.third_down_attempts,
                fourth_down_conversions=ps.fourth_down_conversions,
                fourth_down_attempts=ps.fourth_down_attempts,
                red_zone_touchdowns=ps.red_zone_touchdowns,
                red_zone_attempts=ps.red_zone_attempts,
                goal_to_go_touchdowns=ps.goal_to_go_touchdowns,
                goal_to_go_attempts=ps.goal_to_go_attempts,
                two_minute_touchdowns=ps.two_minute_touchdowns,
                two_minute_attempts=ps.two_minute_attempts
            ))
    
    return result


def _convert_team_stats(team_stats: TeamGameStats, team_name: str) -> TeamStatLine:
    """Convert TeamGameStats to TeamStatLine DTO."""
    if not team_stats:
        return TeamStatLine(
            team_id=0,
            team_name=team_name,
            games_played=0
        )
    
    return TeamStatLine(
        team_id=team_stats.team_id,
        team_name=team_name,
        games_played=1,  # Single game
        wins=1 if team_stats.points_scored > 0 else 0,  # Simplified
        losses=0,
        ties=0,
        total_yards=team_stats.total_yards,
        passing_yards=team_stats.passing_yards,
        rushing_yards=team_stats.rushing_yards,
        points_scored=team_stats.points_scored,
        turnovers_committed=team_stats.turnovers_committed,
        field_goals_made=team_stats.field_goals_made,
        field_goals_attempted=team_stats.field_goals_attempted,
        punts=team_stats.punts,
        punt_net_yards=team_stats.punt_net_yards,
        punts_in_20=team_stats.punts_in_20,
        third_down_conversions=team_stats.third_down_conversions,
        third_down_attempts=team_stats.third_down_attempts,
        fourth_down_conversions=team_stats.fourth_down_conversions,
        fourth_down_attempts=team_stats.fourth_down_attempts,
        red_zone_touchdowns=team_stats.red_zone_touchdowns,
        red_zone_attempts=team_stats.red_zone_attempts
    )


def _get_passing_leaders(year: Optional[int], stat: str, top: int, split: Optional[str],
                        role: Optional[str], scope: str, session: Session) -> List[LeaderEntry]:
    """Get passing leaders."""
    # Simplified implementation
    return []


def _get_rushing_leaders(year: Optional[int], stat: str, top: int, split: Optional[str],
                        role: Optional[str], scope: str, session: Session) -> List[LeaderEntry]:
    """Get rushing leaders."""
    # Simplified implementation
    return []


def _get_receiving_leaders(year: Optional[int], stat: str, top: int, split: Optional[str],
                          role: Optional[str], scope: str, session: Session) -> List[LeaderEntry]:
    """Get receiving leaders."""
    # Simplified implementation
    return []


def _get_defensive_leaders(year: Optional[int], stat: str, top: int, split: Optional[str],
                          role: Optional[str], scope: str, session: Session) -> List[LeaderEntry]:
    """Get defensive leaders."""
    # Simplified implementation
    return []


def _get_special_teams_leaders(year: Optional[int], stat: str, top: int, split: Optional[str],
                              role: Optional[str], scope: str, session: Session) -> List[LeaderEntry]:
    """Get special teams leaders."""
    # Simplified implementation
    return []
