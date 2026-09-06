# app/services/stats/season_agg.py
from __future__ import annotations
from typing import Iterable, Dict, Tuple
from sqlmodel import Session, select, delete
from app.models.stats_models import TeamSeasonStats, PlayerSeasonStats, TeamGameStats, PlayerGameStats
from app.models.core_min import Player, Game

def _season_for_teamgame(tg: TeamGameStats) -> int:
    """Get season for TeamGameStats - prefer direct field, else via Game relationship."""
    return getattr(tg, "season", None) or getattr(tg.game, "season", 2025)

def _season_for_playergame(pg: PlayerGameStats) -> int:
    """Get season for PlayerGameStats - prefer direct field, else via Game relationship."""
    return getattr(pg, "season", None) or getattr(pg.game, "season", 2025)

def aggregate_team_season(session: Session, season: int) -> None:
    """Rebuild TeamSeasonStats for a season from TeamGameStats rows."""
    # Delete existing season stats for this season
    session.exec(delete(TeamSeasonStats).where(TeamSeasonStats.season == season))
    
    # Get all team game stats for this season
    # Since TeamGameStats doesn't have a direct relationship to Game, we'll get all and filter
    rows: Iterable[TeamGameStats] = session.exec(select(TeamGameStats))
    
    # Filter by season by checking the game_id against Game table
    filtered_rows = []
    for tg in rows:
        try:
            game = session.exec(select(Game).where(Game.id == tg.game_id)).first()
            if game and game.season == season:
                filtered_rows.append(tg)
        except Exception:
            # If we can't find the game, skip this row
            continue

    buckets: Dict[Tuple[int, int], TeamSeasonStats] = {}
    for tg in filtered_rows:
        s = season
        key = (tg.team_id, s)
        if key not in buckets:
            buckets[key] = TeamSeasonStats(team_id=tg.team_id, season=s)
        agg = buckets[key]
        
        # Aggregate game-level stats
        agg.games_played += 1
        agg.points_scored += getattr(tg, "points_scored", 0)
        agg.points_allowed += getattr(tg, "points_allowed", 0)  # TODO: calculate from opponent
        agg.total_yards += getattr(tg, "total_yards", 0)
        agg.passing_yards += getattr(tg, "passing_yards", 0)
        agg.rushing_yards += getattr(tg, "rushing_yards", 0)
        agg.turnovers_committed += getattr(tg, "turnovers_committed", 0)
        agg.turnovers_forced += getattr(tg, "turnovers_forced", 0)
        
        # Special teams
        agg.field_goals_made += getattr(tg, "field_goals_made", 0)
        agg.field_goals_attempted += getattr(tg, "field_goals_attempted", 0)
        agg.punts += getattr(tg, "punts", 0)
        agg.punt_net_yards += getattr(tg, "punt_net_yards", 0)
        agg.punts_in_20 += getattr(tg, "punts_in_20", 0)
        
        # Situational splits
        agg.third_down_conversions += getattr(tg, "third_down_conversions", 0)
        agg.third_down_attempts += getattr(tg, "third_down_attempts", 0)
        agg.fourth_down_conversions += getattr(tg, "fourth_down_conversions", 0)
        agg.fourth_down_attempts += getattr(tg, "fourth_down_attempts", 0)
        agg.red_zone_touchdowns += getattr(tg, "red_zone_touchdowns", 0)
        agg.red_zone_attempts += getattr(tg, "red_zone_attempts", 0)
        
        # W-L-T (simplified - would need game result logic)
        # TODO: Implement proper win/loss calculation from game results

    for obj in buckets.values():
        session.add(obj)
    session.commit()

def aggregate_player_season(session: Session, season: int) -> None:
    """Rebuild PlayerSeasonStats for a season from PlayerGameStats rows."""
    # Delete existing season stats for this season
    session.exec(delete(PlayerSeasonStats).where(PlayerSeasonStats.season == season))
    
    # Get all player game stats for this season
    # Since PlayerGameStats doesn't have a direct relationship to Game, we'll get all and filter
    rows: Iterable[PlayerGameStats] = session.exec(select(PlayerGameStats))
    
    # Filter by season by checking the game_id against Game table
    filtered_rows = []
    for pg in rows:
        try:
            game = session.exec(select(Game).where(Game.id == pg.game_id)).first()
            if game and game.season == season:
                filtered_rows.append(pg)
        except Exception:
            # If we can't find the game, skip this row
            continue

    buckets: Dict[Tuple[int, int], PlayerSeasonStats] = {}
    for pg in filtered_rows:
        s = season
        key = (pg.player_id, s)
        if key not in buckets:
            buckets[key] = PlayerSeasonStats(
                player_id=pg.player_id, 
                team_id=pg.team_id, 
                season=s
            )
        agg = buckets[key]
        
        # Aggregate game-level stats
        agg.games_played += 1
        agg.snaps_offense += getattr(pg, "snaps_offense", 0)
        agg.snaps_defense += getattr(pg, "snaps_defense", 0)
        agg.snaps_special_teams += getattr(pg, "snaps_special_teams", 0)

        # Passing stats
        agg.pass_attempts += getattr(pg, "pass_attempts", 0)
        agg.pass_completions += getattr(pg, "pass_completions", 0)
        agg.pass_yards += getattr(pg, "pass_yards", 0)
        agg.pass_touchdowns += getattr(pg, "pass_touchdowns", 0)
        agg.interceptions += getattr(pg, "interceptions", 0)
        agg.sacks_taken += getattr(pg, "sacks_taken", 0.0)
        agg.sack_yards += getattr(pg, "sack_yards", 0)
        agg.qb_hits += getattr(pg, "qb_hits", 0)
        agg.pressures_faced += getattr(pg, "pressures_faced", 0)

        # Rushing stats
        agg.rush_attempts += getattr(pg, "rush_attempts", 0)
        agg.rush_yards += getattr(pg, "rush_yards", 0)
        agg.rush_touchdowns += getattr(pg, "rush_touchdowns", 0)
        agg.fumbles += getattr(pg, "fumbles", 0)
        agg.fumbles_lost += getattr(pg, "fumbles_lost", 0)

        # Receiving stats
        agg.targets += getattr(pg, "targets", 0)
        agg.receptions += getattr(pg, "receptions", 0)
        agg.receiving_yards += getattr(pg, "receiving_yards", 0)
        agg.receiving_touchdowns += getattr(pg, "receiving_touchdowns", 0)
        agg.drops += getattr(pg, "drops", 0)
        agg.yards_after_catch += getattr(pg, "yards_after_catch", 0)

        # Defensive stats
        agg.tackles += getattr(pg, "tackles", 0)
        agg.tackles_for_loss += getattr(pg, "tackles_for_loss", 0)
        agg.sacks += getattr(pg, "sacks", 0.0)
        agg.quarterback_hits += getattr(pg, "quarterback_hits", 0)
        agg.pressures += getattr(pg, "pressures", 0)
        agg.pass_deflections += getattr(pg, "pass_deflections", 0)
        agg.interceptions_caught += getattr(pg, "interceptions_caught", 0)
        agg.forced_fumbles += getattr(pg, "forced_fumbles", 0)
        agg.fumble_recoveries += getattr(pg, "fumble_recoveries", 0)

        # Coverage stats
        agg.targets_against += getattr(pg, "targets_against", 0)
        agg.completions_allowed += getattr(pg, "completions_allowed", 0)
        agg.yards_allowed += getattr(pg, "yards_allowed", 0)
        agg.touchdowns_allowed += getattr(pg, "touchdowns_allowed", 0)
        agg.passes_defended += getattr(pg, "passes_defended", 0)

        # Special Teams stats
        agg.field_goals_made += getattr(pg, "field_goals_made", 0)
        agg.field_goals_attempted += getattr(pg, "field_goals_attempted", 0)
        agg.extra_points_made += getattr(pg, "extra_points_made", 0)
        agg.extra_points_attempted += getattr(pg, "extra_points_attempted", 0)
        agg.punts += getattr(pg, "punts", 0)
        agg.punt_yards += getattr(pg, "punt_yards", 0)
        agg.punt_net_yards += getattr(pg, "punt_net_yards", 0)
        agg.punts_in_20 += getattr(pg, "punts_in_20", 0)
        agg.kickoff_returns += getattr(pg, "kickoff_returns", 0)
        agg.kickoff_return_yards += getattr(pg, "kickoff_return_yards", 0)
        agg.punt_returns += getattr(pg, "punt_returns", 0)
        agg.punt_return_yards += getattr(pg, "punt_return_yards", 0)

        # Advanced OL stats
        agg.sacks_allowed += getattr(pg, "sacks_allowed", 0.0)
        agg.pressures_allowed += getattr(pg, "pressures_allowed", 0)
        agg.qb_hits_allowed += getattr(pg, "qb_hits_allowed", 0)

        # Situational splits
        agg.third_down_conversions += getattr(pg, "third_down_conversions", 0)
        agg.third_down_attempts += getattr(pg, "third_down_attempts", 0)
        agg.fourth_down_conversions += getattr(pg, "fourth_down_conversions", 0)
        agg.fourth_down_attempts += getattr(pg, "fourth_down_attempts", 0)
        agg.red_zone_touchdowns += getattr(pg, "red_zone_touchdowns", 0)
        agg.red_zone_attempts += getattr(pg, "red_zone_attempts", 0)
        agg.goal_to_go_touchdowns += getattr(pg, "goal_to_go_touchdowns", 0)
        agg.goal_to_go_attempts += getattr(pg, "goal_to_go_attempts", 0)
        agg.two_minute_touchdowns += getattr(pg, "two_minute_touchdowns", 0)
        agg.two_minute_attempts += getattr(pg, "two_minute_attempts", 0)

    for obj in buckets.values():
        session.add(obj)
    session.commit()
