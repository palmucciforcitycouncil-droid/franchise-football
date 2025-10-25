# app/services/draft.py
from __future__ import annotations
from typing import List, Dict, Tuple
import random
from sqlmodel import Session, select, delete
from app.models.draft import DraftClass, Prospect, DraftPick
from app.models.season_stats import TeamSeasonStats

POS_DISTRIBUTION: Dict[str, int] = {
    "QB": 12, "RB": 20, "WR": 40, "TE": 16, "OL": 56,
    "DL": 42, "LB": 36, "DB": 48, "K": 6, "P": 4
}  # sums to 280 = 32*7

def _name_gen(rng: random.Random, pos: str, idx: int) -> str:
    first = ["Jace","Ty","Kai","Jalen","Mason","Evan","Zane","Noah","Leo","Kade","Owen","Liam","Cade","Micah","Troy"]
    last = ["Hendrix","Carver","Mercer","Dalton","Reeves","Bennett","Hayes","Porter","Coleman","Banks","Knight","Foster","Wells","Griffin","Abbott"]
    return f"{rng.choice(first)} {rng.choice(last)}-{pos}{idx}"

def _roll_attr(rng: random.Random, base: int, spread: int=10) -> int:
    return max(30, min(99, base + rng.randint(-spread, spread)))

def _apply_small_jitter(attrs: dict, rng: random.Random, amount: int = 3) -> dict:
    """
    Deterministic micro-variance to avoid clusters of identical prospects.
    Applied only at draft-class generation (not at promotion).
    """
    out = {}
    for k, v in attrs.items():
        if isinstance(v, int):
            out[k] = max(30, min(99, v + rng.randint(-amount, amount)))
        else:
            out[k] = v
    return out

def _archetype_base(pos: str) -> Dict[str, int]:
    return {
        "QB": {"overall":78,"awareness":75,"throw":78,"ath":70},
        "RB": {"overall":75,"awareness":60,"ath":80},
        "WR": {"overall":75,"awareness":62,"ath":82},
        "TE": {"overall":73,"awareness":65,"ath":74},
        "OL": {"overall":74,"awareness":70,"ath":62},
        "DL": {"overall":74,"awareness":65,"ath":74},
        "LB": {"overall":74,"awareness":66,"ath":74},
        "DB": {"overall":73,"awareness":65,"ath":78},
        "K":  {"overall":70,"awareness":68,"ath":50},
        "P":  {"overall":70,"awareness":68,"ath":50},
    }[pos]

def generate_draft_class(session: Session, season: int, seed: int = 2025) -> int:
    existing = session.exec(select(DraftClass).where(DraftClass.season == season)).first()
    if existing:  # idempotent: rebuild only if forced in future; here we just skip
        return len(session.exec(select(Prospect).where(Prospect.season==season)).all())
    rng = random.Random(seed)
    session.add(DraftClass(season=season, seed_used=seed, prospects=0))
    count = 0; idx = 1
    for pos, total in POS_DISTRIBUTION.items():
        base = _archetype_base(pos)
        for _ in range(total):
            name = _name_gen(rng, pos, idx); idx += 1
            # base rolls
            speed = _roll_attr(rng, base["ath"], spread=8)
            strength = _roll_attr(rng, 70 if pos in {"OL","DL","TE","LB"} else 60, spread=8)
            agility = _roll_attr(rng, base["ath"], spread=8)
            awareness = _roll_attr(rng, base["awareness"], spread=6)
            overall = _roll_attr(rng, base["overall"], spread=5)
            potential = _roll_attr(rng, 75, spread=15)
            # apply tiny deterministic jitter (±3) at generation time
            jittered = _apply_small_jitter({
                "overall": overall, "speed": speed, "strength": strength,
                "agility": agility, "awareness": awareness, "potential": potential
            }, rng, amount=3)
            session.add(Prospect(
                season=season, name=name, pos=pos,
                overall=jittered["overall"], speed=jittered["speed"], strength=jittered["strength"],
                agility=jittered["agility"], awareness=jittered["awareness"], potential=jittered["potential"]
            ))
            count += 1
    dc = session.exec(select(DraftClass).where(DraftClass.season==season)).first()
    dc.prospects = count
    session.add(dc); session.commit()
    return count

def draft_order_from_standings(session: Session, season: int) -> List[int]:
    rows = session.exec(select(TeamSeasonStats).where(TeamSeasonStats.season == season)).all()
    if not rows:
        # fallback to 1..32
        return list(range(1,33))
    # worst-to-best: fewer wins first; ties: more losses, then team_id
    rows_sorted = sorted(rows, key=lambda r: (r.wins, -r.losses, r.team_id))
    return [r.team_id for r in rows_sorted][:32]

def assign_picks(session: Session, season: int) -> int:
    session.exec(delete(DraftPick).where(DraftPick.season == season))
    order = draft_order_from_standings(session, season)
    total = 0; overall = 1
    for rnd in range(1, 8):
        for i, team_id in enumerate(order, start=1):
            session.add(DraftPick(
                season=season, round=rnd, pick_in_round=i, overall_pick=overall, team_id=team_id
            ))
            overall += 1; total += 1
    session.commit(); return total

def make_selection(session: Session, season: int, overall_pick: int, prospect_id: int, team_id: int) -> Dict[str, int]:
    pick = session.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==overall_pick)).first()
    if not pick: raise ValueError("Pick not found")
    if pick.prospect_id: raise ValueError("Pick already used")
    prospect = session.get(Prospect, prospect_id)
    if not prospect or prospect.season != season: raise ValueError("Prospect not found")
    if prospect.drafted_by_team_id: raise ValueError("Prospect already drafted")
    pick.prospect_id = prospect_id
    prospect.drafted_by_team_id = team_id
    prospect.drafted_overall_pick = overall_pick
    session.add(pick); session.add(prospect); session.commit()
    return {"overall_pick": overall_pick, "prospect_id": prospect_id, "team_id": team_id}
