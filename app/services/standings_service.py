from typing import List, Dict, Tuple
from sqlmodel import Session
from app.models.sim_models import SimTeam, SimGame
import random
from dataclasses import dataclass

def shuffle_seeded(items, seed):
    r = random.Random(seed)
    items = list(items)
    r.shuffle(items)
    return items

@dataclass
class TeamRecord:
    team_id: int
    wins: int
    losses: int
    points_for: int
    points_against: int
    power: float

def standings(session: Session, season: int) -> List[TeamRecord]:
    teams = {t.id: t for t in session.query(SimTeam).all()}
    games = session.query(SimGame).filter(SimGame.season == season).all()
    rec = {tid: TeamRecord(tid,0,0,0,0,teams[tid].power) for tid in teams}
    for g in games:
        if not g.is_played: continue
        r = rec[g.home_team_id]; a = rec[g.away_team_id]
        r.points_for += g.home_score; r.points_against += g.away_score
        a.points_for += g.away_score; a.points_against += g.home_score
        if g.home_score >= g.away_score:
            r.wins += 1; a.losses += 1
        else:
            a.wins += 1; r.losses += 1
    return list(rec.values())

def update_power(elo_a: float, elo_b: float, score_a: int, score_b: int, k: float = 20) -> (float, float):
    import math
    ea = 1 / (1 + 10 ** ((elo_b - elo_a)/400))
    sa = 1.0 if score_a > score_b else 0.0 if score_b > score_a else 0.5
    margin = max(1.0, abs(score_a - score_b) ** 0.5)
    k *= margin
    new_a = elo_a + k * (sa - ea)
    new_b = elo_b + k * ((1 - sa) - (1 - ea))
    return new_a, new_b

def head_to_head_record(session: Session, season: int, a: int, b: int) -> Tuple[int,int]:
    games = session.query(SimGame).filter(SimGame.season==season).all()
    w = l = 0
    for g in games:
        if not g.is_played: continue
        if {g.home_team_id, g.away_team_id} == {a,b}:
            if g.home_team_id == a:
                if g.home_score >= g.away_score: w += 1
                else: l += 1
            else:
                if g.away_score >= g.home_score: w += 1
                else: l += 1
    return w, l

def points_for_against(session: Session, season: int, team_id: int) -> Tuple[int,int]:
    games = session.query(SimGame).filter(SimGame.season==season).all()
    pf = pa = 0
    for g in games:
        if not g.is_played: continue
        if g.home_team_id == team_id:
            pf += g.home_score; pa += g.away_score
        elif g.away_team_id == team_id:
            pf += g.away_score; pa += g.home_score
    return pf, pa

def league_order_worst_to_best(session: Session, season: int) -> List[int]:
    teams = {t.id: t for t in session.query(SimTeam).all()}
    games = session.query(SimGame).filter(SimGame.season==season).all()
    wins = {tid:0 for tid in teams}
    losses = {tid:0 for tid in teams}
    pf = {tid:0 for tid in teams}
    pa = {tid:0 for tid in teams}
    for g in games:
        if not g.is_played: continue
        pf[g.home_team_id]+=g.home_score; pa[g.home_team_id]+=g.away_score
        pf[g.away_team_id]+=g.away_score; pa[g.away_team_id]+=g.home_score
        if g.home_score >= g.away_score:
            wins[g.home_team_id]+=1; losses[g.away_team_id]+=1
        else:
            wins[g.away_team_id]+=1; losses[g.home_team_id]+=1
    # sort: worst → best
    def key(tid):
        return (wins[tid], -(pf[tid]-pa[tid]), -pf[tid], teams[tid].power)
    order = list(teams.keys())
    order.sort(key=key)  # ascending wins (worst first)
    return order
