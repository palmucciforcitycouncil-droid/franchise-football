from __future__ import annotations
from typing import List, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db import get_session
from app.models.trade import TradeProposal, TradeItem, TradeItemType, TradeStatus
from app.services.trade_service import (
    evaluate_trade, ai_counter, accept_trade, reject_trade,
    get_trade_details, list_team_trades, get_trade_history
)
from app.services.trade_value import bundle_value, calculate_trade_balance

router = APIRouter(prefix="/api/v1/trades", tags=["trades"])

class TradeCreateReq(BaseModel):
    season: int
    from_team_id: int
    to_team_id: int
    from_players: List[int] = []
    from_picks: List[int] = []
    to_players: List[int] = []
    to_picks: List[int] = []

class TradeQuoteRes(BaseModel):
    from_value: int
    to_value: int
    diff: int
    balance_ratio: float
    is_balanced: bool
    favor_side: str

@router.post("/quote", response_model=TradeQuoteRes)
def quote(body: TradeCreateReq, sess: Session = Depends(get_session)):
    """Get a quote for a potential trade without creating it."""
    try:
        fv = bundle_value(sess, body.season, body.from_players, body.from_picks)
        tv = bundle_value(sess, body.season, body.to_players, body.to_picks)
        
        balance_info = calculate_trade_balance(fv, tv)
        
        return TradeQuoteRes(
            from_value=fv,
            to_value=tv,
            diff=fv - tv,
            balance_ratio=balance_info["balance_ratio"],
            is_balanced=balance_info["is_balanced"],
            favor_side=balance_info["favor_side"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote calculation failed: {str(e)}")

class TradeDTO(BaseModel):
    trade_id: int
    season: int
    from_team_id: int
    to_team_id: int
    status: TradeStatus
    round_num: int
    from_value_total: int
    to_value_total: int
    fair_margin: int
    created_at: str
    from_players: List[int]
    from_picks: List[int]
    to_players: List[int]
    to_picks: List[int]

@router.post("/propose", response_model=TradeDTO)
def propose(body: TradeCreateReq, sess: Session = Depends(get_session)):
    """Create a new trade proposal."""
    try:
        # Create trade proposal
        t = TradeProposal(
            season=body.season, 
            from_team_id=body.from_team_id, 
            to_team_id=body.to_team_id
        )
        sess.add(t)
        sess.commit()
        sess.refresh(t)
        
        # Add trade items
        for pid in body.from_players:
            sess.add(TradeItem(trade_id=t.trade_id, side="FROM", item_type=TradeItemType.PLAYER, player_id=pid))
        for pk in body.from_picks:
            sess.add(TradeItem(trade_id=t.trade_id, side="FROM", item_type=TradeItemType.PICK, pick_id=pk))
        for pid in body.to_players:
            sess.add(TradeItem(trade_id=t.trade_id, side="TO", item_type=TradeItemType.PLAYER, player_id=pid))
        for pk in body.to_picks:
            sess.add(TradeItem(trade_id=t.trade_id, side="TO", item_type=TradeItemType.PICK, pick_id=pk))
        
        sess.commit()
        
        # Evaluate the trade
        t = evaluate_trade(sess, t, body.season)
        
        return TradeDTO(
            trade_id=t.trade_id,
            season=t.season,
            from_team_id=t.from_team_id,
            to_team_id=t.to_team_id,
            status=t.status,
            round_num=t.round_num,
            from_value_total=t.from_value_total,
            to_value_total=t.to_value_total,
            fair_margin=t.fair_margin,
            created_at=t.created_at.isoformat(),
            from_players=body.from_players,
            from_picks=body.from_picks,
            to_players=body.to_players,
            to_picks=body.to_picks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trade proposal failed: {str(e)}")

@router.post("/counter/{trade_id}", response_model=TradeDTO)
def counter(trade_id: int, season: int, sess: Session = Depends(get_session)):
    """Generate an AI counter-offer for a trade."""
    try:
        t = ai_counter(sess, season, trade_id)
        
        # Get updated trade details
        details = get_trade_details(sess, trade_id)
        
        return TradeDTO(
            trade_id=t.trade_id,
            season=t.season,
            from_team_id=t.from_team_id,
            to_team_id=t.to_team_id,
            status=t.status,
            round_num=t.round_num,
            from_value_total=t.from_value_total,
            to_value_total=t.to_value_total,
            fair_margin=t.fair_margin,
            created_at=t.created_at.isoformat(),
            from_players=details.get("from_players", []),
            from_picks=details.get("from_picks", []),
            to_players=details.get("to_players", []),
            to_picks=details.get("to_picks", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Counter-offer failed: {str(e)}")

@router.post("/accept/{trade_id}")
def accept(trade_id: int, sess: Session = Depends(get_session)):
    """Accept a trade."""
    try:
        ok = accept_trade(sess, trade_id)
        return {"ok": ok, "message": "Trade accepted and executed" if ok else "Trade could not be accepted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Accept trade failed: {str(e)}")

@router.post("/reject/{trade_id}")
def reject(trade_id: int, sess: Session = Depends(get_session)):
    """Reject a trade."""
    try:
        ok = reject_trade(sess, trade_id)
        return {"ok": ok, "message": "Trade rejected" if ok else "Trade could not be rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reject trade failed: {str(e)}")

@router.get("/{trade_id}", response_model=TradeDTO)
def get_trade(trade_id: int, sess: Session = Depends(get_session)):
    """Get details of a specific trade."""
    try:
        details = get_trade_details(sess, trade_id)
        if not details:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        return TradeDTO(**details)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get trade failed: {str(e)}")

@router.get("/team/{team_id}", response_model=List[TradeDTO])
def get_team_trades(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get all trades involving a specific team."""
    try:
        trades = list_team_trades(sess, team_id, season)
        return [TradeDTO(**trade) for trade in trades]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get team trades failed: {str(e)}")

@router.get("/team/{team_id}/history", response_model=List[TradeDTO])
def get_team_trade_history(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get completed trade history for a team."""
    try:
        trades = get_trade_history(sess, team_id, season)
        return [TradeDTO(**trade) for trade in trades]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get trade history failed: {str(e)}")

class TradeStatsRes(BaseModel):
    total_trades: int
    accepted_trades: int
    rejected_trades: int
    open_trades: int
    countered_trades: int
    total_value_traded: int

@router.get("/stats", response_model=TradeStatsRes)
def get_trade_stats(season: int, sess: Session = Depends(get_session)):
    """Get trade statistics for a season."""
    try:
        from sqlmodel import select
        
        trades = list(sess.exec(select(TradeProposal).where(TradeProposal.season == season)))
        
        total_trades = len(trades)
        accepted_trades = len([t for t in trades if t.status == TradeStatus.ACCEPTED])
        rejected_trades = len([t for t in trades if t.status == TradeStatus.REJECTED])
        open_trades = len([t for t in trades if t.status == TradeStatus.OPEN])
        countered_trades = len([t for t in trades if t.status == TradeStatus.COUNTERED])
        
        total_value_traded = sum(t.from_value_total + t.to_value_total for t in trades if t.status == TradeStatus.ACCEPTED)
        
        return TradeStatsRes(
            total_trades=total_trades,
            accepted_trades=accepted_trades,
            rejected_trades=rejected_trades,
            open_trades=open_trades,
            countered_trades=countered_trades,
            total_value_traded=total_value_traded
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get trade stats failed: {str(e)}")

class PickValueRes(BaseModel):
    pick_id: int
    team_id: int
    season: int
    round: int
    value: int

@router.get("/picks/values", response_model=List[PickValueRes])
def get_pick_values(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get values for all draft picks owned by a team."""
    try:
        from sqlmodel import select
        from app.models.trade import DraftPick
        from app.services.trade_value import pick_value
        
        picks = list(sess.exec(select(DraftPick).where(
            DraftPick.team_id == team_id,
            DraftPick.season == season
        )))
        
        return [
            PickValueRes(
                pick_id=pick.pick_id,
                team_id=pick.team_id,
                season=pick.season,
                round=pick.round,
                value=pick_value(sess, pick.pick_id)
            )
            for pick in picks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get pick values failed: {str(e)}")

class PlayerValueRes(BaseModel):
    player_id: int
    value: int

@router.get("/players/values", response_model=List[PlayerValueRes])
def get_player_values(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get trade values for all players on a team."""
    try:
        from sqlmodel import select
        from app.models.player import Player
        from app.services.trade_value import players_value
        
        players = list(sess.exec(select(Player).where(Player.team_id == team_id)))
        
        return [
            PlayerValueRes(
                player_id=player.player_id,
                value=players_value(sess, [player.player_id], season)
            )
            for player in players
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get player values failed: {str(e)}")

