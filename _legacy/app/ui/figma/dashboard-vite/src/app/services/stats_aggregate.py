# app/services/stats_aggregate.py
from __future__ import annotations
from typing import Iterable, Dict
from sqlmodel import Session, select
from app.models.stats import (
    PlayerGameStats, PlayerSeasonStats, PlayerCareerStats, 
    TeamGameStats, TeamSeasonStats, RecordEntry, RecordType, RecordCategory
)

def _sum_fields(dst, src, exclude: set[str]):
    """Dynamically sum fields from src to dst, excluding specified fields."""
    # Fields that should use max instead of sum
    max_fields = {"long_fg_made", "long_punt"}
    
    for f in dst.__fields__.keys():
        if f in exclude: 
            continue
        if hasattr(src, f):
            if f in max_fields:
                # Use max for fields like long_fg_made, long_punt
                setattr(dst, f, max(getattr(dst, f), getattr(src, f)))
            else:
                # Sum for all other fields
                setattr(dst, f, getattr(dst, f) + getattr(src, f))

def upsert_player_season(sess: Session, season: int, player_id: int, team_id: int, game_rows: Iterable[PlayerGameStats]):
    """Aggregate player game stats into season totals."""
    agg = PlayerSeasonStats(season=season, player_id=player_id, team_id=team_id)
    exclude = {"id","season","player_id","team_id"}
    for g in game_rows:
        _sum_fields(agg, g, exclude)
    existing = sess.exec(select(PlayerSeasonStats).where(
        PlayerSeasonStats.season==season, PlayerSeasonStats.player_id==player_id
    )).first()
    if existing:
        agg.id = existing.id
    sess.add(agg)

def upsert_player_career(sess: Session, player_id: int):
    """Aggregate player season stats into career totals."""
    seasons = list(sess.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.player_id==player_id)).all())
    if not seasons:
        return
    car = PlayerCareerStats(player_id=player_id, seasons=len({s.season for s in seasons}))
    exclude = {"id","player_id","seasons","season","team_id"}
    for s in seasons:
        _sum_fields(car, s, exclude)
    existing = sess.exec(select(PlayerCareerStats).where(PlayerCareerStats.player_id==player_id)).first()
    if existing:
        car.id = existing.id
    sess.add(car)

def upsert_team_season(sess: Session, season: int, team_id: int, games: Iterable[TeamGameStats]):
    """Aggregate team game stats into season totals."""
    agg = TeamSeasonStats(season=season, team_id=team_id)
    
    for g in games:
        for f in agg.__fields__.keys():
            if f in ("id", "season", "team_id"):
                continue
            if hasattr(g, f):
                current_val = getattr(agg, f)
                game_val = getattr(g, f)
                if isinstance(current_val, (int, float)) and isinstance(game_val, (int, float)):
                    setattr(agg, f, current_val + game_val)
    
    # Derive wins/losses/ties from PF/PA at TeamGameStats time (assumed present)
    existing = sess.exec(select(TeamSeasonStats).where(
        TeamSeasonStats.season == season, 
        TeamSeasonStats.team_id == team_id
    )).first()
    if existing:
        agg.id = existing.id
    sess.add(agg)

def _push_record(sess: Session, record_type: str, category: str, season: int | None, player_id: int, value: float):
    """Add a record entry."""
    row = RecordEntry(record_type=record_type, category=category, season=season, player_id=player_id, value=value)
    sess.add(row)

def update_records_for_season(sess: Session, season: int):
    """Update single-season and career records."""
    # Single-season records
    mapping = {
        RecordCategory.PASS_YDS: ("pass_yds", PlayerSeasonStats),
        RecordCategory.PASS_TD: ("pass_td", PlayerSeasonStats),
        RecordCategory.RUSH_YDS: ("rush_yds", PlayerSeasonStats),
        RecordCategory.RUSH_TD: ("rush_td", PlayerSeasonStats),
        RecordCategory.REC_YDS: ("rec_yds", PlayerSeasonStats),
        RecordCategory.REC_TD: ("rec_td", PlayerSeasonStats),
        RecordCategory.SACKS: ("sacks", PlayerSeasonStats),
        RecordCategory.INTS: ("ints", PlayerSeasonStats),
        RecordCategory.FGM: ("fg_made", PlayerSeasonStats),
        RecordCategory.PUNTS: ("punts", PlayerSeasonStats),
        RecordCategory.TACKLES: ("tackles", PlayerSeasonStats),
        # Extended categories
        RecordCategory.PRESSURES: ("pressures", PlayerSeasonStats),
        RecordCategory.PBU: ("pbus", PlayerSeasonStats),
        RecordCategory.KR_TD: ("kr_td", PlayerSeasonStats),
        RecordCategory.PR_TD: ("pr_td", PlayerSeasonStats),
        RecordCategory.I20_PUNTS: ("punts_inside_20", PlayerSeasonStats),
        RecordCategory.LONG_FG: ("long_fg_made", PlayerSeasonStats),
    }
    
    for cat, (field, Model) in mapping.items():
        row = sess.exec(select(Model).where(Model.season == season).order_by(getattr(Model, field).desc())).first()
        if row:
            _push_record(sess, RecordType.SINGLE_SEASON, cat, season, row.player_id, float(getattr(row, field)))

    # Career records (recompute whole-table; acceptable on SQLite size)
    cmap = {
        RecordCategory.PASS_YDS: "pass_yds",
        RecordCategory.PASS_TD: "pass_td",
        RecordCategory.RUSH_YDS: "rush_yds",
        RecordCategory.RUSH_TD: "rush_td",
        RecordCategory.REC_YDS: "rec_yds",
        RecordCategory.REC_TD: "rec_td",
        RecordCategory.SACKS: "sacks",
        RecordCategory.INTS: "ints",
        RecordCategory.FGM: "fg_made",
        RecordCategory.PUNTS: "punts",
        RecordCategory.TACKLES: "tackles",
        # Extended categories
        RecordCategory.PRESSURES: "pressures",
        RecordCategory.PBU: "pbus",
        RecordCategory.KR_TD: "kr_td",
        RecordCategory.PR_TD: "pr_td",
        RecordCategory.I20_PUNTS: "punts_inside_20",
        RecordCategory.LONG_FG: "long_fg_made",
    }
    
    for cat, field in cmap.items():
        row = sess.exec(select(PlayerCareerStats).order_by(getattr(PlayerCareerStats, field).desc())).first()
        if row:
            _push_record(sess, RecordType.CAREER, cat, None, row.player_id, float(getattr(row, field)))

    sess.commit()
