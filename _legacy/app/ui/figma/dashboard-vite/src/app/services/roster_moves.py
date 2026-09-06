# app/services/roster_moves.py
from __future__ import annotations
from sqlmodel import Session, select
from app.models.core_min import Player
from app.models.contracts import Contract

def release_player(sess: Session, player_id: int):
    p = sess.get(Player, player_id)
    if not p:
        raise ValueError("PLAYER_NOT_FOUND")
    # end active contract
    c = sess.exec(select(Contract).where(Contract.player_id == player_id, Contract.is_active == True)).first()  # noqa: E712
    if c:
        c.is_active = False
        sess.add(c)
    # move to FA pool
    p.team_id = None
    p.trade_block = False
    sess.add(p)
    sess.commit()


