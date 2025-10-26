from __future__ import annotations
from typing import Dict, Any, List, Tuple
from sqlmodel import Session, select
from math import exp

def _try(path: str, name: str):
    try:
        mod = __import__(path, fromlist=[name]); return getattr(mod, name)
    except Exception:
        return None

Player = _try("app.models.player", "Player")
PlayerContract = _try("app.models.contract_models", "PlayerContract")
Team = _try("app.models.team", "Team")
DraftPick = _try("app.models.draft", "DraftPickInventory")

from app.services.team_needs_service import team_needs

# --- Draft pick chart (tunable; relative points) ---
# Round 1 slots ~ 3000..600, Round 2 ~ 500..200, then taper
PICK_CHART = {
    1: [3000, 2600, 2400, 2200, 2000, 1900, 1800, 1700, 1600, 1500, 1400, 1300, 1200, 1100, 1000, 900, 850, 800, 750, 700, 660, 620, 580, 540, 500, 470, 440, 410, 380, 350, 320, 300],
    2: [550, 520, 500, 480, 460, 440, 420, 400, 380, 360, 340, 320, 300, 280, 265, 250, 235, 220, 205, 190, 180, 170, 160, 150, 140, 130, 120, 112, 104, 96, 90, 84],
    3: [80]*32, 4: [45]*32, 5:[28]*32, 6:[15]*32, 7:[8]*32
}

def _pick_value(round:int, slot:int) -> float:
    return float(PICK_CHART.get(round, [0]*32)[min(max(slot,1),32)-1])

# --- Player value components (MVP, tunable) ---
def _age_curve(age:int) -> float:
    # Peak 26–29, slight drop before/after
    if age <= 21: return 0.75
    if age <= 24: return 0.9
    if age <= 25: return 0.95
    if 26 <= age <= 29: return 1.0
    if 30 <= age <= 31: return 0.92
    if 32 <= age <= 34: return 0.84
    return 0.75

def _contract_surplus(aav:int, overall:int) -> float:
    # Rough $ per OVR benchmark (tunable)
    fair = max(1_000_000, int(overall * 500_000))
    return (fair - aav) / 1_000_000.0  # positive = team-friendly

def _expiring_discount(sess: Session, season: int, player_id: int) -> float:
    """
    If player unlikely to re-sign with current team: discount their value to the holding team.
    """
    try:
        from app.services.expiring_contracts import unlikely_to_resign
        flag = unlikely_to_resign(sess, season, player_id)
        return 0.85 if flag else 1.0
    except Exception:
        return 1.0

def player_trade_value(sess: Session, season: int, player_id: int, acquiring_team_id: int) -> float:
    p = sess.get(Player, player_id)
    if not p: return 0.0
    ov = getattr(p, "overall", 60)
    age = getattr(p, "age", 26)
    base = ov * 50.0 * _age_curve(age)  # 80 OVR ~ 4000 pts before modifiers (scaled to match pick values)

    # current AAV (active deal) + ask
    con = sess.exec(select(PlayerContract).where(PlayerContract.player_id==player_id, PlayerContract.is_active==True)).first()  # noqa: E712
    aav = getattr(con, "aav", 0) if con else 0
    surplus = _contract_surplus(aav, ov)

    # team need multiplier (acquiring team)
    needs = team_needs(sess, season, acquiring_team_id)
    pos = getattr(p, "pos", "")
    need_mult = 1.15 if (pos in needs and bool(needs[pos]["need"])) else 1.0

    # expiring discount for the holder lowers what they can demand
    hold_disc = _expiring_discount(sess, season, player_id)

    return max(0.0, base * (1.0 + 0.1*surplus) * need_mult * hold_disc)

def picks_value_total(picks: List[dict]) -> float:
    return sum(_pick_value(int(x["round"]), int(x["slot"])) for x in picks or [])

def players_value_total(sess: Session, season: int, players: List[int], acquiring_team_id: int) -> float:
    return sum(player_trade_value(sess, season, pid, acquiring_team_id) for pid in players or [])

def side_value(sess: Session, season: int, *, from_team_id:int, to_team_id:int, assets:dict) -> float:
    # Value SENT by from_team as received by to_team (so we evaluate fit for the recipient)
    return players_value_total(sess, season, assets.get("players", []), to_team_id) + picks_value_total(assets.get("picks", []))
