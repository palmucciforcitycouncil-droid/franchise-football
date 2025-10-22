from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, asc, and_
from app.core.db import get_session
from app.models.stats import (
    PlayerGameStats, TeamGameStats, 
    PlayerSeasonStats, TeamSeasonStats, PlayerCareerStats
)
from app.models.sim_models import Game, Team
from app.services.stats_rollup_ultra_simple import rollup_game_stats_ultra_simple, rollup_season_stats_ultra_simple
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["stats"])

# Response DTOs
class PlayerGameStatsResponse(BaseModel):
    """Player game statistics response"""
    player_id: int
    team_id: int
    game_id: int
    gp: bool
    gs: bool
    snaps_offense: int
    snaps_defense: int
    snaps_st: int
    
    # Passing stats
    pass_attempts: int
    pass_completions: int
    pass_yards: int
    pass_td: int
    pass_int: int
    sacks: float
    sack_yards: int
    qb_hits: int
    pressures: int
    
    # Rushing stats
    rush_attempts: int
    rush_yards: int
    rush_td: int
    broken_tackle: int
    
    # Receiving stats
    targets: int
    receptions: int
    receiving_yards: int
    receiving_td: int
    yac: int
    
    # Defense stats
    tackles_solo: int
    tackles_assist: int
    tfl: int
    sacks_defense: float
    qb_hits_defense: int
    pressures_defense: int
    interceptions: int
    int_yards: int
    int_td: int
    pbus: int
    forced_fumbles: int
    fumble_recoveries: int
    fr_yards: int
    fr_td: int
    
    # Special teams
    kickoffs: int
    kickoff_touchbacks: int
    punts: int
    punt_yards: int
    punts_in_20: int
    punt_touchbacks: int
    punt_returns: int
    punt_return_yards: int
    punt_return_td: int
    kickoff_returns: int
    kickoff_return_yards: int
    kickoff_return_td: int
    
    # Kicking
    fg_attempts: int
    fg_made: int
    fg_yards: int
    xp_attempts: int
    xp_made: int
    
    # Turnovers
    fumbles: int
    fumbles_lost: int
    
    # Penalties
    penalties: int
    penalty_yards: int
    
    # Advanced metrics
    epa: float
    success_rate: float
    explosives: int
    third_down_conversions: int
    third_down_attempts: int

class TeamGameStatsResponse(BaseModel):
    """Team game statistics response"""
    team_id: int
    game_id: int
    gp: bool
    snaps_offense: int
    snaps_defense: int
    snaps_st: int
    
    # Offensive stats
    pass_attempts: int
    pass_completions: int
    pass_yards: int
    pass_td: int
    pass_int: int
    sacks_allowed: float
    sack_yards_allowed: int
    qb_hits_allowed: int
    pressures_allowed: int
    
    rush_attempts: int
    rush_yards: int
    rush_td: int
    
    total_yards: int
    total_td: int
    turnovers: int
    
    # Defensive stats
    tackles_solo: int
    tackles_assist: int
    tfl: int
    sacks: float
    qb_hits: int
    pressures: int
    interceptions: int
    int_yards: int
    int_td: int
    pbus: int
    forced_fumbles: int
    fumble_recoveries: int
    fr_yards: int
    fr_td: int
    
    # Special teams
    kickoffs: int
    kickoff_touchbacks: int
    punts: int
    punt_yards: int
    punts_in_20: int
    punt_touchbacks: int
    punt_returns: int
    punt_return_yards: int
    punt_return_td: int
    kickoff_returns: int
    kickoff_return_yards: int
    kickoff_return_td: int
    
    # Kicking
    fg_attempts: int
    fg_made: int
    fg_yards: int
    xp_attempts: int
    xp_made: int
    
    # Penalties
    penalties: int
    penalty_yards: int
    
    # Advanced metrics
    epa: float
    success_rate: float
    explosives: int
    third_down_conversions: int
    third_down_attempts: int

class BoxScoreResponse(BaseModel):
    """Complete box score response"""
    game_id: int
    home_team: TeamGameStatsResponse
    away_team: TeamGameStatsResponse
    home_players: List[PlayerGameStatsResponse]
    away_players: List[PlayerGameStatsResponse]

class LeaderResponse(BaseModel):
    """Statistical leader response"""
    player_id: int
    team_id: int
    team_name: str
    stat_value: float
    games_played: int

@router.get("/games/{game_id}", response_model=BoxScoreResponse)
def get_game_box_score(game_id: int, s: Session = Depends(get_session)):
    """Get complete box score for a game"""
    
    # Get game info
    game = s.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    # Get team stats
    team_stats = s.exec(
        select(TeamGameStats).where(TeamGameStats.game_id == game_id)
    ).all()
    
    if len(team_stats) != 2:
        raise HTTPException(status_code=404, detail=f"Team stats not found for game {game_id}")
    
    home_team_stat = next((ts for ts in team_stats if ts.team_id == game.home_team_id), None)
    away_team_stat = next((ts for ts in team_stats if ts.team_id == game.away_team_id), None)
    
    if not home_team_stat or not away_team_stat:
        raise HTTPException(status_code=404, detail="Missing team stats")
    
    # Get player stats
    player_stats = s.exec(
        select(PlayerGameStats).where(PlayerGameStats.game_id == game_id)
    ).all()
    
    home_player_stats = [ps for ps in player_stats if ps.team_id == game.home_team_id]
    away_player_stats = [ps for ps in player_stats if ps.team_id == game.away_team_id]
    
    return BoxScoreResponse(
        game_id=game_id,
        home_team=TeamGameStatsResponse(**home_team_stat.__dict__),
        away_team=TeamGameStatsResponse(**away_team_stat.__dict__),
        home_players=[PlayerGameStatsResponse(**ps.__dict__) for ps in home_player_stats],
        away_players=[PlayerGameStatsResponse(**ps.__dict__) for ps in away_player_stats]
    )

@router.get("/leaders")
def get_statistical_leaders(
    year: int = Query(..., description="Season year"),
    stat: str = Query(..., description="Statistic name"),
    top: int = Query(10, ge=1, le=100, description="Number of leaders to return"),
    split: str = Query("regular", description="regular|playoffs|both|third_down|red_zone|goal_to_go|two_minute"),
    role: str = Query("all", description="all|ol|dl|db|st|qb|rb|wr|te"),
    s: Session = Depends(get_session)
):
    """Get statistical leaders for a given season"""
    
    # Map stat names to database fields (including GDD v3.2 advanced fields)
    stat_fields = {
        # Basic offensive stats
        "pass_yards": PlayerSeasonStats.pass_yards,
        "pass_td": PlayerSeasonStats.pass_td,
        "pass_int": PlayerSeasonStats.pass_int,
        "rush_yards": PlayerSeasonStats.rush_yards,
        "rush_td": PlayerSeasonStats.rush_td,
        "receiving_yards": PlayerSeasonStats.receiving_yards,
        "receiving_td": PlayerSeasonStats.receiving_td,
        
        # Basic defensive stats
        "tackles": PlayerSeasonStats.tackles_solo + PlayerSeasonStats.tackles_assist,
        "sacks": PlayerSeasonStats.sacks_defense,
        "interceptions": PlayerSeasonStats.interceptions,
        "pbus": PlayerSeasonStats.pbus,
        
        # Special teams
        "fg_made": PlayerSeasonStats.fg_made,
        "punt_yards": PlayerSeasonStats.punt_yards,
        "punt_net_avg": PlayerSeasonStats.punt_net_avg,
        "punts_in_20": PlayerSeasonStats.punts_in_20,
        
        # Advanced metrics
        "epa": PlayerSeasonStats.epa,
        "success_rate": PlayerSeasonStats.success_rate,
        
        # GDD v3.2 OL stats
        "sacks_allowed": PlayerSeasonStats.sacks_allowed,
        "pressures_allowed": PlayerSeasonStats.pressures_allowed,
        "run_block_wins": PlayerSeasonStats.run_block_wins,
        "pass_block_wins": PlayerSeasonStats.pass_block_wins,
        
        # GDD v3.2 Defense stats
        "pressures": PlayerSeasonStats.pressures,
        "qb_hits": PlayerSeasonStats.qb_hits,
        "tfl": PlayerSeasonStats.tfl,
        "run_stops": PlayerSeasonStats.run_stops,
        "missed_tackles": PlayerSeasonStats.missed_tackles,
        
        # GDD v3.2 Coverage stats
        "targets_faced": PlayerSeasonStats.targets_faced,
        "completions_allowed": PlayerSeasonStats.completions_allowed,
        "yards_allowed": PlayerSeasonStats.yards_allowed,
        "passer_rating_against": PlayerSeasonStats.passer_rating_against,
        
        # GDD v3.2 Situational stats
        "fourth_down_conversions": PlayerSeasonStats.fourth_down_conversions,
        "red_zone_td": PlayerSeasonStats.red_zone_td,
        "goal_to_go_td": PlayerSeasonStats.goal_to_go_td,
        "two_minute_plays": PlayerSeasonStats.two_minute_plays,
    }
    
    if stat not in stat_fields:
        raise HTTPException(status_code=400, detail=f"Invalid stat: {stat}")
    
    # Role-based stat filtering
    role_stats = {
        "ol": ["sacks_allowed", "pressures_allowed", "run_block_wins", "pass_block_wins"],
        "dl": ["pressures", "qb_hits", "sacks", "tfl", "run_stops"],
        "db": ["targets_faced", "completions_allowed", "yards_allowed", "pbus", "interceptions", "passer_rating_against"],
        "st": ["fg_made", "punt_yards", "punt_net_avg", "punts_in_20", "hang_time_avg", "kick_distance_avg"],
        "qb": ["pass_yards", "pass_td", "pass_int", "epa", "success_rate"],
        "rb": ["rush_yards", "rush_td", "broken_tackle"],
        "wr": ["receiving_yards", "receiving_td", "targets", "receptions"],
        "te": ["receiving_yards", "receiving_td", "targets", "receptions"]
    }
    
    if role != "all" and role in role_stats:
        if stat not in role_stats[role]:
            raise HTTPException(status_code=400, detail=f"Stat '{stat}' not available for role '{role}'")
    
    # Build query with situational split filtering
    query = select(
        PlayerSeasonStats.player_id,
        PlayerSeasonStats.team_id,
        Team.name.label("team_name"),
        stat_fields[stat].label("stat_value"),
        PlayerSeasonStats.gp.label("games_played")
    ).join(
        Team, PlayerSeasonStats.team_id == Team.id
    ).where(
        PlayerSeasonStats.season == year
    )
    
    # Apply situational split filtering
    if split == "third_down":
        # Filter for players with meaningful third down stats
        query = query.where(PlayerSeasonStats.third_down_attempts > 0)
    elif split == "red_zone":
        # Filter for players with red zone attempts
        query = query.where(PlayerSeasonStats.red_zone_attempts > 0)
    elif split == "goal_to_go":
        # Filter for players with goal-to-go attempts
        query = query.where(PlayerSeasonStats.goal_to_go_attempts > 0)
    elif split == "two_minute":
        # Filter for players with two-minute drill plays
        query = query.where(PlayerSeasonStats.two_minute_plays > 0)
    elif split == "garbage_time_excluded":
        # Filter out garbage time plays (this would require additional logic)
        # For now, we'll use regular season stats
        pass
    
    query = query.order_by(desc(stat_fields[stat])).limit(top)
    
    results = s.exec(query).all()
    
    return [
        LeaderResponse(
            player_id=r.player_id,
            team_id=r.team_id,
            team_name=r.team_name,
            stat_value=float(r.stat_value),
            games_played=r.games_played
        )
        for r in results
    ]

@router.get("/leaders/ol")
def get_ol_leaders(
    year: int = Query(..., description="Season year"),
    stat: str = Query("sacks_allowed", description="sacks_allowed|pressures_allowed|run_block_wins|pass_block_wins"),
    top: int = Query(10, ge=1, le=100, description="Number of leaders to return"),
    s: Session = Depends(get_session)
):
    """Get offensive line statistical leaders"""
    
    ol_stats = {
        "sacks_allowed": PlayerSeasonStats.sacks_allowed,
        "pressures_allowed": PlayerSeasonStats.pressures_allowed,
        "run_block_wins": PlayerSeasonStats.run_block_wins,
        "pass_block_wins": PlayerSeasonStats.pass_block_wins,
    }
    
    if stat not in ol_stats:
        raise HTTPException(status_code=400, detail=f"Invalid OL stat: {stat}")
    
    # For OL stats, lower is better for sacks/pressures allowed, higher is better for wins
    order_field = desc(ol_stats[stat]) if stat in ["run_block_wins", "pass_block_wins"] else asc(ol_stats[stat])
    
    query = select(
        PlayerSeasonStats.player_id,
        PlayerSeasonStats.team_id,
        Team.name.label("team_name"),
        ol_stats[stat].label("stat_value"),
        PlayerSeasonStats.gp.label("games_played")
    ).join(
        Team, PlayerSeasonStats.team_id == Team.id
    ).where(
        PlayerSeasonStats.season == year
    ).order_by(order_field).limit(top)
    
    results = s.exec(query).all()
    
    return [
        LeaderResponse(
            player_id=r.player_id,
            team_id=r.team_id,
            team_name=r.team_name,
            stat_value=float(r.stat_value),
            games_played=r.games_played
        )
        for r in results
    ]

@router.get("/leaders/defense")
def get_defense_leaders(
    year: int = Query(..., description="Season year"),
    stat: str = Query("pressures", description="pressures|qb_hits|sacks|tfl|run_stops|missed_tackles"),
    top: int = Query(10, ge=1, le=100, description="Number of leaders to return"),
    s: Session = Depends(get_session)
):
    """Get defensive front statistical leaders"""
    
    defense_stats = {
        "pressures": PlayerSeasonStats.pressures,
        "qb_hits": PlayerSeasonStats.qb_hits,
        "sacks": PlayerSeasonStats.sacks_defense,
        "tfl": PlayerSeasonStats.tfl,
        "run_stops": PlayerSeasonStats.run_stops,
        "missed_tackles": PlayerSeasonStats.missed_tackles,
    }
    
    if stat not in defense_stats:
        raise HTTPException(status_code=400, detail=f"Invalid defense stat: {stat}")
    
    # For defense stats, lower is better for missed tackles, higher is better for others
    order_field = asc(defense_stats[stat]) if stat == "missed_tackles" else desc(defense_stats[stat])
    
    query = select(
        PlayerSeasonStats.player_id,
        PlayerSeasonStats.team_id,
        Team.name.label("team_name"),
        defense_stats[stat].label("stat_value"),
        PlayerSeasonStats.gp.label("games_played")
    ).join(
        Team, PlayerSeasonStats.team_id == Team.id
    ).where(
        PlayerSeasonStats.season == year
    ).order_by(order_field).limit(top)
    
    results = s.exec(query).all()
    
    return [
        LeaderResponse(
            player_id=r.player_id,
            team_id=r.team_id,
            team_name=r.team_name,
            stat_value=float(r.stat_value),
            games_played=r.games_played
        )
        for r in results
    ]

@router.get("/leaders/coverage")
def get_coverage_leaders(
    year: int = Query(..., description="Season year"),
    stat: str = Query("pbus", description="targets_faced|completions_allowed|yards_allowed|pbus|interceptions|passer_rating_against"),
    top: int = Query(10, ge=1, le=100, description="Number of leaders to return"),
    s: Session = Depends(get_session)
):
    """Get coverage/secondary statistical leaders"""
    
    coverage_stats = {
        "targets_faced": PlayerSeasonStats.targets_faced,
        "completions_allowed": PlayerSeasonStats.completions_allowed,
        "yards_allowed": PlayerSeasonStats.yards_allowed,
        "pbus": PlayerSeasonStats.pbus,
        "interceptions": PlayerSeasonStats.interceptions,
        "passer_rating_against": PlayerSeasonStats.passer_rating_against,
    }
    
    if stat not in coverage_stats:
        raise HTTPException(status_code=400, detail=f"Invalid coverage stat: {stat}")
    
    # For coverage stats, lower is better for allowed stats and passer rating, higher is better for positive plays
    order_field = asc(coverage_stats[stat]) if stat in ["completions_allowed", "yards_allowed", "passer_rating_against"] else desc(coverage_stats[stat])
    
    query = select(
        PlayerSeasonStats.player_id,
        PlayerSeasonStats.team_id,
        Team.name.label("team_name"),
        coverage_stats[stat].label("stat_value"),
        PlayerSeasonStats.gp.label("games_played")
    ).join(
        Team, PlayerSeasonStats.team_id == Team.id
    ).where(
        PlayerSeasonStats.season == year
    ).order_by(order_field).limit(top)
    
    results = s.exec(query).all()
    
    return [
        LeaderResponse(
            player_id=r.player_id,
            team_id=r.team_id,
            team_name=r.team_name,
            stat_value=float(r.stat_value),
            games_played=r.games_played
        )
        for r in results
    ]

@router.get("/leaders/situational")
def get_situational_leaders(
    year: int = Query(..., description="Season year"),
    stat: str = Query("fourth_down_conversions", description="fourth_down_conversions|red_zone_td|goal_to_go_td|two_minute_plays"),
    top: int = Query(10, ge=1, le=100, description="Number of leaders to return"),
    s: Session = Depends(get_session)
):
    """Get situational statistical leaders"""
    
    situational_stats = {
        "fourth_down_conversions": PlayerSeasonStats.fourth_down_conversions,
        "red_zone_td": PlayerSeasonStats.red_zone_td,
        "goal_to_go_td": PlayerSeasonStats.goal_to_go_td,
        "two_minute_plays": PlayerSeasonStats.two_minute_plays,
    }
    
    if stat not in situational_stats:
        raise HTTPException(status_code=400, detail=f"Invalid situational stat: {stat}")
    
    query = select(
        PlayerSeasonStats.player_id,
        PlayerSeasonStats.team_id,
        Team.name.label("team_name"),
        situational_stats[stat].label("stat_value"),
        PlayerSeasonStats.gp.label("games_played")
    ).join(
        Team, PlayerSeasonStats.team_id == Team.id
    ).where(
        PlayerSeasonStats.season == year
    ).order_by(desc(situational_stats[stat])).limit(top)
    
    results = s.exec(query).all()
    
    return [
        LeaderResponse(
            player_id=r.player_id,
            team_id=r.team_id,
            team_name=r.team_name,
            stat_value=float(r.stat_value),
            games_played=r.games_played
        )
        for r in results
    ]

@router.get("/players/season")
def get_player_season_stats(
    team: Optional[int] = Query(None, description="Filter by team ID"),
    position: Optional[str] = Query(None, description="Filter by position"),
    year: int = Query(..., description="Season year"),
    s: Session = Depends(get_session)
):
    """Get player season statistics"""
    
    query = select(PlayerSeasonStats).where(PlayerSeasonStats.season == year)
    
    if team is not None:
        query = query.where(PlayerSeasonStats.team_id == team)
    
    # Note: Position filtering would require a Player model with position field
    # For now, we'll skip position filtering
    
    results = s.exec(query).all()
    
    return [
        {
            "player_id": r.player_id,
            "team_id": r.team_id,
            "season": r.season,
            "gp": r.gp,
            "gs": r.gs,
            "pass_attempts": r.pass_attempts,
            "pass_completions": r.pass_completions,
            "pass_yards": r.pass_yards,
            "pass_td": r.pass_td,
            "pass_int": r.pass_int,
            "rush_attempts": r.rush_attempts,
            "rush_yards": r.rush_yards,
            "rush_td": r.rush_td,
            "targets": r.targets,
            "receptions": r.receptions,
            "receiving_yards": r.receiving_yards,
            "receiving_td": r.receiving_td,
            "tackles_solo": r.tackles_solo,
            "tackles_assist": r.tackles_assist,
            "sacks_defense": r.sacks_defense,
            "interceptions": r.interceptions,
            "epa": r.epa,
            "success_rate": r.success_rate,
            # Derived stats
            "ypa": r.ypa,
            "ypc": r.ypc,
            "ypr": r.ypr,
            "completion_pct": r.completion_pct,
            "passer_rating": r.passer_rating,
            "fg_pct": r.fg_pct,
            "third_down_pct": r.third_down_pct,
            "explosives_rate": r.explosives_rate,
        }
        for r in results
    ]

@router.get("/teams/season")
def get_team_season_stats(
    conference: Optional[str] = Query(None, description="Filter by conference"),
    division: Optional[str] = Query(None, description="Filter by division"),
    year: int = Query(..., description="Season year"),
    s: Session = Depends(get_session)
):
    """Get team season statistics"""
    
    query = select(TeamSeasonStats).join(
        Team, TeamSeasonStats.team_id == Team.id
    ).where(TeamSeasonStats.season == year)
    
    if conference is not None:
        query = query.where(Team.conference == conference)
    
    if division is not None:
        query = query.where(Team.division == division)
    
    results = s.exec(query).all()
    
    return [
        {
            "team_id": r.team_id,
            "season": r.season,
            "gp": r.gp,
            "pass_attempts": r.pass_attempts,
            "pass_completions": r.pass_completions,
            "pass_yards": r.pass_yards,
            "pass_td": r.pass_td,
            "pass_int": r.pass_int,
            "rush_attempts": r.rush_attempts,
            "rush_yards": r.rush_yards,
            "rush_td": r.rush_td,
            "total_yards": r.total_yards,
            "total_td": r.total_td,
            "turnovers": r.turnovers,
            "tackles_solo": r.tackles_solo,
            "tackles_assist": r.tackles_assist,
            "sacks": r.sacks,
            "interceptions": r.interceptions,
            "forced_fumbles": r.forced_fumbles,
            "fumble_recoveries": r.fumble_recoveries,
            "punts": r.punts,
            "punt_yards": r.punt_yards,
            "punts_in_20": r.punts_in_20,
            "fg_attempts": r.fg_attempts,
            "fg_made": r.fg_made,
            "penalties": r.penalties,
            "penalty_yards": r.penalty_yards,
            "epa": r.epa,
            "success_rate": r.success_rate,
            "explosives": r.explosives,
            "third_down_conversions": r.third_down_conversions,
            "third_down_attempts": r.third_down_attempts,
        }
        for r in results
    ]

@router.post("/test-create")
def test_create_stats(s: Session = Depends(get_session)):
    """Test creating a simple stats record"""
    
    try:
        # Create a simple test stats record
        test_stats = TeamGameStats(
            game_id=1,
            team_id=1,
            gp=True,
            snaps_offense=10,
            pass_attempts=5,
            pass_completions=3,
            pass_yards=50,
            rush_attempts=3,
            rush_yards=20,
            total_yards=70,
            total_td=1,
            turnovers=1,
            punts=2,
            fg_attempts=1,
            fg_made=1,
        )
        
        s.add(test_stats)
        s.commit()
        
        return {"ok": True, "message": "Test stats created successfully"}
        
    except Exception as e:
        s.rollback()
        logger.error(f"Error creating test stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create test stats: {e}")

@router.post("/test-create-game-1")
def test_create_game_1_stats(s: Session = Depends(get_session)):
    """Test creating stats for game 1"""
    
    try:
        # Create stats for game 1
        test_stats = TeamGameStats(
            game_id=1,
            team_id=1,
            gp=True,
            snaps_offense=10,
            pass_attempts=5,
            pass_completions=3,
            pass_yards=50,
            rush_attempts=3,
            rush_yards=20,
            total_yards=70,
            total_td=1,
            turnovers=1,
            punts=2,
            fg_attempts=1,
            fg_made=1,
        )
        
        s.add(test_stats)
        s.commit()
        
        return {"ok": True, "message": "Game 1 stats created successfully"}
        
    except Exception as e:
        s.rollback()
        logger.error(f"Error creating game 1 stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create game 1 stats: {e}")

@router.post("/rollup/game/{game_id}")
def rollup_game_stats_endpoint(game_id: int, s: Session = Depends(get_session)):
    """Roll up stats for a specific game"""
    
    success = rollup_game_stats_ultra_simple(s, game_id)
    if success:
        return {"ok": True, "message": f"Stats rolled up for game {game_id}"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to roll up stats for game {game_id}")

@router.post("/rollup/season/{season}")
def rollup_season_stats_endpoint(season: int, s: Session = Depends(get_session)):
    """Roll up stats for all games in a season"""
    
    success = rollup_season_stats_ultra_simple(s, season)
    if success:
        return {"ok": True, "message": f"Stats rolled up for season {season}"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to roll up stats for season {season}")