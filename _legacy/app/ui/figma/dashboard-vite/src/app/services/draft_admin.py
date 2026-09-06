from __future__ import annotations
from typing import Optional, Dict, Any, List
from sqlmodel import Session, select
from app.models.draft import DraftState, DraftPick
from app.models.trade_block import TeamTradeBlock, TradeBlockItemType

def draft_status(sess: Session, season: int) -> Dict[str, Any]:
    st = sess.get(DraftState, season)
    if not st:
        return {"exists": False}
    return {
        "exists": True, "is_active": st.is_active, "paused": getattr(st, "paused", False),
        "round": st.current_round, "slot": st.current_pick_slot
    }

def pause(sess: Session, season: int) -> Dict[str, Any]:
    st = sess.get(DraftState, season)
    if not st: return {"error": "no draft state"}
    setattr(st, "paused", True)  # tolerate column absence; NOT persisted if column missing
    st.is_active = False
    sess.add(st); sess.commit()
    return {"ok": True, "paused": True}

def resume(sess: Session, season: int) -> Dict[str, Any]:
    st = sess.get(DraftState, season)
    if not st: return {"error":"no draft state"}
    setattr(st, "paused", False)
    st.is_active = True
    sess.add(st); sess.commit()
    return {"ok": True, "paused": False}

def list_owned_picks(sess: Session, season: int, team_id: int) -> List[DraftPick]:
    return list(sess.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.owning_team_id==team_id).order_by(DraftPick.round, DraftPick.slot)))

def add_pick_to_block(sess: Session, season: int, team_id: int, round: int, slot: int, note: str = "") -> Dict[str, Any]:
    pk = sess.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.round==round, DraftPick.slot==slot)).first()
    if not pk or pk.owning_team_id != team_id:
        return {"error": "pick not owned"}
    row = TeamTradeBlock(season=season, team_id=team_id, item_type=TradeBlockItemType.PICK, round=round, slot=slot, note=note)
    sess.add(row); sess.commit()
    return {"ok": True, "trade_block_id": row.id}

def remove_pick_from_block(sess: Session, season: int, team_id: int, round: int, slot: int) -> Dict[str, Any]:
    row = sess.exec(select(TeamTradeBlock).where(TeamTradeBlock.season==season, TeamTradeBlock.team_id==team_id,
                                                 TeamTradeBlock.item_type==TradeBlockItemType.PICK,
                                                 TeamTradeBlock.round==round, TeamTradeBlock.slot==slot)).first()
    if not row: return {"ok": True}
    sess.delete(row); sess.commit()
    return {"ok": True}

def transfer_pick_ownership(sess: Session, season: int, round: int, slot: int, to_team_id: int) -> Dict[str, Any]:
    """Call this from your Trade Engine when a trade is accepted. Safe no-op if not found."""
    pk = sess.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.round==round, DraftPick.slot==slot)).first()
    if not pk: return {"error": "pick not found"}
    pk.owning_team_id = to_team_id
    sess.add(pk); sess.commit()
    # remove from any trade block rows where no longer owned
    stray = list(sess.exec(select(TeamTradeBlock).where(TeamTradeBlock.season==season,
                                                        TeamTradeBlock.item_type==TradeBlockItemType.PICK,
                                                        TeamTradeBlock.round==round, TeamTradeBlock.slot==slot)))
    for r in stray:
        if r.team_id != to_team_id:
            sess.delete(r)
    sess.commit()
    return {"ok": True}
