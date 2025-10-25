# app/services/draft_compare.py
from __future__ import annotations
from typing import Dict, Any, List
from sqlmodel import Session, select
from statistics import mean
from app.models.draft import Prospect

FIELDS_CORE = ["overall","potential","speed","agility","strength","awareness"]
FIELDS_META = ["name","pos","season","drafted_by_team_id","drafted_overall_pick"]

def board_score(prospect: Prospect) -> float:
    """
    Calculate a composite board score for a prospect.
    This is a simple weighted average of key attributes.
    """
    # Weight the attributes based on importance
    weights = {
        "overall": 0.4,
        "potential": 0.3,
        "awareness": 0.15,
        "speed": 0.1,
        "agility": 0.03,
        "strength": 0.02
    }
    
    score = 0.0
    total_weight = 0.0
    
    for attr, weight in weights.items():
        value = getattr(prospect, attr, 0) or 0
        score += float(value) * weight
        total_weight += weight
    
    return score / total_weight if total_weight > 0 else 0.0

def _pct_rank(val: float, values: List[float]) -> float:
    """Return percentile rank (0..100) of val within values; robust to ties/empties."""
    if not values:
        return 0.0
    below = sum(1 for v in values if v < val)
    equal = sum(1 for v in values if v == val)
    # average rank within ties
    rank = (below + (equal/2.0)) / len(values)
    return round(rank * 100.0, 1)

def _collect_pos_bucket(session: Session, season: int, pos: str) -> Dict[str, List[float]]:
    rows = session.exec(select(Prospect).where(Prospect.season == season, Prospect.pos == pos)).all()
    bucket: Dict[str, List[float]] = {k: [] for k in FIELDS_CORE}
    bucket["board_score"] = []
    for r in rows:
        for k in FIELDS_CORE:
            bucket[k].append(float(getattr(r, k, 0) or 0))
        bucket["board_score"].append(float(board_score(r)))
    return bucket

def compare_prospects(session: Session, season: int, ids: List[int]) -> Dict[str, Any]:
    """
    Returns aligned comparisons + position-percentile ranks per field and board_score.
    """
    # fetch
    rows = session.exec(select(Prospect).where(Prospect.season == season, Prospect.id.in_(ids))).all()
    # build pos buckets (per unique position)
    pos_buckets: Dict[str, Dict[str, List[float]]] = {}
    for r in rows:
        pos = (r.pos or "").upper()
        if pos not in pos_buckets:
            pos_buckets[pos] = _collect_pos_bucket(session, season, pos)

    items: List[Dict[str, Any]] = []
    for r in rows:
        pos = (r.pos or "").upper()
        bs = round(float(board_score(r)), 3)
        # percentiles within position
        pct = {}
        for k in FIELDS_CORE + ["board_score"]:
            vals = pos_buckets[pos].get(k, [])
            val = bs if k == "board_score" else float(getattr(r, k, 0) or 0)
            pct[k] = _pct_rank(val, vals)

        item = {
            "id": r.id,
            **{k: getattr(r, k, None) for k in FIELDS_META},
            "metrics": {k: getattr(r, k, None) for k in FIELDS_CORE},
            "board_score": bs,
            "percentiles_pos": pct,   # per-position percentile ranks
        }
        items.append(item)

    # quick diff table (pairwise deltas relative to the first id)
    diff = {}
    if items:
        base = items[0]
        diff["baseline_id"] = base["id"]
        diff_rows = []
        for it in items[1:]:
            row = {"id": it["id"], "name": it["name"], "pos": it["pos"], "deltas": {}}
            for k in FIELDS_CORE + ["board_score"]:
                a = base["metrics"].get(k, base.get(k)) if k != "board_score" else base["board_score"]
                b = it["metrics"].get(k, it.get(k)) if k != "board_score" else it["board_score"]
                if a is not None and b is not None:
                    row["deltas"][k] = round(float(b) - float(a), 1)
            diff_rows.append(row)
        diff["rows"] = diff_rows

    return {"season": season, "count": len(items), "items": items, "diff": diff}


