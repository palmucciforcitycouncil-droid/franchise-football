"""
Weekly Awards Service.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import random
from sqlmodel import Session, select

from app.models.weekly_awards import WeeklyAward, WeeklyAwardType
from app.config_awards import settings_awards


def _try_models():
    out = {}
    for mod, name in [
        ("app.models.sim_models", "SimGame"),
        ("app.models.player_models", "Player"),
        ("app.models.sim_models", "SimTeam"),
    ]:
        try:
            m = __import__(mod, fromlist=[name])
            out[name] = getattr(m, name)
        except Exception:
            out[name] = None
    
    # PlayerGameStats accessor (service or model)
    for mod, name in [
        ("app.models.stats_models", "PlayerGameStats"),
    ]:
        try:
            m = __import__(mod, fromlist=[name])
            out["PlayerGameStats"] = getattr(m, name)
            out["PlayerGameStats_kind"] = "model"
            break
        except Exception:
            continue
    return out


MODELS = _try_models()


def _fetch_weeks(session: Session, season: int) -> List[int]:
    SimGame = MODELS.get("SimGame")
    if not SimGame:
        return list(range(1, 19))  # fallback 18-week NFL-like
    
    rows = session.exec(select(SimGame.week).where(SimGame.season == season)).all()
    uniq = sorted({w for w in rows if w is not None})
    return uniq or list(range(1, 19))


def _iter_player_game_stats_for_week(session: Session, season: int, week: int):
    """Get player game stats for a specific week."""
    kind = MODELS.get("PlayerGameStats_kind")
    PGS = MODELS.get("PlayerGameStats")
    if PGS is None:
        return []
    
    if kind == "model":
        # Try to join with Game table to filter by week
        try:
            from app.models.sim_models import SimGame
            q = select(PGS).join(SimGame, SimGame.id == PGS.game_id).where(
                SimGame.week == week, 
                SimGame.season == season
            )
            return session.exec(q).all()
        except Exception:
            # Fallback: assume PGS has week/season columns
            try:
                q = select(PGS).where(PGS.week == week, PGS.season == season)
                return session.exec(q).all()
            except Exception:
                return []
    
    return []


def _score_off(r) -> float:
    """Score offensive performance for weekly awards."""
    # offense composite per game: TDs + EPA + Yards with mild weighting
    td = (getattr(r, "rush_td", 0) or 0) + (getattr(r, "pass_td", 0) or 0) + (getattr(r, "rec_td", 0) or 0)
    yds = (getattr(r, "rush_yards", 0) or 0) + (getattr(r, "pass_yards", 0) or 0) + (getattr(r, "rec_yards", 0) or 0)
    epa = getattr(r, "epa_total", 0.0) or 0.0
    return 1.5 * td + 0.002 * yds + 1.0 * epa


def _score_def(r) -> float:
    """Score defensive performance for weekly awards."""
    sacks = (getattr(r, "sacks", 0) or 0)
    ints = (getattr(r, "ints", 0) or 0)
    tfl = (getattr(r, "tfl", 0) or 0)
    pbu = (getattr(r, "pbu", 0) or 0)
    depa = getattr(r, "epa_def_total", 0.0) or 0.0
    return 2.0 * ints + 1.5 * sacks + 0.5 * tfl + 0.25 * pbu + 0.5 * (-depa)


def _score_st(r) -> float:
    """Score special teams performance for weekly awards."""
    fgm = getattr(r, "fgm", 0) or 0
    fga = getattr(r, "fga", 0) or 0
    punts = getattr(r, "punts", 0) or 0
    net = getattr(r, "net_punt", 0.0) or 0.0
    ret_td = getattr(r, "ret_td", 0) or 0
    fg_score = (fgm / fga) * 5.0 if fga else 0.0
    return fg_score + 0.05 * net + 2.0 * ret_td + 0.2 * punts


def compute_weekly_awards(session: Session, season: int) -> List[WeeklyAward]:
    """Compute weekly awards for a season."""
    rnd = random.Random(settings_awards.AWARDS_SEED + season * 101)
    winners: List[WeeklyAward] = []
    weeks = _fetch_weeks(session, season)
    
    for wk in weeks:
        rows = _iter_player_game_stats_for_week(session, season, wk)
        if not rows:
            continue
        
        # pick max per category
        try:
            off_row = max(rows, key=_score_off)
            def_row = max(rows, key=_score_def)
            st_row = max(rows, key=_score_st)
            
            for typ, row in [
                (WeeklyAwardType.WPOY_OFF, off_row),
                (WeeklyAwardType.WPOY_DEF, def_row),
                (WeeklyAwardType.WPOY_ST, st_row),
            ]:
                pid = getattr(row, "player_id", None)
                tid = getattr(row, "team_id", None)
                gid = getattr(row, "game_id", None)
                
                if pid:
                    wa = WeeklyAward(
                        season=season, 
                        week=wk, 
                        award=typ, 
                        player_id=pid, 
                        team_id=tid, 
                        game_id=gid
                    )
                    session.add(wa)
                    winners.append(wa)
        except Exception:
            continue
    
    session.commit()
    return winners
