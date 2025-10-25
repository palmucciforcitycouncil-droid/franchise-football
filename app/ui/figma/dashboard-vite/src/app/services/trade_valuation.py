# app/services/trade_valuation.py
from __future__ import annotations
from sqlmodel import Session
from app.models.core_min import Player
from app.services.contracts_service import current_contract, is_expiring, get_or_create_ask
from app.services.expiring_ai import is_more_willing_to_trade

def player_trade_value(sess: Session, player_id: int, season: int) -> int:
    """
    Return a rough 'value units' the owning team seeks.
    Baseline = OVR * age curve. If expiring+unlikely (on trade block), apply discount (e.g., -20%).
    """
    p = sess.get(Player, player_id)
    if not p or p.team_id is None:
        return 0
    base = int(p.rating * (1.0 + max(-0.2, min(0.2, (28 - p.age)/50.0))) * 100_000)  # Using p.rating instead of p.overall
    con = current_contract(sess, player_id)
    exp = con and is_expiring(sess, con, season)
    discount = 0.0
    if exp and is_more_willing_to_trade(sess, p.team_id, season, player_id):
        discount = 0.20  # 20% lower return ask if expiring + on trade block
    return max(100_000, int(base * (1.0 - discount)))


