# app/services/rollover.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from pathlib import Path
import json, random
from sqlmodel import Session, select, delete
from app.models.core_min import Player
from app.models.rollover import RolloverAudit

RATING_MIN, RATING_MAX = 30, 99

def clamp(v:int, lo:int=RATING_MIN, hi:int=RATING_MAX) -> int:
    return max(lo, min(hi, v))

def _name(p: Player) -> str:
    fn = getattr(p,"first_name","") or ""
    ln = getattr(p,"last_name","") or ""
    nm = (fn + " " + ln).strip()
    return nm or getattr(p, "name", "")

def snapshot_league(session: Session, season: int) -> Dict[str, Any]:
    rows = session.exec(select(Player)).all()
    data = []
    for p in rows:
        data.append({
            "player_id": getattr(p,"player_id",getattr(p,"id",None)),
            "team_id": getattr(p,"team_id",None),
            "name": _name(p),
            "position": getattr(p,"position",getattr(p,"pos","")),
            "age": getattr(p,"age",0),
            "years_pro": getattr(p,"years_pro",0),
            "awareness": getattr(p,"awareness",0),
            "speed": getattr(p,"speed",0),
            "strength": getattr(p,"strength",0),
            "agility": getattr(p,"agility",0),
            "throw_power": getattr(p,"throw_power",0),
            "throw_accuracy": getattr(p,"throw_accuracy",0),
            "catching": getattr(p,"catching",0),
            "tackling": getattr(p,"tackling",0),
            "stamina": getattr(p,"stamina",0),
            "morale": getattr(p,"morale",0),
            "injury_proneness": getattr(p,"injury_proneness",0),
        })
    return {"season": season, "players": data, "count": len(data)}

def _retire_rule_simple(p: Player) -> bool:
    age = getattr(p, "age", 0)
    pot = getattr(p, "potential", 50)
    pos = (getattr(p,"position","") or "").upper()
    grace = 2 if pos in {"K","P"} else 0
    if age >= 35 + grace: 
        return True
    if age >= 33 + grace and pot <= 50:
        return True
    return False

def _apply_recovery(p: Player) -> None:
    # reset fatigue/lingering effects modestly
    st = clamp(int(getattr(p,"stamina",60)) + 5, 30, 99)
    mo = clamp(int(getattr(p,"morale",60)) + 3, 30, 99)
    setattr(p,"stamina", st)
    setattr(p,"morale", mo)

def apply_season_rollover(session: Session, from_season: int, to_season: int, *, seed:int=2025, retire_rule:str="simple", force:bool=False) -> Dict[str, Any]:
    # idempotency guard
    existing = session.exec(select(RolloverAudit).where(RolloverAudit.from_season==from_season, RolloverAudit.to_season==to_season)).first()
    if existing and not force:
        return {"status":"skipped","reason":"audit exists","audit_id":existing.id}

    rng = random.Random(seed)
    # snapshot before
    snap_before = snapshot_league(session, from_season)
    outdir = Path("data/rollovers")
    outdir.mkdir(parents=True, exist_ok=True)
    before_path = outdir / f"league_snapshot_before_{from_season}_to_{to_season}.json"
    before_path.write_text(json.dumps(snap_before, separators=(",",":")), encoding="utf-8")

    retired: List[int] = []
    players = session.exec(select(Player)).all()
    for p in players:
        # age & experience
        setattr(p, "age", int(getattr(p,"age",0)) + 1)
        setattr(p, "years_pro", int(getattr(p,"years_pro",0)) + 1)

        # recovery
        _apply_recovery(p)

        # retirement
        will_retire = _retire_rule_simple(p) if retire_rule=="simple" else False
        # tiny randomness: allow ±5% wiggle based on potential
        pot = int(getattr(p,"potential",50))
        if not will_retire and getattr(p,"age",0) >= 34 and rng.random() < max(0.0, (0.05 - (pot-50)/1000.0)):
            will_retire = True

        if will_retire:
            # mark as retired (non-destructive): free agent, stabilize ratings a bit
            setattr(p,"team_id", None)
            setattr(p,"morale", 50)
            setattr(p,"stamina", 50)
            retired.append(int(getattr(p,"player_id",getattr(p,"id",0))))
        session.add(p)

    session.flush()

    # snapshot after
    snap_after = snapshot_league(session, to_season)
    after_path = outdir / f"league_snapshot_after_{from_season}_to_{to_season}.json"
    after_path.write_text(json.dumps(snap_after, separators=(",",":")), encoding="utf-8")

    # write audit
    if existing and force:
        session.delete(existing)
        session.flush()

    audit = RolloverAudit(
        from_season=from_season, to_season=to_season, seed_used=seed,
        players_before=snap_before["count"], players_after=snap_after["count"],
        retired_count=len(retired), snapshot_path_before=str(before_path), snapshot_path_after=str(after_path),
        notes=f"retire_rule={retire_rule}"
    )
    session.add(audit)
    session.commit()

    return {
        "status":"ok",
        "audit_id":audit.id,
        "from":from_season,"to":to_season,
        "players_before":snap_before["count"],
        "players_after":snap_after["count"],
        "retired_count":len(retired),
        "snapshots":{"before":str(before_path),"after":str(after_path)}
    }
