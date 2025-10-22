from typing import Dict, List
from sqlmodel import Session
from app.models.player_models import Player, DepthChart

CORE_STARTERS = {
    "QB":1,"RB":1,"WR":3,"TE":1,"OL":5,"DL":4,"LB":3,"CB":2,"S":2,"K":1,"P":1
}

def team_pos_counts(session: Session, team_id: int) -> Dict[str,int]:
    counts: Dict[str,int] = {k:0 for k in CORE_STARTERS}
    rows = session.query(Player).filter(Player.team_id==team_id, Player.is_active==True).all()
    for p in rows:
        if p.pos in counts:
            counts[p.pos] += 1
    return counts

def need_score(session: Session, team_id: int) -> Dict[str,float]:
    """
    Higher score => bigger need. Based on shortage vs starters and avg OVR at position.
    """
    from statistics import mean
    rows = session.query(Player).filter(Player.team_id==team_id, Player.is_active==True).all()
    by_pos: Dict[str, List[int]] = {}
    for p in rows:
        by_pos.setdefault(p.pos, []).append(p.ovr)
    scores: Dict[str,float] = {}
    for pos, starters in CORE_STARTERS.items():
        have = len(by_pos.get(pos, []))
        avg = mean(by_pos.get(pos, [50]))
        shortage = max(0, starters - have)
        scores[pos] = shortage*1.5 + (80 - avg)/30.0  # normalized
    return scores

def top_needs(session: Session, team_id: int, k: int = 3) -> List[str]:
    sc = need_score(session, team_id)
    return [p for p,_ in sorted(sc.items(), key=lambda kv: kv[1], reverse=True)[:k]]
