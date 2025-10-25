from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from statistics import mean
from sqlmodel import Session, select
from app.models.roster import DepthChart
from app.services.depth_chart_service import ORDERED_SLOTS, ELIGIBILITY, auto_fill, list_depth_chart
from app.models.player import Player

# Map slots -> position buckets used for needs
BUCKETS: Dict[str, str] = {
    "QB":"QB", "RB":"RB", "WR1":"WR","WR2":"WR","WR3":"WR",
    "TE":"TE", "LT":"LT","LG":"G","C":"C","RG":"G","RT":"RT",
    "EDGE1":"EDGE","EDGE2":"EDGE","DL1":"DL","DL2":"DL","LB1":"LB","LB2":"LB",
    "CB1":"CB","CB2":"CB","S1":"S","S2":"S",
    # Special teams are excluded from draft needs
}

NEEDS_POSITIONS = ["QB","RB","WR","TE","LT","G","C","RT","EDGE","DL","LB","CB","S"]

def ensure_all_depth_charts(sess: Session, season: int, week: int = 0) -> None:
    """Fill every team's chart if missing so needs calcs have starters."""
    from app.models.team import Team
    teams = list(sess.exec(select(Team)))
    # Use opponent_id=0 and game_id composite dummy; availability hook tolerates this
    for t in teams:
        rows = list_depth_chart(sess, t.team_id)
        if not rows:
            auto_fill(sess, t.team_id, season=season, week=week, game_id=10_000 + t.team_id, opponent_id=0)

def _starter_overall(sess: Session, player_id: Optional[int]) -> Optional[int]:
    if not player_id: return None
    p = sess.get(Player, player_id)
    return getattr(p, "overall", None) if p else None

def league_starter_averages(sess: Session, season: int) -> Dict[str, float]:
    """Average OVR for starters at each bucket across all teams/slots."""
    from app.models.team import Team
    ensure_all_depth_charts(sess, season)
    teams = list(sess.exec(select(Team)))
    bucket_vals: Dict[str, List[int]] = {pos: [] for pos in NEEDS_POSITIONS}

    for t in teams:
        rows = list(sess.exec(select(DepthChart).where(DepthChart.team_id==t.team_id)))
        # starters = order_index == 0
        starters = [r for r in rows if r.order_index == 0 and r.slot in BUCKETS]
        for r in starters:
            pos_bucket = BUCKETS[r.slot]
            ov = _starter_overall(sess, r.player_id)
            if ov is not None:
                bucket_vals[pos_bucket].append(int(ov))

    return {k: (mean(v) if v else 0.0) for k,v in bucket_vals.items()}

def team_starter_averages(sess: Session, season: int, team_id: int) -> Dict[str, float]:
    """Average OVR for this team's starters per bucket (e.g., WR uses WR1..WR3)."""
    ensure_all_depth_charts(sess, season)
    rows = list(sess.exec(select(DepthChart).where(DepthChart.team_id==team_id, DepthChart.order_index==0)))
    by_bucket: Dict[str, List[int]] = {pos: [] for pos in NEEDS_POSITIONS}
    for r in rows:
        if r.slot not in BUCKETS: continue
        ov = _starter_overall(sess, r.player_id)
        if ov is not None:
            by_bucket[BUCKETS[r.slot]].append(int(ov))
    # average across that team's starter slots per bucket
    return {k: (mean(v) if v else 0.0) for k,v in by_bucket.items()}

def team_needs(sess: Session, season: int, team_id: int, epsilon: float = 0.0) -> Dict[str, Dict[str, float | bool]]:
    """Return per-position: league_avg, team_avg, need (team_avg < league_avg - epsilon)."""
    lg = league_starter_averages(sess, season)
    tm = team_starter_averages(sess, season, team_id)
    out: Dict[str, Dict[str, float | bool]] = {}
    for pos in NEEDS_POSITIONS:
        la = float(lg.get(pos, 0.0))
        ta = float(tm.get(pos, 0.0))
        out[pos] = {"league_avg": round(la,2), "team_avg": round(ta,2), "need": (ta < la - epsilon)}
    return out
