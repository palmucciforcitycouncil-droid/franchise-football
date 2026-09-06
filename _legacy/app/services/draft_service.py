from __future__ import annotations
from typing import List, Dict, Any, Optional
from random import Random
from sqlmodel import Session, select
from app.models.draft import Prospect, ProspectPosition, ScoutingReport, DraftBoard, DraftPick, DraftState
from app.models.player import Player
from app.models.contracts import PlayerContract

# ---------- Helpers ----------
POSITIONS = [p.value for p in ProspectPosition]
POS_NEEDS_WEIGHTS = {
    "QB":1.7,"WR":1.3,"RB":0.8,"TE":0.9,"LT":1.2,"G":1.0,"C":1.0,"RT":1.1,
    "EDGE":1.4,"DL":1.1,"LB":1.0,"CB":1.3,"S":1.0,"K":0.3,"P":0.2
}
ARCH_QB = ["Field General","Gunslinger","Scrambler"]
ARCH_WR = ["Deep Threat","Possession","YAC"]
ARCH_EDGE = ["Speed Rusher","Power Rusher","Hybrid"]
ARCH_GENERIC = ["Balanced","High Motor","Technician","Ballhawk","Road Grader","Mauler"]

def _rng(seed: int) -> Random:
    return Random(seed)

def _name(r: Random) -> str:
    first = ["Jalen","Evan","Micah","Caleb","Tyler","Noah","Aiden","Xavier","Jackson","Liam","Mason","Elijah","Kai","Owen","Logan","Wyatt"]
    last  = ["Harris","Johnson","Williams","Brown","Jones","Davis","Miller","Wilson","Moore","Taylor","Anderson","Thomas","Jackson","White"]
    return f"{r.choice(first)} {r.choice(last)}"

def _college(r: Random) -> str:
    schools = ["Alabama","Georgia","Ohio State","Michigan","USC","Texas","Oklahoma","LSU","Clemson","Notre Dame","Oregon","Washington","Florida State"]
    return r.choice(schools)

def _archetype_for(pos: str, r: Random) -> str:
    if pos=="QB": return r.choice(ARCH_QB)
    if pos=="WR": return r.choice(ARCH_WR)
    if pos=="EDGE": return r.choice(ARCH_EDGE)
    return r.choice(ARCH_GENERIC)

def _pos_distribution() -> List[str]:
    # rough class distribution
    return (["QB"]*4 + ["RB"]*14 + ["WR"]*22 + ["TE"]*10 + ["LT"]*6 + ["G"]*12 + ["C"]*6 + ["RT"]*6 +
            ["EDGE"]*18 + ["DL"]*14 + ["LB"]*14 + ["CB"]*18 + ["S"]*12 + ["K"]*2 + ["P"]*2)

def _overall_for(pos: str, r: Random) -> int:
    base = {
        "QB": (68,88), "WR": (62,84), "RB": (60,82), "TE": (60,82),
        "LT": (62,84), "G": (60,82), "C": (60,82), "RT": (62,84),
        "EDGE": (62,86), "DL": (60,84), "LB": (60,84), "CB": (62,86), "S": (60,84),
        "K": (58,76), "P": (58,76)
    }[pos]
    return r.randint(*base)

def _range(n:int, lo:int, hi:int, r:Random)->int:
    return max(lo, min(hi, n + r.randint(-3,3)))

# ---------- Generation ----------
def generate_draft_class(sess: Session, season: int, seed: int = 4242, size: int = 240) -> int:
    # idempotent: if prospects exist for season, return count
    existing = sess.exec(select(Prospect).where(Prospect.season==season)).first()
    if existing: 
        return sess.exec(select(Prospect).where(Prospect.season==season)).count()  # type: ignore

    r = _rng(seed + season*101)
    pool = _pos_distribution()
    r.shuffle(pool)
    pool = pool[:size]

    for pos in pool:
        ov = _overall_for(pos, r)
        p = Prospect(
            season=season,
            name=_name(r),
            pos=ProspectPosition(pos),
            age=r.randint(20,23),
            overall=ov,
            ceiling=_range(ov+5, ov, min(95, ov+12), r),
            floor=_range(ov-5, max(50, ov-12), ov, r),
            archetype=_archetype_for(pos, r),
            college=_college(r),
            speed=r.randint(55,90),
            strength=r.randint(55,90),
            agility=r.randint(55,90),
            iq=r.randint(55,90),
            volatility=r.randint(3,12)
        )
        sess.add(p)
    # picks (7 rounds * 32)
    for rnd in range(1,8):
        for slot in range(1,33):
            # initial ownership = slot as team_id 1..32; swap later via trades
            sess.add(DraftPick(season=season, round=rnd, slot=slot, owning_team_id=slot, original_team_id=slot))
    sess.add(DraftState(season=season, is_active=False, seed=seed))
    sess.commit()
    return size

# ---------- Queries ----------
def list_prospects(sess: Session, season: int, pos: Optional[str]=None) -> List[Prospect]:
    q = select(Prospect).where(Prospect.season==season)
    if pos: q = q.where(Prospect.pos==pos)  # type: ignore
    return list(sess.exec(q))

def team_scout_view(sess: Session, season: int, team_id: int, prospect_id: int) -> Dict[str,Any]:
    p = sess.get(Prospect, prospect_id)
    if not p: return {"error":"not found"}
    rep = sess.exec(select(ScoutingReport).where(ScoutingReport.season==season, ScoutingReport.team_id==team_id, ScoutingReport.prospect_id==prospect_id)).first()
    bias = rep.bias_overall if rep else 0
    conf = rep.confidence if rep else 70
    scouted = max(50, min(99, p.overall + bias))
    return {"prospect_id": p.prospect_id, "name": p.name, "pos": p.pos.value, "overall": p.overall,
            "scouted_overall": scouted, "confidence": conf, "archetype": p.archetype, "college": p.college,
            "speed": p.speed, "strength": p.strength, "agility": p.agility, "iq": p.iq,
            "floor": p.floor, "ceiling": p.ceiling}

def upsert_scouting(sess: Session, season: int, team_id: int, prospect_id: int, bias_overall: int, confidence: int, notes: str="") -> None:
    row = sess.exec(select(ScoutingReport).where(ScoutingReport.season==season, ScoutingReport.team_id==team_id, ScoutingReport.prospect_id==prospect_id)).first()
    if not row:
        row = ScoutingReport(season=season, team_id=team_id, prospect_id=prospect_id, bias_overall=bias_overall, confidence=confidence, notes=notes)
    else:
        row.bias_overall = bias_overall; row.confidence = confidence; row.notes = notes
    sess.add(row); sess.commit()

def set_draft_board(sess: Session, season: int, team_id: int, ordered_prospect_ids: List[int]) -> None:
    # wipe previous
    from app.models.draft import DraftBoard
    sess.exec(DraftBoard.delete().where(DraftBoard.season==season, DraftBoard.team_id==team_id))
    sess.commit()
    for i,pid in enumerate(ordered_prospect_ids, start=1):
        sess.add(DraftBoard(season=season, team_id=team_id, rank=i, prospect_id=pid))
    sess.commit()

def get_board(sess: Session, season: int, team_id: int) -> List[int]:
    rows = list(sess.exec(select(DraftBoard).where(DraftBoard.season==season, DraftBoard.team_id==team_id).order_by(DraftBoard.rank)))
    return [r.prospect_id for r in rows]

# ---------- Rookie contracts ----------
def _rookie_contract(round:int, slot:int) -> dict:
    # Super simple wage scale
    years = 4 if round <= 3 else 3
    base = 8_000_000 if round==1 else 4_000_000 if round<=3 else 1_200_000
    aav = int(base * (1.0 - (round-1)*0.12) * (1.0 - (slot-1)*0.01))
    return {"years": years, "aav": max(750_000, aav)}

# ---------- Team needs / AI pick ----------
def _team_pos_need(sess: Session, team_id: int) -> Dict[str,float]:
    from app.models.player import Player
    roster = list(sess.exec(select(Player).where(Player.team_id==team_id)))
    counts: Dict[str,int] = {}
    for p in roster:
        pos = getattr(p,"pos","")
        counts[pos] = counts.get(pos,0)+1
    needs: Dict[str,float] = {}
    for pos in POSITIONS:
        base_need = POS_NEEDS_WEIGHTS.get(pos,1.0)
        have = counts.get(pos,0)
        needs[pos] = base_need * (1.2 if have<1 else 1.0 if have<3 else 0.8)
    return needs

def _best_available(sess: Session, season: int, team_id: int) -> Optional[int]:
    # From board first; else BPA by (overall * need_weight)
    board = get_board(sess, season, team_id)
    undrafted = {p.prospect_id for p in list_prospects(sess, season) if p.drafted_by_team_id is None}
    # board top remaining
    for pid in board:
        if pid in undrafted:
            return pid
    # fallback BPA * need
    needs = _team_pos_need(sess, team_id)
    cand = [p for p in list_prospects(sess, season) if p.drafted_by_team_id is None]
    if not cand: return None
    cand.sort(key=lambda p: getattr(p,"overall",60) * needs.get(p.pos.value,1.0), reverse=True)
    return cand[0].prospect_id

# ---------- Draft lifecycle ----------
def start_draft(sess: Session, season: int, seed: int = 4242) -> None:
    st = sess.get(DraftState, season)
    if not st:
        st = DraftState(season=season, current_round=1, current_pick_slot=1, is_active=True, seed=seed)
    else:
        st.current_round = 1; st.current_pick_slot = 1; st.is_active = True; st.seed = seed
    sess.add(st); sess.commit()

def _advance(st: DraftState) -> None:
    st.current_pick_slot += 1
    if st.current_pick_slot > 32:
        st.current_pick_slot = 1
        st.current_round += 1
    if st.current_round > 7:
        st.is_active = False

def _materialize_player_from_prospect(sess: Session, prospect_id: int, team_id: int, season: int, round:int, slot:int):
    pr = sess.get(Prospect, prospect_id)
    if not pr: return
    # Create/convert to Player (keep ov, pos, age)
    pl = Player(name=pr.name, team_id=team_id, pos=pr.pos.value, age=pr.age, overall=pr.overall)
    sess.add(pl); sess.commit(); sess.refresh(pl)
    # rookie contract
    rc = _rookie_contract(round,slot)
    sess.add(PlayerContract(player_id=pl.player_id, team_id=team_id, start_season=season, end_season=season+rc["years"]-1, aav=rc["aav"], is_active=True))
    # mark prospect drafted
    pr.drafted_by_team_id = team_id; pr.drafted_round = round; pr.drafted_slot = slot
    sess.add(pr); sess.commit()

def pick_on_clock(sess: Session, season: int, team_id: int, prospect_id: int) -> dict:
    st = sess.get(DraftState, season)
    if not st or not st.is_active:
        return {"error":"draft not active"}
    # validate owner
    pk = sess.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.round==st.current_round, DraftPick.slot==st.current_pick_slot)).first()
    if not pk: return {"error":"pick not found"}
    if pk.owning_team_id != team_id:
        return {"error":"not your pick"}
    # validate prospect available
    pr = sess.get(Prospect, prospect_id)
    if not pr or pr.drafted_by_team_id is not None:
        return {"error":"prospect taken or invalid"}

    _materialize_player_from_prospect(sess, prospect_id, team_id, season, st.current_round, st.current_pick_slot)
    # Event
    try:
        from app.services.event_log_service import emit_event
        emit_event(sess, season=season, week=0, event_type="DRAFT_PICK",
                   team_id=team_id, player_id=None,
                   payload={"prospect_id": prospect_id, "round": st.current_round, "slot": st.current_pick_slot})
    except Exception:
        pass
    _advance(st); sess.add(st); sess.commit()
    return {"ok": True, "round": st.current_round, "slot": st.current_pick_slot, "next_active": st.is_active}

def cpu_pick(sess: Session, season: int) -> dict:
    st = sess.get(DraftState, season)
    if not st or not st.is_active:
        return {"error":"draft not active"}
    pk = sess.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.round==st.current_round, DraftPick.slot==st.current_pick_slot)).first()
    if not pk: return {"error":"pick not found"}
    pid = _best_available(sess, season, pk.owning_team_id)
    if pid is None: 
        _advance(st); sess.add(st); sess.commit()
        return {"ok": True, "auto_skipped": True}
    _materialize_player_from_prospect(sess, pid, pk.owning_team_id, season, st.current_round, st.current_pick_slot)
    try:
        from app.services.event_log_service import emit_event
        emit_event(sess, season=season, week=0, event_type="DRAFT_PICK",
                   team_id=pk.owning_team_id, payload={"prospect_id": pid, "round": st.current_round, "slot": st.current_pick_slot})
    except Exception:
        pass
    _advance(st); sess.add(st); sess.commit()
    return {"ok": True, "picked": pid}

def run_to_end(sess: Session, season: int, max_steps: int = 5000) -> dict:
    st = sess.get(DraftState, season)
    steps = 0
    while st and st.is_active and steps < max_steps:
        cpu_pick(sess, season)
        st = sess.get(DraftState, season); steps += 1
    return {"ok": True, "completed": (st and not st.is_active)}