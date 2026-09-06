# app/services/stats_pipeline.py
from __future__ import annotations
from sqlmodel import Session, select
from app.models.stats import PlayerGameStats, TeamGameStats, RecordEntry
from app.services.stats_aggregate import (
    upsert_player_season, upsert_player_career, upsert_team_season, update_records_for_season
)
from app.services.hof_service import nominate_retiring_players, nominate_eligible_coaches, vote_and_induct
from app.services.awards_pipeline import on_week_complete, on_season_finalized as awards_season_finalized

def on_game_finalized(sess: Session, game_id: int):
    """Process stats aggregation after a game is finalized."""
    # Get all player game stats for this game
    player_games = list(sess.exec(select(PlayerGameStats).where(PlayerGameStats.game_id == game_id)))
    
    # Group by player for season aggregation
    players_by_id = {}
    for pg in player_games:
        if pg.player_id not in players_by_id:
            players_by_id[pg.player_id] = []
        players_by_id[pg.player_id].append(pg)
    
    # Aggregate player season stats
    for player_id, game_rows in players_by_id.items():
        if not game_rows:
            continue
        
        # Get season and team from first game row
        season = game_rows[0].season
        team_id = game_rows[0].team_id
        
        # Upsert season stats
        upsert_player_season(sess, season, player_id, team_id, game_rows)
        
        # Update career stats
        upsert_player_career(sess, player_id)
    
    # Get team game stats for this game
    team_games = list(sess.exec(select(TeamGameStats).where(TeamGameStats.game_id == game_id)))
    
    # Group by team for season aggregation
    teams_by_id = {}
    for tg in team_games:
        if tg.team_id not in teams_by_id:
            teams_by_id[tg.team_id] = []
        teams_by_id[tg.team_id].append(tg)
    
    # Aggregate team season stats
    for team_id, game_rows in teams_by_id.items():
        if not game_rows:
            continue
        
        # Get season from first game row
        season = game_rows[0].season
        
        # Upsert season stats
        upsert_team_season(sess, season, team_id, game_rows)
    
    sess.commit()

def on_week_complete(sess: Session, season: int, week: int):
    """Process stats aggregation and awards after a week is completed."""
    # Process awards for the completed week
    from app.services.awards_pipeline import on_week_complete as awards_week_complete
    awards_week_complete(sess, season, week)
    
    # Note: Game-level stats aggregation is handled by on_game_finalized
    # This function focuses on weekly awards and annual projections

def on_regular_season_complete(sess: Session, season: int):
    """Process end of regular season stats and records."""
    # Update records for the season
    update_records_for_season(sess, season)
    
    # Clear existing records for this season to avoid duplicates
    existing_records = list(sess.exec(select(RecordEntry).where(
        RecordEntry.record_type == "SINGLE_SEASON",
        RecordEntry.season == season
    )))
    
    for record in existing_records:
        sess.delete(record)
    
    # Recompute records
    update_records_for_season(sess, season)

def on_postseason_complete(sess: Session, season: int):
    """Process end of postseason stats, records, awards finalization, and HOF nominations."""
    # Update final records
    update_records_for_season(sess, season)
    
    # Finalize annual awards
    awards_season_finalized(sess, season)
    
    # HOF nomination process
    # Note: In a real implementation, you'd get retiring players and eligible coaches
    # from your retirement/coaching system. For now, we'll use placeholder lists.
    retiring_player_ids = []  # TODO: Get from retirement system
    eligible_coach_ids = []   # TODO: Get from coaching system
    
    # Nominate retiring players and eligible coaches
    nominate_retiring_players(sess, season, retiring_player_ids)
    nominate_eligible_coaches(sess, season, eligible_coach_ids)
    
    # Vote and induct
    vote_and_induct(sess, season)

def rebuild_records_for_season(sess: Session, season: int):
    """Manually rebuild records for a specific season."""
    # Clear existing single-season records
    existing_records = list(sess.exec(select(RecordEntry).where(
        RecordEntry.record_type == "SINGLE_SEASON",
        RecordEntry.season == season
    )))
    
    for record in existing_records:
        sess.delete(record)
    
    # Recompute records
    update_records_for_season(sess, season)

def rebuild_all_career_records(sess: Session):
    """Manually rebuild all career records."""
    # Clear existing career records
    existing_records = list(sess.exec(select(RecordEntry).where(
        RecordEntry.record_type == "CAREER"
    )))
    
    for record in existing_records:
        sess.delete(record)
    
    # Recompute career records
    update_records_for_season(sess, 0)  # Use dummy season for career records
