# app/services/awards_compute.py
from __future__ import annotations
import json
from typing import List, Tuple, Dict
from sqlmodel import Session, select, delete
from app.models.awards import WeeklyAward, WeeklyAwardType, AnnualAward, AnnualAwardType, AnnualAwardProjection
from app.models.stats import PlayerGameStats, PlayerSeasonStats, TeamSeasonStats
from app.services.awards_scoring import (
    weekly_offense_score, weekly_defense_score, weekly_special_teams_score, weekly_rookie_score,
    season_player_mvp_score, season_opoy_score, season_dpoy_score, season_roy_score,
    season_coty_score, season_gmoty_score
)

def _pgs_to_dict(p: PlayerGameStats) -> Dict[str, float]:
    """Convert PlayerGameStats to dictionary for scoring."""
    return {
        "pass_yds": p.pass_yds, "pass_td": p.pass_td, "pass_int": p.pass_int, "sacks_taken": p.sacks_taken,
        "rush_yds": p.rush_yds, "rush_td": p.rush_td,
        "rec_yds": p.rec_yds, "rec_td": p.rec_td, "fumbles_lost": p.fumbles_lost,
        "tackles": p.tackles, "tfl": p.tfl, "sacks": float(p.sacks), "qb_hits": p.qb_hits,
        "ints": p.ints, "pbus": p.pbus, "ff": p.ff, "fr": p.fr, "td_def": p.td_def,
        "kr_yds": p.kr_yds, "pr_yds": p.pr_yds, "fg_made": p.fg_made, "fg_att": p.fg_att, "xp_made": p.xp_made,
        "punts": p.punts, "punt_yds": p.punt_yds
    }

def _pss_to_dict(p: PlayerSeasonStats) -> Dict[str, float]:
    """Convert PlayerSeasonStats to dictionary for scoring."""
    return {
        "pass_yds": p.pass_yds, "pass_td": p.pass_td, "pass_int": p.pass_int,
        "rush_yds": p.rush_yds, "rush_td": p.rush_td,
        "rec_yds": p.rec_yds, "rec_td": p.rec_td, "fumbles_lost": p.fumbles_lost,
        "tackles": p.tackles, "tfl": p.tfl, "sacks": float(p.sacks), "qb_hits": p.qb_hits,
        "ints": p.ints, "pbus": p.pbus, "ff": p.ff, "fr": p.fr, "td_def": p.td_def,
        "fg_made": p.fg_made, "fg_att": p.fg_att, "xp_made": p.xp_made,
        "punts": p.punts, "punt_yds": p.punt_yds
    }

def _team_season_to_dict(t: TeamSeasonStats) -> Dict[str, float]:
    """Convert TeamSeasonStats to dictionary for scoring."""
    games = (t.wins + t.losses + t.ties) or 1
    w_pct = (t.wins + 0.5*t.ties) / games
    return {"w_pct": w_pct, "points_for": t.points_for, "points_against": t.points_against, "improvement": 0.0}

def _is_rookie(sess: Session, player_id: int) -> bool:
    """Rookie = only one PlayerSeasonStats row (the current season)"""
    cnt = sess.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.player_id==player_id)).all()
    seasons = {r.season for r in cnt}
    return len(seasons) == 1

def compute_weekly_awards(sess: Session, season: int, week: int):
    """Compute weekly awards for a specific season and week."""
    # wipe existing for idempotence
    sess.exec(delete(WeeklyAward).where(WeeklyAward.season==season, WeeklyAward.week==week))

    rows = list(sess.exec(select(PlayerGameStats).where(PlayerGameStats.season==season, PlayerGameStats.week==week)))
    if not rows:
        sess.commit()
        return

    best = {
        WeeklyAwardType.OPOTW: (None, -1e9, None),
        WeeklyAwardType.DPOTW: (None, -1e9, None),
        WeeklyAwardType.STPOTW: (None, -1e9, None),
        WeeklyAwardType.ROW:   (None, -1e9, None),
    }
    
    # compute scores for each player
    for r in rows:
        d = _pgs_to_dict(r)
        off = weekly_offense_score(d)
        de  = weekly_defense_score(d)
        st  = weekly_special_teams_score(d)

        if off > best[WeeklyAwardType.OPOTW][1]:
            best[WeeklyAwardType.OPOTW] = (r, off, d)
        if de > best[WeeklyAwardType.DPOTW][1]:
            best[WeeklyAwardType.DPOTW] = (r, de, d)
        if st > best[WeeklyAwardType.STPOTW][1]:
            best[WeeklyAwardType.STPOTW] = (r, st, d)
        if _is_rookie(sess, r.player_id):
            row = weekly_rookie_score(d)
            if row > best[WeeklyAwardType.ROW][1]:
                best[WeeklyAwardType.ROW] = (r, row, d)

    # persist winners
    for award, (r, score, d) in best.items():
        if r is None: 
            continue
        sess.add(WeeklyAward(
            season=season, week=week, award=award,
            winner_player_id=r.player_id, winner_team_id=r.team_id, score=score,
            stats_blob=json.dumps(d)
        ))
    sess.commit()

def compute_annual_projections(sess: Session, season: int, top_n: int = 5):
    """Compute annual award projections for a specific season."""
    # reset projections for this season
    sess.exec(delete(AnnualAwardProjection).where(AnnualAwardProjection.season==season))

    p_season = list(sess.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.season==season)))
    if not p_season:
        sess.commit()
        return
        
    # Player awards
    def rank_and_store(award: AnnualAwardType, scored: List[Tuple[int,float,int,Dict]]):
        scored.sort(key=lambda x: x[1], reverse=True)
        for i, (pid, score, team_id, snap) in enumerate(scored[:top_n], start=1):
            sess.add(AnnualAwardProjection(season=season, award=award, rank=i, candidate_type="PLAYER",
                                           candidate_id=pid, team_id=team_id, score=score, stats_blob=json.dumps(snap)))

    # MVP/OPOY/DPOY/ROY
    mvp_scored, opoy_scored, dpoy_scored, roy_scored = [], [], [], []
    for ps in p_season:
        sd = _pss_to_dict(ps)
        mvp_scored.append((ps.player_id, season_player_mvp_score(sd), ps.team_id, sd))
        opoy_scored.append((ps.player_id, season_opoy_score(sd), ps.team_id, sd))
        dpoy_scored.append((ps.player_id, season_dpoy_score(sd), ps.team_id, sd))
        # rookie?
        seasons_for_player = sess.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.player_id==ps.player_id)).all()
        if len({r.season for r in seasons_for_player}) == 1:
            roy_scored.append((ps.player_id, season_roy_score(sd), ps.team_id, sd))

    rank_and_store(AnnualAwardType.MVP, mvp_scored)
    rank_and_store(AnnualAwardType.OPOY, opoy_scored)
    rank_and_store(AnnualAwardType.DPOY, dpoy_scored)
    rank_and_store(AnnualAwardType.ROY, roy_scored)

    # Coach/GM awards from team table
    teams = list(sess.exec(select(TeamSeasonStats).where(TeamSeasonStats.season==season)))
    coty_scored, gmoty_scored = [], []
    for t in teams:
        td = _team_season_to_dict(t)
        coty_scored.append((t.team_id, season_coty_score(td), t.team_id, td))
        gmoty_scored.append((t.team_id, season_gmoty_score(td), t.team_id, td))

    # store as TEAM candidates
    def rank_team_and_store(award: AnnualAwardType, scored: List[Tuple[int,float,int,Dict]]):
        scored.sort(key=lambda x: x[1], reverse=True)
        for i, (tid, score, _tid, snap) in enumerate(scored[:top_n], start=1):
            sess.add(AnnualAwardProjection(season=season, award=award, rank=i, candidate_type="TEAM",
                                           candidate_id=tid, team_id=tid, score=score, stats_blob=json.dumps(snap)))

    rank_team_and_store(AnnualAwardType.COTY, coty_scored)
    rank_team_and_store(AnnualAwardType.GMOTY, gmoty_scored)

    sess.commit()

def finalize_annual_awards(sess: Session, season: int):
    """
    Called once at end of season (after playoffs). Picks #1 in projections as winners and sets finalized flags.
    """
    for award in AnnualAwardType:
        top = sess.exec(select(AnnualAwardProjection).where(
            AnnualAwardProjection.season==season,
            AnnualAwardProjection.award==award,
            AnnualAwardProjection.rank==1
        )).first()
        if not top:
            continue
        row = sess.exec(select(AnnualAward).where(AnnualAward.season==season, AnnualAward.award==award)).first()
        if not row:
            row = AnnualAward(season=season, award=award)
        row.finalized = True
        row.score = top.score
        if top.candidate_type == "PLAYER":
            row.winner_player_id = top.candidate_id
            row.winner_team_id = top.team_id
        elif top.candidate_type == "TEAM":
            row.winner_team_id = top.candidate_id
        # (coach/gm mapping can be fleshed out later)
        sess.add(row)
    sess.commit()


