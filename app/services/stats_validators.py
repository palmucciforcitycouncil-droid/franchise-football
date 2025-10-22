"""
Advanced Stats Validators

Validates data invariants and consistency for the GDD v3.2 Stat Catalog fields.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
import math
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.stats import PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats, PlayerCareerStats
from app.models.sim_models import GameEvent, Game
import json
import logging

logger = logging.getLogger(__name__)

class ValidationResult:
    """Container for validation results."""
    
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
    
    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def __str__(self) -> str:
        result = f"Validation Result: {'PASS' if self.is_valid else 'FAIL'}\n"
        if self.errors:
            result += "Errors:\n" + "\n".join(f"  - {error}" for error in self.errors)
        if self.warnings:
            result += "Warnings:\n" + "\n".join(f"  - {warning}" for warning in self.warnings)
        return result

def validate_game_stats(s: Session, game_id: int) -> ValidationResult:
    """Validate stats for a specific game."""
    
    result = ValidationResult()
    
    try:
        # Get game info
        game = s.exec(select(Game).where(Game.id == game_id)).first()
        if not game:
            result.add_error(f"Game {game_id} not found")
            return result
        
        # Get team stats
        team_stats = s.exec(
            select(TeamGameStats).where(TeamGameStats.game_id == game_id)
        ).all()
        
        if len(team_stats) != 2:
            result.add_error(f"Expected 2 team stats records, found {len(team_stats)}")
            return result
        
        # Get player stats
        player_stats = s.exec(
            select(PlayerGameStats).where(PlayerGameStats.game_id == game_id)
        ).all()
        
        # Validate team stats
        for team_stat in team_stats:
            _validate_team_game_stats(team_stat, result)
        
        # Validate team vs team consistency
        if len(team_stats) == 2:
            _validate_team_vs_team_consistency(team_stats[0], team_stats[1], result)
        
        # Validate player stats sum to team stats
        _validate_player_sum_to_team(s, game_id, result)
        
        # Validate PBP consistency
        _validate_pbp_consistency(s, game_id, result)
        
    except Exception as e:
        result.add_error(f"Error validating game {game_id}: {e}")
    
    return result

def validate_season_stats(s: Session, season: int) -> ValidationResult:
    """Validate stats for an entire season."""
    
    result = ValidationResult()
    
    try:
        # Get all games for the season
        games = s.exec(select(Game).where(Game.season == season)).all()
        
        if not games:
            result.add_error(f"No games found for season {season}")
            return result
        
        # Validate each game
        for game in games:
            game_result = validate_game_stats(s, game.id)
            if not game_result.is_valid:
                result.add_error(f"Game {game.id} validation failed: {game_result.errors}")
        
        # Validate season totals
        _validate_season_totals(s, season, result)
        
    except Exception as e:
        result.add_error(f"Error validating season {season}: {e}")
    
    return result

def _validate_team_game_stats(team_stat: TeamGameStats, result: ValidationResult) -> None:
    """Validate individual team game stats."""
    
    # Basic consistency checks
    if team_stat.pass_attempts < team_stat.pass_completions:
        result.add_error(f"Team {team_stat.team_id}: Pass completions ({team_stat.pass_completions}) > attempts ({team_stat.pass_attempts})")
    
    if team_stat.pass_attempts < team_stat.pass_int:
        result.add_error(f"Team {team_stat.team_id}: Pass interceptions ({team_stat.pass_int}) > attempts ({team_stat.pass_attempts})")
    
    if team_stat.rush_attempts < 0:
        result.add_error(f"Team {team_stat.team_id}: Negative rush attempts ({team_stat.rush_attempts})")
    
    if team_stat.total_yards != team_stat.pass_yards + team_stat.rush_yards:
        result.add_warning(f"Team {team_stat.team_id}: Total yards ({team_stat.total_yards}) != pass ({team_stat.pass_yards}) + rush ({team_stat.rush_yards})")
    
    # GDD v3.2 Stat Catalog specific validations
    
    # Sack share validation
    if team_stat.sacks > 0 and team_stat.sacks_allowed > 0:
        result.add_warning(f"Team {team_stat.team_id}: Both sacks ({team_stat.sacks}) and sacks allowed ({team_stat.sacks_allowed}) > 0")
    
    # Coverage consistency
    if team_stat.targets_faced < team_stat.completions_allowed:
        result.add_error(f"Team {team_stat.team_id}: Completions allowed ({team_stat.completions_allowed}) > targets faced ({team_stat.targets_faced})")
    
    if team_stat.targets_faced < team_stat.pbus:
        result.add_error(f"Team {team_stat.team_id}: PBUs ({team_stat.pbus}) > targets faced ({team_stat.targets_faced})")
    
    # Situational splits consistency
    if team_stat.third_down_attempts < team_stat.third_down_conversions:
        result.add_error(f"Team {team_stat.team_id}: Third down conversions ({team_stat.third_down_conversions}) > attempts ({team_stat.third_down_attempts})")
    
    if team_stat.fourth_down_attempts < team_stat.fourth_down_conversions:
        result.add_error(f"Team {team_stat.team_id}: Fourth down conversions ({team_stat.fourth_down_conversions}) > attempts ({team_stat.fourth_down_attempts})")
    
    if team_stat.red_zone_attempts < team_stat.red_zone_td:
        result.add_error(f"Team {team_stat.team_id}: Red zone TDs ({team_stat.red_zone_td}) > attempts ({team_stat.red_zone_attempts})")
    
    if team_stat.goal_to_go_attempts < team_stat.goal_to_go_td:
        result.add_error(f"Team {team_stat.team_id}: Goal-to-go TDs ({team_stat.goal_to_go_td}) > attempts ({team_stat.goal_to_go_attempts})")
    
    # Special teams consistency
    if team_stat.punts > 0 and team_stat.punt_yards == 0:
        result.add_warning(f"Team {team_stat.team_id}: Punts ({team_stat.punts}) > 0 but punt yards = 0")
    
    if team_stat.punts_in_20 > team_stat.punts:
        result.add_error(f"Team {team_stat.team_id}: Punts in 20 ({team_stat.punts_in_20}) > total punts ({team_stat.punts})")
    
    # Kicking consistency
    if team_stat.fg_attempts < team_stat.fg_made:
        result.add_error(f"Team {team_stat.team_id}: FGs made ({team_stat.fg_made}) > attempts ({team_stat.fg_attempts})")
    
    if team_stat.xp_attempts < team_stat.xp_made:
        result.add_error(f"Team {team_stat.team_id}: XPs made ({team_stat.xp_made}) > attempts ({team_stat.xp_attempts})")

def _validate_team_vs_team_consistency(team1: TeamGameStats, team2: TeamGameStats, result: ValidationResult) -> None:
    """Validate consistency between opposing teams."""
    
    # Sacks: team1 sacks should equal team2 sacks_allowed
    if not math.isclose(team1.sacks, team2.sacks_allowed, rel_tol=0.1):
        result.add_warning(f"Sack mismatch: Team {team1.team_id} sacks ({team1.sacks}) != Team {team2.team_id} sacks allowed ({team2.sacks_allowed})")
    
    # Pressures: team1 pressures should equal team2 pressures_allowed
    if team1.pressures != team2.pressures_allowed:
        result.add_warning(f"Pressure mismatch: Team {team1.team_id} pressures ({team1.pressures}) != Team {team2.team_id} pressures allowed ({team2.pressures_allowed})")
    
    # QB hits: team1 qb_hits should equal team2 qb_hits_allowed
    if team1.qb_hits != team2.qb_hits_allowed:
        result.add_warning(f"QB hit mismatch: Team {team1.team_id} qb_hits ({team1.qb_hits}) != Team {team2.team_id} qb_hits_allowed ({team2.qb_hits_allowed})")
    
    # Coverage: team1 targets_faced should equal team2 pass_attempts
    if team1.targets_faced != team2.pass_attempts:
        result.add_warning(f"Target mismatch: Team {team1.team_id} targets faced ({team1.targets_faced}) != Team {team2.team_id} pass attempts ({team2.pass_attempts})")
    
    # Completions: team1 completions_allowed should equal team2 pass_completions
    if team1.completions_allowed != team2.pass_completions:
        result.add_warning(f"Completion mismatch: Team {team1.team_id} completions allowed ({team1.completions_allowed}) != Team {team2.team_id} pass completions ({team2.pass_completions})")
    
    # Yards: team1 yards_allowed should equal team2 pass_yards
    if team1.yards_allowed != team2.pass_yards:
        result.add_warning(f"Yard mismatch: Team {team1.team_id} yards allowed ({team1.yards_allowed}) != Team {team2.team_id} pass yards ({team2.pass_yards})")

def _validate_player_sum_to_team(s: Session, game_id: int, result: ValidationResult) -> None:
    """Validate that player stats sum to team stats."""
    
    # Get team stats
    team_stats = s.exec(
        select(TeamGameStats).where(TeamGameStats.game_id == game_id)
    ).all()
    
    # Get player stats grouped by team
    player_stats = s.exec(
        select(PlayerGameStats).where(PlayerGameStats.game_id == game_id)
    ).all()
    
    for team_stat in team_stats:
        team_players = [p for p in player_stats if p.team_id == team_stat.team_id]
        
        if not team_players:
            result.add_warning(f"No player stats found for team {team_stat.team_id}")
            continue
        
        # Sum player stats
        player_totals = {
            "pass_attempts": sum(p.pass_attempts for p in team_players),
            "pass_completions": sum(p.pass_completions for p in team_players),
            "pass_yards": sum(p.pass_yards for p in team_players),
            "pass_td": sum(p.pass_td for p in team_players),
            "pass_int": sum(p.pass_int for p in team_players),
            "rush_attempts": sum(p.rush_attempts for p in team_players),
            "rush_yards": sum(p.rush_yards for p in team_players),
            "rush_td": sum(p.rush_td for p in team_players),
            "tackles_solo": sum(p.tackles_solo for p in team_players),
            "tackles_assist": sum(p.tackles_assist for p in team_players),
            "sacks": sum(p.sacks_defense for p in team_players),
            "interceptions": sum(p.interceptions for p in team_players),
            "pbus": sum(p.pbus for p in team_players),
        }
        
        # Compare with team stats
        for stat_name, player_total in player_totals.items():
            team_value = getattr(team_stat, stat_name, 0)
            if not math.isclose(player_total, team_value, rel_tol=0.1):
                result.add_warning(f"Team {team_stat.team_id} {stat_name}: Players sum ({player_total}) != Team ({team_value})")

def _validate_pbp_consistency(s: Session, game_id: int, result: ValidationResult) -> None:
    """Validate PBP events against aggregated stats."""
    
    # Get all events for the game
    events = s.exec(
        select(GameEvent).where(GameEvent.game_id == game_id)
    ).all()
    
    if not events:
        result.add_warning(f"No PBP events found for game {game_id}")
        return
    
    # Count events by type
    event_counts = {}
    for event in events:
        event_type = event.event_type
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    # Get team stats
    team_stats = s.exec(
        select(TeamGameStats).where(TeamGameStats.game_id == game_id)
    ).all()
    
    if len(team_stats) != 2:
        return
    
    # Validate event counts against stats
    total_punts = sum(ts.punts for ts in team_stats)
    total_turnovers = sum(ts.turnovers for ts in team_stats)
    total_fg_attempts = sum(ts.fg_attempts for ts in team_stats)
    
    if event_counts.get("punt", 0) != total_punts:
        result.add_warning(f"PBP punt events ({event_counts.get('punt', 0)}) != team punt stats ({total_punts})")
    
    if event_counts.get("turnover", 0) != total_turnovers:
        result.add_warning(f"PBP turnover events ({event_counts.get('turnover', 0)}) != team turnover stats ({total_turnovers})")
    
    if event_counts.get("fg", 0) != total_fg_attempts:
        result.add_warning(f"PBP FG events ({event_counts.get('fg', 0)}) != team FG attempts ({total_fg_attempts})")

def _validate_season_totals(s: Session, season: int, result: ValidationResult) -> None:
    """Validate season totals consistency."""
    
    # Get all team season stats
    season_stats = s.exec(
        select(TeamSeasonStats).where(TeamSeasonStats.season == season)
    ).all()
    
    if not season_stats:
        result.add_warning(f"No season stats found for season {season}")
        return
    
    # Get all team game stats for the season
    games = s.exec(select(Game).where(Game.season == season)).all()
    game_ids = [g.id for g in games]
    
    game_stats = s.exec(
        select(TeamGameStats).where(TeamGameStats.game_id.in_(game_ids))
    ).all()
    
    # Group game stats by team
    game_stats_by_team = {}
    for gs in game_stats:
        team_id = gs.team_id
        if team_id not in game_stats_by_team:
            game_stats_by_team[team_id] = []
        game_stats_by_team[team_id].append(gs)
    
    # Validate season totals
    for season_stat in season_stats:
        team_id = season_stat.team_id
        team_games = game_stats_by_team.get(team_id, [])
        
        if not team_games:
            result.add_warning(f"No game stats found for team {team_id} in season {season}")
            continue
        
        # Sum game stats
        game_totals = {
            "gp": len(team_games),
            "pass_attempts": sum(gs.pass_attempts for gs in team_games),
            "pass_completions": sum(gs.pass_completions for gs in team_games),
            "pass_yards": sum(gs.pass_yards for gs in team_games),
            "pass_td": sum(gs.pass_td for gs in team_games),
            "pass_int": sum(gs.pass_int for gs in team_games),
            "rush_attempts": sum(gs.rush_attempts for gs in team_games),
            "rush_yards": sum(gs.rush_yards for gs in team_games),
            "rush_td": sum(gs.rush_td for gs in team_games),
            "total_yards": sum(gs.total_yards for gs in team_games),
            "total_td": sum(gs.total_td for gs in team_games),
            "turnovers": sum(gs.turnovers for gs in team_games),
            "punts": sum(gs.punts for gs in team_games),
            "fg_attempts": sum(gs.fg_attempts for gs in team_games),
            "fg_made": sum(gs.fg_made for gs in team_games),
        }
        
        # Compare with season stats
        for stat_name, game_total in game_totals.items():
            season_value = getattr(season_stat, stat_name, 0)
            if not math.isclose(game_total, season_value, rel_tol=0.1):
                result.add_warning(f"Team {team_id} season {stat_name}: Games sum ({game_total}) != Season ({season_value})")

def validate_sack_shares(s: Session, game_id: int) -> ValidationResult:
    """Validate that sack shares sum to approximately 1.0."""
    
    result = ValidationResult()
    
    try:
        # Get all play events for the game
        events = s.exec(
            select(GameEvent).where(
                GameEvent.game_id == game_id,
                GameEvent.event_type == "play"
            )
        ).all()
        
        for event in events:
            try:
                if event.data_json:
                    payload = json.loads(event.data_json)
                elif event.description:
                    payload = json.loads(event.description)
                else:
                    continue
                
                sack_split = payload.get("sack_split", [])
                if sack_split:
                    total_share = sum(share for _, share in sack_split)
                    if not math.isclose(total_share, 1.0, rel_tol=0.01):
                        result.add_error(f"Event {event.id}: Sack split shares sum to {total_share:.3f}, expected ~1.0")
                
            except Exception as e:
                result.add_warning(f"Error processing event {event.id}: {e}")
    
    except Exception as e:
        result.add_error(f"Error validating sack shares for game {game_id}: {e}")
    
    return result

def validate_coverage_consistency(s: Session, game_id: int) -> ValidationResult:
    """Validate coverage stats consistency."""
    
    result = ValidationResult()
    
    try:
        # Get all play events for the game
        events = s.exec(
            select(GameEvent).where(
                GameEvent.game_id == game_id,
                GameEvent.event_type == "play"
            )
        ).all()
        
        coverage_stats = {
            "targets": 0,
            "completions": 0,
            "incompletions": 0,
            "interceptions": 0,
            "pbus": 0,
        }
        
        for event in events:
            try:
                if event.data_json:
                    payload = json.loads(event.data_json)
                elif event.description:
                    payload = json.loads(event.description)
                else:
                    continue
                
                if payload.get("play") == "pass":
                    coverage_stats["targets"] += 1
                    
                    if payload.get("complete", False):
                        coverage_stats["completions"] += 1
                    else:
                        coverage_stats["incompletions"] += 1
                    
                    if payload.get("interception", False):
                        coverage_stats["interceptions"] += 1
                    
                    if payload.get("is_pd", False):
                        coverage_stats["pbus"] += 1
                
            except Exception as e:
                result.add_warning(f"Error processing event {event.id}: {e}")
        
        # Validate consistency
        total_outcomes = coverage_stats["completions"] + coverage_stats["incompletions"] + coverage_stats["interceptions"]
        if coverage_stats["targets"] != total_outcomes:
            result.add_warning(f"Coverage targets ({coverage_stats['targets']}) != total outcomes ({total_outcomes})")
        
        if coverage_stats["pbus"] > coverage_stats["incompletions"]:
            result.add_warning(f"PBUs ({coverage_stats['pbus']}) > incompletions ({coverage_stats['incompletions']})")
    
    except Exception as e:
        result.add_error(f"Error validating coverage consistency for game {game_id}: {e}")
    
    return result
