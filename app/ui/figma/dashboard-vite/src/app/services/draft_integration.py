# app/services/draft_integration.py
from __future__ import annotations
from typing import Dict, Any, Tuple, List
import random

from sqlmodel import Session, select

from app.models.draft import Prospect, DraftPick
from app.models.core_min import Player
from app.models.contracts import Contract

RATING_MIN, RATING_MAX = 30, 99

def _clamp(v: int, lo: int = RATING_MIN, hi: int = RATING_MAX) -> int:
    return max(lo, min(hi, v))

def _to_player_attrs_from_prospect(pos: str, p: Prospect, jitter: int = 0, rng: random.Random | None = None) -> Dict[str, int]:
    """
    Map Prospect → Player ratings. Uses position to decide where to place throwing/catching/tackling weight.
    A tiny ±jitter is applied deterministically via rng to avoid ties (kept within clamps).
    """
    def j(x: int) -> int:
        if not rng or jitter <= 0: return x
        return _clamp(x + rng.randint(-jitter, jitter))

    pos = (pos or "").upper()
    base = {
        "awareness": p.awareness,
        "speed": p.speed,
        "strength": p.strength,
        "agility": p.agility,
        "stamina": _clamp(60 + (p.agility + p.speed)//20),
        "morale": 70,
        "throw_power": 50,
        "throw_accuracy": 50,
        "catching": 50,
        "tackling": 50,
    }

    if pos == "QB":
        base["throw_power"] = _clamp(int(0.65*p.overall + 0.35*p.speed))
        base["throw_accuracy"] = _clamp(int(0.7*p.overall + 0.3*p.awareness))
        base["catching"] = 40
        base["tackling"] = 40
    elif pos in {"WR", "TE"}:
        base["catching"] = _clamp(int(0.6*p.overall + 0.4*p.awareness))
        base["throw_power"] = 40; base["throw_accuracy"] = 40
        base["tackling"] = 45 if pos == "TE" else 40
    elif pos == "RB":
        base["catching"] = _clamp(int(0.3*p.overall + 0.2*p.awareness))
        base["tackling"] = 45
        base["throw_power"] = 35; base["throw_accuracy"] = 35
    elif pos in {"OL"}:
        base["tackling"] = _clamp(int(0.3*p.overall + 0.5*p.strength))
        base["catching"] = 35; base["throw_power"] = 30; base["throw_accuracy"] = 30
    elif pos in {"DL", "LB"}:
        base["tackling"] = _clamp(int(0.6*p.overall + 0.4*p.strength))
        base["catching"] = 40; base["throw_power"] = 30; base["throw_accuracy"] = 30
    elif pos in {"DB"}:
        base["tackling"] = _clamp(int(0.4*p.overall + 0.4*p.agility))
        base["catching"] = _clamp(int(0.3*p.overall + 0.3*p.awareness))
        base["throw_power"] = 30; base["throw_accuracy"] = 30
    elif pos in {"K", "P"}:
        base["awareness"] = _clamp(int(0.6*p.overall + 0.4*p.awareness))
        base["catching"] = 30; base["tackling"] = 30
        base["throw_power"] = 30; base["throw_accuracy"] = 30

    # jitter is now applied only at draft generation; promotion leaves attributes as mapped
    for k in list(base.keys()):
        base[k] = int(base[k])
    return base

def _rookie_wage_scale(rnd: int, overall_pick: int) -> Tuple[int, int]:
    """
    Very simple rookie scale:
    - Round 1: 4 years, AAV descending from ~900 to ~500
    - Round 2: 4 years, ~400 to ~300
    - R3-4: 4 years, ~250 to ~150
    - R5-7: 4 years, ~120 to ~80
    """
    if rnd == 1:
        years = 4
        aav = 900 - (overall_pick-1) * 12  # simple slope
    elif rnd == 2:
        years = 4
        aav = 420 - (overall_pick-32-1) * 4
    elif rnd in {3,4}:
        years = 4
        aav = 250 - max(0, (overall_pick-64)) // 4
    else:
        years = 4
        aav = 120 - max(0, (overall_pick-96)) // 6
    return years, max(80, int(aav))

def _ensure_player_fields(p: Player, attrs: Dict[str, int]) -> None:
    for k, v in attrs.items():
        if hasattr(p, k):
            setattr(p, k, v)

def finalize_draft_class(session: Session, season: int, seed: int = 2025) -> Dict[str, Any]:
    """
    Promote drafted prospects of given season into core Players and assign rookie contracts.
    Idempotent: if a prospect already became a Player (matched by drafted_overall_pick), we skip.
    """
    rng = random.Random(seed)

    picks = session.exec(select(DraftPick).where(DraftPick.season == season).order_by(DraftPick.overall_pick)).all()
    if not picks:
        return {"status": "no_picks"}

    created_players = 0
    created_contracts = 0

    for pick in picks:
        if not pick.prospect_id:
            continue
        pr: Prospect | None = session.get(Prospect, pick.prospect_id)
        if not pr:
            continue
        if pr.drafted_by_team_id is None:
            # safety: align the prospect with pick team if missing
            pr.drafted_by_team_id = pick.team_id
            pr.drafted_overall_pick = pick.overall_pick

        # Check if a Player already exists for this prospect (idempotency heuristic):
        # Look for a Player with the same name on the same team
        already_promoted = False
        
        existing_player = session.exec(
            select(Player).where(
                Player.team_id == pr.drafted_by_team_id,
                Player.name == pr.name
            )
        ).first()
        
        if existing_player:
            # Check if this player has rookie flags for this season
            if (hasattr(existing_player, "is_rookie") and existing_player.is_rookie) or \
               (hasattr(existing_player, "rookie_season") and existing_player.rookie_season == season):
                already_promoted = True

        if already_promoted:
            continue

        # Create Player
        pl = Player()
        # Names: we already have deterministic Prospect names; copy to Player.name or first/last if present
        if hasattr(pl, "name"):
            setattr(pl, "name", pr.name)
        else:
            if hasattr(pl, "first_name") and hasattr(pl, "last_name"):
                # split best-effort
                parts = pr.name.split(" ", 1)
                setattr(pl, "first_name", parts[0])
                if len(parts) > 1:
                    setattr(pl, "last_name", parts[1])

        # Map ratings
        attrs = _to_player_attrs_from_prospect(pr.pos, pr, jitter=1, rng=rng)
        _ensure_player_fields(pl, attrs)

        # Position / team / meta
        if hasattr(pl, "position"):
            pl.position = pr.pos
        elif hasattr(pl, "pos"):
            pl.pos = pr.pos
        if hasattr(pl, "team_id"):
            pl.team_id = pr.drafted_by_team_id or pick.team_id
        if hasattr(pl, "age"):
            pl.age = 22
        if hasattr(pl, "potential"):
            pl.potential = pr.potential
        if hasattr(pl, "is_rookie"):
            pl.is_rookie = True
        if hasattr(pl, "rookie_season"):
            pl.rookie_season = season

        session.add(pl)
        session.flush()  # get player_id

        # Contract
        rnd = pick.round
        years, aav = _rookie_wage_scale(rnd, pick.overall_pick)
        c = Contract(
            player_id=getattr(pl, "player_id", getattr(pl, "id", None)),
            team_id=pl.team_id,
            start_season=season,
            years=years,
            aav=aav,
            is_rookie=True,
        )
        session.add(c)

        created_players += 1
        created_contracts += 1

    session.commit()
    return {"status": "ok", "players_created": created_players, "contracts_created": created_contracts}
