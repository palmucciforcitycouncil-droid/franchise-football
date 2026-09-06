from __future__ import annotations
from typing import Dict, Any, List, Optional
from sqlmodel import Session, select

def _try(path: str, name: str):
    try:
        mod = __import__(path, fromlist=[name]); return getattr(mod, name)
    except Exception:
        return None

Player = _try("app.models.player", "Player")
PlayerContract = _try("app.models.contracts", "PlayerContract")
Team = _try("app.models.team", "Team")

DEFAULT_CAP = 225_000_000  # adjustable per season

def _active_contracts(sess: Session, team_id: int) -> List:
    if not PlayerContract: return []
    return list(sess.exec(select(PlayerContract).where(PlayerContract.team_id==team_id, PlayerContract.is_active==True)))  # noqa: E712

def _remaining_years(con, season: int) -> int:
    return max(0, getattr(con, "end_season", season) - season + 1)

def estimate_dead_cap_for_player(sess: Session, player_id: int, season: int) -> int:
    # MVP: 50% of remaining AAV across remaining years for active deal
    if not PlayerContract: return 0
    con = sess.exec(select(PlayerContract).where(PlayerContract.player_id==player_id, PlayerContract.is_active==True)).first()  # noqa: E712
    if not con: return 0
    yrs = _remaining_years(con, season)
    return int(0.5 * yrs * getattr(con, "aav", 0))

def team_cap_summary(sess: Session, season: int, team_id: int, cap: Optional[int] = None) -> Dict[str, Any]:
    cap_limit = int(cap or DEFAULT_CAP)
    active = _active_contracts(sess, team_id)
    active_aav = sum(int(getattr(c, "aav", 0)) for c in active)
    # Rough dead cap: for players not on team anymore but with inactive contract? (Optional future)
    # MVP: compute only on pending cuts in UI preview; here keep 0 and let release endpoint recompute as needed
    dead_cap = 0
    used = active_aav + dead_cap
    space = cap_limit - used
    return {
        "season": season,
        "team_id": team_id,
        "cap_limit": cap_limit,
        "active_aav": active_aav,
        "dead_cap": dead_cap,
        "cap_used": used,
        "cap_space": space
    }

def can_afford(sess: Session, season: int, team_id: int, added_aav: int, cap: Optional[int] = None) -> bool:
    s = team_cap_summary(sess, season, team_id, cap)
    return (s["cap_space"] - int(added_aav)) >= 0

def roster_size(sess: Session, team_id: int) -> int:
    if not Player: return 0
    return len(list(sess.exec(select(Player).where(Player.team_id==team_id))))

def roster_has_room(sess: Session, team_id: int, max_size: int = 53) -> bool:
    return roster_size(sess, team_id) < max_size
