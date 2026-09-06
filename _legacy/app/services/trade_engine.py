from __future__ import annotations
from typing import Dict, Any, List, Tuple
from sqlmodel import Session, select
from app.models.trade import TradeProposal, TradeStatus
from app.models.trade_block import TeamTradeBlock, TradeBlockItemType
# Note: Using DraftPickInventory as the table name
from app.models.draft import DraftPickInventory as DraftPick
from app.models.player import Player
from app.services.trade_value import side_value
from app.services.cap_compliance import can_afford, roster_has_room
from app.services.draft_admin import transfer_pick_ownership
from app.services.event_log_service import emit_event

MAX_ASSETS_PER_SIDE = 6
FAIR_BAND = 0.75, 1.33   # accept if 0.75 <= from_value/to_value <= 1.33 (wider fair band)
COUNTER_BAND = 0.60, 1.67  # else try a counter if within wider band

def _validate_assets(sess: Session, season:int, team_id:int, assets:dict) -> Tuple[bool,str]:
    # Ensure ownership
    # Players: on team
    for pid in assets.get("players", []):
        p = sess.get(Player, pid)
        if not p or getattr(p, "team_id", None) != team_id:
            return False, f"Player {pid} not owned by team {team_id}"
    # Picks: owned
    for pk in assets.get("picks", []):
        row = sess.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.round==pk["round"], DraftPick.slot==pk["slot"])).first()
        if not row or row.owning_team_id != team_id:
            return False, f"Pick R{pk['round']}-S{pk['slot']} not owned by team {team_id}"
    if len(assets.get("players", [])) + len(assets.get("picks", [])) > MAX_ASSETS_PER_SIDE:
        return False, "Too many assets on one side"
    return True, ""

def _cap_roster_checks(sess: Session, season:int, acquire_team_id:int, incoming_players:List[int], incoming_aav:int=0) -> Tuple[bool,str]:
    # roster
    if not roster_has_room(sess, acquire_team_id):
        return False, "Roster full (53)"
    # cap (sum AAV of incoming active deals)
    aav_sum = incoming_aav
    from app.models.contract_models import PlayerContract
    for pid in incoming_players:
        con = sess.exec(select(PlayerContract).where(PlayerContract.player_id==pid, PlayerContract.is_active==True)).first()  # noqa: E712
        aav_sum += getattr(con, "aav", 0) if con else 0
    if not can_afford(sess, season, acquire_team_id, aav_sum):
        return False, "Cap space insufficient"
    return True, ""

def evaluate(sess: Session, *, season:int, from_team_id:int, to_team_id:int, from_assets:dict, to_assets:dict) -> Dict[str,Any]:
    ok,msg = _validate_assets(sess, season, from_team_id, from_assets); 
    if not ok: return {"error": msg}
    ok,msg = _validate_assets(sess, season, to_team_id, to_assets); 
    if not ok: return {"error": msg}

    # Values as perceived by each recipient
    val_to = side_value(sess, season, from_team_id=from_team_id, to_team_id=to_team_id, assets=from_assets)
    val_from = side_value(sess, season, from_team_id=to_team_id, to_team_id=from_team_id, assets=to_assets)
    ratio = (val_to / max(1.0, val_from)) if val_from > 0 else 999.0

    return {"from_value": round(val_to,2), "to_value": round(val_from,2), "ratio": round(ratio,3)}

def propose(sess: Session, *, season:int, from_team_id:int, to_team_id:int, from_assets:dict, to_assets:dict) -> Dict[str,Any]:
    ev = evaluate(sess, season=season, from_team_id=from_team_id, to_team_id=to_team_id, from_assets=from_assets, to_assets=to_assets)
    if "error" in ev: return ev
    ratio = ev["ratio"]
    lo, hi = FAIR_BAND

    # Basic cap/roster pre-checks for each side (approx incoming assets)
    from_incoming_players = to_assets.get("players", [])
    to_incoming_players = from_assets.get("players", [])
    ok,msg = _cap_roster_checks(sess, season, from_team_id, from_incoming_players); 
    if not ok: return {"error": f"From team: {msg}"}
    ok,msg = _cap_roster_checks(sess, season, to_team_id, to_incoming_players); 
    if not ok: return {"error": f"To team: {msg}"}

    if lo <= ratio <= hi:
        status = TradeStatus.PENDING
        message = "Offer within fair band. Counterparty likely to accept."
    elif (COUNTER_BAND[0] <= ratio < lo) or (hi < ratio <= COUNTER_BAND[1]):
        status = TradeStatus.COUNTER
        message = "Offer close. Counter suggested."
    else:
        status = TradeStatus.REJECTED
        message = "Far from fair value."

    tp = TradeProposal(
        season=season, from_team_id=from_team_id, to_team_id=to_team_id,
        from_assets=from_assets, to_assets=to_assets,
        from_value=ev["from_value"], to_value=ev["to_value"], status=status, message=message
    )
    sess.add(tp); sess.commit(); sess.refresh(tp)
    return {"ok": True, "proposal_id": tp.id, "status": tp.status.value, "message": tp.message, **ev}

def _apply_player_transfer(sess: Session, player_id:int, to_team_id:int):
    p = sess.get(Player, player_id)
    if p:
        p.team_id = to_team_id
        sess.add(p)

def _apply_pick_transfer(sess: Session, season:int, rnd:int, slot:int, to_team_id:int):
    transfer_pick_ownership(sess, season, rnd, slot, to_team_id)

def accept(sess: Session, *, proposal_id:int) -> Dict[str,Any]:
    tp = sess.get(TradeProposal, proposal_id)
    if not tp: return {"error": "Proposal not found"}
    if tp.status in (TradeStatus.ACCEPTED, TradeStatus.REJECTED):
        return {"error": f"Already {tp.status.value}"}

    season = tp.season
    # Final cap/roster checks
    ok,msg = _cap_roster_checks(sess, season, tp.from_team_id, tp.to_assets.get("players", []))
    if not ok: return {"error": f"From team: {msg}"}
    ok,msg = _cap_roster_checks(sess, season, tp.to_team_id, tp.from_assets.get("players", []))
    if not ok: return {"error": f"To team: {msg}"}

    # Apply transfers
    for pid in tp.from_assets.get("players", []):
        _apply_player_transfer(sess, pid, tp.to_team_id)
    for pk in tp.from_assets.get("picks", []):
        _apply_pick_transfer(sess, season, pk["round"], pk["slot"], tp.to_team_id)

    for pid in tp.to_assets.get("players", []):
        _apply_player_transfer(sess, pid, tp.from_team_id)
    for pk in tp.to_assets.get("picks", []):
        _apply_pick_transfer(sess, season, pk["round"], pk["slot"], tp.from_team_id)

    sess.commit()
    tp.status = TradeStatus.ACCEPTED; tp.message = "Trade finalized"
    sess.add(tp); sess.commit()

    # Events
    emit_event(sess, season=season, week=0, event_type="TRADE_ACCEPTED",
               team_id=tp.from_team_id, payload={"proposal_id": tp.id})
    emit_event(sess, season=season, week=0, event_type="TRADE_ACCEPTED",
               team_id=tp.to_team_id, payload={"proposal_id": tp.id})

    return {"ok": True, "proposal_id": tp.id, "status": tp.status.value}

def list_trade_block(sess: Session, season:int) -> Dict[str,Any]:
    rows = list(sess.exec(select(TeamTradeBlock).where(TeamTradeBlock.season==season)))
    out = {"players": [], "picks": []}
    for r in rows:
        if r.item_type == TradeBlockItemType.PLAYER:
            out["players"].append({"team_id": r.team_id, "player_id": r.player_id, "note": r.note})
        elif r.item_type == TradeBlockItemType.PICK:
            out["picks"].append({"team_id": r.team_id, "round": r.round, "slot": r.slot, "note": r.note})
    return out
