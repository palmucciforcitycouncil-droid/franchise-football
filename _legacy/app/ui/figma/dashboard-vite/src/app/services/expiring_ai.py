# app/services/expiring_ai.py
from __future__ import annotations
from typing import List, Tuple
from random import Random
from sqlmodel import Session, select
from app.models.core_min import Player
from app.models.contracts import PlayerContract, PlayerContractAsk, TeamTradeBlock
from app.services.contracts_service import current_contract, is_expiring, get_or_create_ask

def _likelihood_to_resign(p: Player, ask: PlayerContractAsk) -> float:
    """0..1 probability team will meet the ask. Placeholder ties to OVR and age."""
    base = 0.5 + (p.rating - 50)/100.0  # Using p.rating instead of p.overall
    age_pen = 0.0 if 24 <= p.age <= 30 else (-0.1 if p.age > 31 else -0.05)
    price_pen = -min(0.25, max(0.0, (ask.desired_aav - 8_000_000)/20_000_000))  # Large asks reduce likelihood
    return max(0.0, min(1.0, base + age_pen + price_pen))

def preseason_sweep_mark_trade_block(sess: Session, season: int, rng: Random):
    """Run preseason AI to mark expiring players on trade block (≤25% cap)."""
    teams = {p.team_id for p in sess.exec(select(Player).where(Player.team_id != None))}
    for tid in teams:
        expiring = []
        for p in sess.exec(select(Player).where(Player.team_id == tid)):
            con = current_contract(sess, p.id)  # Using p.id instead of p.player_id
            if not con or not is_expiring(sess, con, season):
                continue
            ask = get_or_create_ask(sess, p.id, season)  # Using p.id instead of p.player_id
            pr = _likelihood_to_resign(p, ask)
            # Team makes internal offer if pr >= 0.6
            will_offer = pr >= 0.6
            accepted = False
            if will_offer:
                # Internal offer ~ 96% of ask; accept if meets min (same logic as FA)
                offered_aav = int(ask.desired_aav * 0.96)
                offered_years = max(1, ask.desired_years - 1)
                accepted = (offered_aav >= int(ask.desired_aav*0.96) and offered_years >= max(1, ask.desired_years-1))
            if not accepted:
                expiring.append(p.id)  # Using p.id instead of p.player_id

        # Cap: ≤25% of "unlikely-to-re-sign" go on the block
        rng.shuffle(expiring)
        max_on_block = max(0, int(len(expiring) * 0.25))
        pick = set(expiring[:max_on_block])
        # Write blocks
        for pid in expiring:
            is_blocked = pid in pick
            existing = sess.exec(select(TeamTradeBlock).where(
                TeamTradeBlock.season == season, TeamTradeBlock.team_id == tid, TeamTradeBlock.player_id == pid)).first()
            if not existing and is_blocked:
                sess.add(TeamTradeBlock(season=season, team_id=tid, player_id=pid, reason="EXPIRING_DECLINED", is_active=True))
            elif existing:
                existing.is_active = is_blocked
                sess.add(existing)
    sess.commit()

def is_more_willing_to_trade(sess: Session, team_id: int, season: int, player_id: int) -> bool:
    """Check if a team is more willing to trade a player (on trade block)."""
    tb = sess.exec(select(TeamTradeBlock).where(
        TeamTradeBlock.team_id == team_id, TeamTradeBlock.season == season, TeamTradeBlock.player_id == player_id,
        TeamTradeBlock.is_active == True)).first()
    return tb is not None


