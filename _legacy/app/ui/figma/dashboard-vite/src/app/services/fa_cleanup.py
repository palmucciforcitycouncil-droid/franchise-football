# app/services/fa_cleanup.py
from __future__ import annotations
from typing import Dict
from sqlmodel import Session, select, delete
from app.models.core_min import Player
from app.models.contracts import Contract

def drop_uifas_without_contracts(session: Session, season: int) -> Dict[str, int]:
    """
    End-of-season cleanup for UDFAs created this season:
    - Find Players with rookie_season == season AND team_id is None
    - If they have no active contract in this season nor any contract at all, delete them.
    Idempotent and safe for reruns.
    """
    removed = 0
    rows = session.exec(
        select(Player).where(
            getattr(Player, "rookie_season") == season,
            getattr(Player, "team_id") == None,  # noqa: E711
        )
    ).all()
    for pl in rows:
        pid = getattr(pl, "player_id", getattr(pl, "id", None))
        if pid is None:
            continue
        has_any_contract = session.exec(select(Contract).where(Contract.player_id == pid)).first()
        if not has_any_contract:
            session.delete(pl)
            removed += 1
    session.commit()
    return {"removed": removed}


