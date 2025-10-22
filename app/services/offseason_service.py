from typing import List, Tuple, Dict
from sqlmodel import Session
from dataclasses import dataclass
from app.engine.rng import RNG
from app.models.sim_models import SimTeam
from app.models.player_models import Player, DepthChart
from app.models.contract_models import PlayerContract, CapSummary
from app.models.season_models import Season
from app.services.import_service import rebuild_depth_charts
from app.services.needs_service import CORE_STARTERS, top_needs, need_score
from app.services.standings_service import league_order_worst_to_best
from pathlib import Path

# --- Retirement model (position bands + skill + FA timeout) ---
_POS_AGE_BANDS = {
    # Typical retirement-pressure "start" and "steep" ages per position (approximate)
    "RB":  {"start":27, "steep":29},   # earliest
    "WR":  {"start":28, "steep":31},
    "TE":  {"start":28, "steep":31},
    "CB":  {"start":28, "steep":31},
    "S":   {"start":29, "steep":32},
    "LB":  {"start":29, "steep":32},
    "DL":  {"start":29, "steep":32},
    "OL":  {"start":30, "steep":33},
    "QB":  {"start":32, "steep":36},   # latest among non-kickers
    "K":   {"start":34, "steep":38},
    "P":   {"start":34, "steep":38},
    "RET": {"start":27, "steep":29}
}

def _retire_probability(pos: str, age: int, ovr: int) -> float:
    band = _POS_AGE_BANDS.get(pos, {"start":29,"steep":32})
    start = band["start"]; steep = band["steep"]
    base = 0.0
    if age >= start:
        base += 0.05 + 0.03*max(0, age - start)         # ramp after start
    if age >= steep:
        base += 0.08 + 0.04*max(0, age - steep)         # steep ramp
    if ovr < 60:
        base += 0.05                                    # skills decline
    return min(0.95, max(0.0, base))

def _mark_fa_since(session: Session, season: int):
    # Ensure FA players have fa_since_season stamped
    fa_rows = session.query(Player).filter(Player.team_id==0).all()
    for p in fa_rows:
        if p.fa_since_season is None:
            p.fa_since_season = season
            session.add(p)
    session.commit()

def retirements(session: Session, season: int, rng: RNG) -> List[int]:
    retired: List[int] = []
    _mark_fa_since(session, season)  # set stamps for current FAs

    players = session.query(Player).all()
    for p in players:
        # auto-retire FAs who spent a full prior season in FA
        if p.team_id == 0 and p.fa_since_season is not None and p.fa_since_season <= season-1:
            p.is_active = False
            session.add(p)
            deals = session.query(PlayerContract).filter(PlayerContract.player_id==p.id, PlayerContract.is_active==True).all()
            for d in deals:
                d.is_active = False; session.add(d)
            retired.append(p.id)
            continue

        if p.team_id <= 0:  # ignore prospects pool or already FA this season
            continue

        prob = _retire_probability(p.pos, p.age, p.ovr)
        if rng.prob(prob):
            p.team_id = 0
            p.fa_since_season = season
            p.is_active = False
            session.add(p)
            deals = session.query(PlayerContract).filter(PlayerContract.player_id==p.id, PlayerContract.is_active==True).all()
            for d in deals:
                d.is_active = False; session.add(d)
            retired.append(p.id)

    session.commit()
    return retired

# --- Progression/Regression ---
def progression(session: Session, season: int, rng: RNG) -> List[int]:
    """
    Age curve:
      <24: +1..+4 tilted by potential
      24..27: +0..+2
      28..30: -1..+1
      31..35: -1..-3
      36+: -2..-5
    Potential scales the positive side; variance small & deterministic.
    """
    changed: List[int] = []
    players = session.query(Player).filter(Player.team_id>0).all()
    for p in players:
        if not p.is_active:  # still count inactive if on roster
            pass
        pot = p.potential
        delta = 0
        r = rng.r()
        if p.age < 24:
            delta = int(1 + r.random()*min(4, 1 + pot/30))
        elif p.age <= 27:
            delta = int(r.random()*2)
        elif p.age <= 30:
            delta = int(-1 + r.random()*2)  # -1..+0 or -1..+1
        elif p.age <= 35:
            delta = -1 - int(r.random()*2)  # -1..-3
        else:
            delta = -2 - int(r.random()*3)  # -2..-5
        p.ovr = int(max(40, min(99, p.ovr + delta)))
        p.age += 1
        p.is_rookie = False
        session.add(p)
        changed.append(p.id)
    session.commit()
    return changed

# --- Draft: worst→best each round (7 rounds) ---
POS_POOL = ["QB","RB","WR","TE","OL","DL","LB","CB","S","K","P"]

def _rookie_aav(pick_no: int) -> int:
    base = 900_000
    step = max(0, 240_000 - (pick_no//32)*30_000)
    return base + step

def generate_prospects(rng: RNG, total: int = 224) -> List[Player]:
    prospects: List[Player] = []
    for i in range(total):
        pos = rng.choice(POS_POOL)
        ovr = int(max(55, min(88, rng.gauss(72, 6))))
        age = 21 + int(rng.r().random()*2)
        pot = int(max(50, min(95, rng.gauss(78, 8))))
        p = Player(team_id=-1, first="R", last=f"Prospect{i+1}", pos=pos, ovr=ovr, age=age, potential=pot, is_active=True, is_rookie=True)
        prospects.append(p)
    return prospects

def draft(session: Session, season: int, rng: RNG) -> List[Tuple[int,int]]:
    # Make/grow the prospect pool
    prospects = generate_prospects(rng)
    for p in prospects: session.add(p)
    session.commit()

    picks: List[Tuple[int,int]] = []
    order_worst_to_best = league_order_worst_to_best(session, season)  # <-- NEW ORDER (worst first)
    pick_no = 0
    for rnd in range(7):
        for tid in order_worst_to_best:
            pick_no += 1
            needs = need_score(session, tid)
            pool = session.query(Player).filter(Player.team_id==-1).all()
            best = None; best_val = -999
            for p in pool:
                val = p.ovr + 8.0*needs.get(p.pos, 0.0)
                if val > best_val:
                    best, best_val = p, val
            if best is None: 
                continue
            best.team_id = tid
            session.add(PlayerContract(player_id=best.id, team_id=tid, years=4, aav=_rookie_aav(pick_no)))
            session.add(best)
            picks.append((tid, best.id))
        session.commit()
    return picks

# --- Free Agency ---
def free_agency(session: Session, season: int, rng: RNG):
    """
    Simple: teams try to sign best FA at top need if they have cap room.
    """
    teams = session.query(SimTeam).all()
    for t in teams:
        needs = top_needs(session, t.id, k=2)
        cap = session.query(CapSummary).filter(CapSummary.team_id==t.id).first()
        space = max(0, (cap.cap_limit if cap else 240_000_000) - (cap.committed if cap else 0))
        for need in needs:
            fa = session.query(Player).filter(Player.team_id==0).first()  # retirees are 0; create extra FA below
            if not fa:
                fa = session.query(Player).filter(Player.team_id==-1).first()  # prospects not drafted or created FA
            if not fa: break
            ask = int(800_000 + fa.ovr*20_000)
            if ask <= space:
                fa.team_id = t.id
                session.add(PlayerContract(player_id=fa.id, team_id=t.id, years=1, aav=ask))
                space -= ask
                session.add(fa)
    session.commit()

def rebuild_caps(session: Session):
    from app.services.import_service import rebuild_caps as _caps
    _caps(session)

# --- Orchestrator ---
@dataclass
class OffseasonResult:
    retired: int
    progressed: int
    drafted: int

def run_offseason(session: Session, season: int, seed: int) -> OffseasonResult:
    rng = RNG.with_seed(seed*104729 + season)
    # 1) Retirements
    retired_ids = retirements(session, season, rng)
    # 2) Progression/Regression (+ age up)
    progressed_ids = progression(session, season, rng)
    # 3) Draft (create prospects; assign; rookie contracts)
    picks = draft(session, season, rng)
    # 4) Free agency (very simple)
    free_agency(session, season, rng)
    # 5) Rebuild depth & caps
    rebuild_depth_charts(session)
    rebuild_caps(session)
    # Update Phase
    s = session.query(Season).filter(Season.season==season).first()
    if s: 
        s.phase = "offseason"
        session.add(s); session.commit()
    return OffseasonResult(retired=len(retired_ids), progressed=len(progressed_ids), drafted=len(picks))
