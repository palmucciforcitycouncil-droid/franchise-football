# app/services/preseason_ai.py
from __future__ import annotations
import random
from sqlmodel import Session, select
from app.models.core_min import Player
from app.models.contracts import Contract
from app.services.negotiation_logic import ai_offer_for_player, player_accepts

def run_preseason_expiring_contract_logic(sess: Session, team_id: int, season: int, team_cap_space: int, rng: random.Random):
    """
    For all expiring players on team:
      - Decide if the team would likely pay.
      - If not likely to pay, make a deterministic offer.
      - If offer would be declined, add player to a candidate list.
      - Mark up to 25% of that candidate list as trade_block=True (random choice).
    """
    expiring = sess.exec(
        select(Player, Contract)
        .join(Contract, Contract.player_id == Player.id)
        .where(Player.team_id == team_id, Contract.team_id == team_id, Contract.is_active == True, Contract.end_season == season)  # noqa: E712
    ).all()

    candidates = []
    for p, _c in expiring:
        dec = ai_offer_for_player(p, team_cap_space)
        if not dec.will_pay:
            # team isn't inclined; still may make a low offer
            if not player_accepts(dec.offered_aav, dec.offered_years, p):
                candidates.append(p.id)

    # cap at 25%
    cap = max(0, int(len(candidates) * 0.25))
    rng.shuffle(candidates)
    trade_list = set(candidates[:cap])

    for p, _c in expiring:
        previously_block = p.trade_block
        p.trade_block = (p.id in trade_list)
        if p.trade_block != previously_block:
            sess.add(p)

    sess.commit()

def expiring_trade_value_discount(player: Player) -> float:
    """
    Discount factor used in trade valuations when team is unlikely to re-sign player.
    If player is trade_block True → deeper discount. (0.85 vs 0.92)
    """
    if player.trade_block:
        return 0.85
    return 0.92


