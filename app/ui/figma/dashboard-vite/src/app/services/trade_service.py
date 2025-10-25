from __future__ import annotations
from typing import List, Tuple
from sqlmodel import Session, select
from app.models.trade import TradeProposal, TradeItem, TradeItemType, TradeStatus, DraftPick
from app.services.trade_value import bundle_value, pick_value
from app.services.trade_valuation import player_trade_value
from app.services.cap_compliance import can_afford, roster_has_room

FAIR_TOLERANCE = 0.15  # 15% window is "fair enough"
COUNTER_STEP = 0.10    # ask back 10% of gap per round
MAX_ROUNDS = 2

def _split_items(sess: Session, trade_id: int) -> Tuple[List[int], List[int], List[int], List[int]]:
    """Split trade items into from/to players and picks."""
    from_players, from_picks, to_players, to_picks = [], [], [], []
    
    for it in sess.exec(select(TradeItem).where(TradeItem.trade_id==trade_id)):
        if it.side == "FROM":
            if it.item_type == TradeItemType.PLAYER and it.player_id: 
                from_players.append(it.player_id)
            if it.item_type == TradeItemType.PICK and it.pick_id: 
                from_picks.append(it.pick_id)
        else:
            if it.item_type == TradeItemType.PLAYER and it.player_id: 
                to_players.append(it.player_id)
            if it.item_type == TradeItemType.PICK and it.pick_id: 
                to_picks.append(it.pick_id)
    
    return from_players, from_picks, to_players, to_picks

def _team_discount_factor(sess: Session, season: int, team_id: int, player_ids: List[int]) -> float:
    """
    If the receiving team is more willing to trade a specific expiring player (on block),
    their required return can be lower. We average a modest -10% across those items.
    """
    if not player_ids: 
        return 1.0
    
    try:
        from app.services.expiring_ai import is_more_willing_to_trade
        # Check if any players are on the trade block
        willing_count = 0
        for pid in player_ids:
            if is_more_willing_to_trade(sess, team_id, pid, season):
                willing_count += 1
        
        if willing_count > 0:
            return 0.9  # 10% discount for players on block
    except ImportError:
        pass  # Fallback if expiring_ai doesn't exist
    
    return 1.0  # No discount

def evaluate_trade(sess: Session, trade: TradeProposal, season: int) -> TradeProposal:
    """Evaluate a trade and update its value totals."""
    fp, fpk, tp, tpk = _split_items(sess, trade.trade_id)
    
    from_total = bundle_value(sess, season, fp, fpk)
    to_total = bundle_value(sess, season, tp, tpk)
    
    # Apply team discount factor
    from_discount = _team_discount_factor(sess, season, trade.from_team_id, fp)
    to_discount = _team_discount_factor(sess, season, trade.to_team_id, tp)
    
    from_total = int(from_total * from_discount)
    to_total = int(to_total * to_discount)

    trade.from_value_total = from_total
    trade.to_value_total = to_total
    trade.fair_margin = from_total - to_total  # >0 means from_team gives more value
    
    sess.add(trade)
    sess.commit()
    return trade

def _needs_counter(trade: TradeProposal) -> bool:
    """Determine if a trade needs a counter-offer."""
    # If inside tolerance, no counter needed; else counter if rounds remain
    bigger = max(trade.from_value_total, trade.to_value_total, 1)
    diff_ratio = abs(trade.fair_margin) / bigger
    return diff_ratio > FAIR_TOLERANCE and trade.round_num < MAX_ROUNDS

def _counter_add_pick(sess: Session, team_id: int) -> int | None:
    """Add a late-round pick to balance a trade."""
    # Grab the lowest-round pick available for this team (MVP).
    row = sess.exec(select(DraftPick).where(DraftPick.team_id==team_id).order_by(DraftPick.round.desc())).first()
    return row.pick_id if row else None

def ai_counter(sess: Session, season: int, trade_id: int) -> TradeProposal:
    """Generate an AI counter-offer for a trade."""
    trade = sess.get(TradeProposal, trade_id)
    if not trade or trade.status not in (TradeStatus.OPEN, TradeStatus.COUNTERED): 
        return trade
    
    trade = evaluate_trade(sess, trade, season)

    if not _needs_counter(trade):
        # If within tolerance, accept automatically
        trade.status = TradeStatus.ACCEPTED
        sess.add(trade)
        sess.commit()
        return trade

    # Determine which side is short and request a small makeweight
    if trade.fair_margin > 0:
        # FROM is giving more; ask TO to add value
        need_side = "TO"
        need_team = trade.to_team_id
    else:
        # TO is giving more; ask FROM to add value
        need_side = "FROM"
        need_team = trade.from_team_id

    added = False
    # Try to add a late pick from the side that is short
    pk = _counter_add_pick(sess, need_team)
    if pk:
        sess.add(TradeItem(trade_id=trade.trade_id, side=need_side, item_type=TradeItemType.PICK, pick_id=pk))
        added = True

    trade.round_num += 1
    trade.status = TradeStatus.COUNTERED if added else TradeStatus.REJECTED
    sess.add(trade)
    sess.commit()
    
    return evaluate_trade(sess, trade, season)

def accept_trade(sess: Session, trade_id: int, season: int = None) -> bool:
    """Accept a trade and execute it."""
    trade = sess.get(TradeProposal, trade_id)
    if not trade or trade.status in (TradeStatus.ACCEPTED, TradeStatus.REJECTED): 
        return False
    
    # Get current season if not provided
    if season is None:
        from app.models.league import League
        league = sess.exec(select(League)).first()
        season = league.year if league else 2025
    
    # Compliance checks before accepting
    items = list(sess.exec(select(TradeItem).where(TradeItem.trade_id==trade_id)))
    
    # Check roster space for both teams
    for team_id in [trade.from_team_id, trade.to_team_id]:
        if not roster_has_room(sess, team_id, max_size=53):
            return False  # Roster full
    
    # Check cap space for incoming players
    for item in items:
        if item.item_type == TradeItemType.PLAYER and item.player_id:
            # Get player's contract
            from app.models.contracts import PlayerContract
            contract = sess.exec(select(PlayerContract).where(
                PlayerContract.player_id == item.player_id,
                PlayerContract.is_active == True  # noqa: E712
            )).first()
            
            if contract:
                # Determine which team is receiving the player
                receiving_team = trade.to_team_id if item.side == "FROM" else trade.from_team_id
                
                if not can_afford(sess, season, receiving_team, contract.aav):
                    return False  # Cap space insufficient
    
    trade.status = TradeStatus.ACCEPTED
    sess.add(trade)
    sess.commit()
    
    # Execute: move players/picks
    _execute_trade(sess, trade_id)
    return True

def reject_trade(sess: Session, trade_id: int) -> bool:
    """Reject a trade."""
    trade = sess.get(TradeProposal, trade_id)
    if not trade: 
        return False
    
    trade.status = TradeStatus.REJECTED
    sess.add(trade)
    sess.commit()
    return True

def _execute_trade(sess: Session, trade_id: int):
    """Execute a trade by moving players and picks between teams."""
    items = list(sess.exec(select(TradeItem).where(TradeItem.trade_id==trade_id)))
    trade = sess.get(TradeProposal, trade_id)
    
    for it in items:
        if it.item_type == TradeItemType.PLAYER and it.player_id:
            try:
                from app.models.player import Player
                p = sess.get(Player, it.player_id)
                if p:
                    p.team_id = trade.to_team_id if it.side=="FROM" else trade.from_team_id
                    sess.add(p)
            except ImportError:
                pass  # Skip if Player model doesn't exist
        
        elif it.item_type == TradeItemType.PICK and it.pick_id:
            pk = sess.get(DraftPick, it.pick_id)
            if pk:
                pk.team_id = trade.to_team_id if it.side=="FROM" else trade.from_team_id
                sess.add(pk)
    
    sess.commit()

def get_trade_details(sess: Session, trade_id: int) -> dict:
    """Get detailed information about a trade."""
    trade = sess.get(TradeProposal, trade_id)
    if not trade:
        return {}
    
    fp, fpk, tp, tpk = _split_items(sess, trade_id)
    
    return {
        "trade_id": trade.trade_id,
        "season": trade.season,
        "from_team_id": trade.from_team_id,
        "to_team_id": trade.to_team_id,
        "status": trade.status,
        "round_num": trade.round_num,
        "from_value_total": trade.from_value_total,
        "to_value_total": trade.to_value_total,
        "fair_margin": trade.fair_margin,
        "created_at": trade.created_at,
        "from_players": fp,
        "from_picks": fpk,
        "to_players": tp,
        "to_picks": tpk
    }

def list_team_trades(sess: Session, team_id: int, season: int) -> List[dict]:
    """List all trades involving a specific team."""
    trades = list(sess.exec(select(TradeProposal).where(
        (TradeProposal.from_team_id == team_id) | (TradeProposal.to_team_id == team_id),
        TradeProposal.season == season
    )))
    
    return [get_trade_details(sess, trade.trade_id) for trade in trades]

def get_trade_history(sess: Session, team_id: int, season: int) -> List[dict]:
    """Get completed trade history for a team."""
    trades = list(sess.exec(select(TradeProposal).where(
        (TradeProposal.from_team_id == team_id) | (TradeProposal.to_team_id == team_id),
        TradeProposal.season == season,
        TradeProposal.status == TradeStatus.ACCEPTED
    )))
    
    return [get_trade_details(sess, trade.trade_id) for trade in trades]

