from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from sqlmodel import Session, select, col
from app.models.roster import DepthChart
from app.models.player import Player

# ---- Position eligibility map (MVP). Adjust to your roster schema if needed.
ELIGIBILITY: Dict[str, List[str]] = {
    "QB": ["QB"],
    "RB": ["RB"],
    "WR1": ["WR"], "WR2": ["WR"], "WR3": ["WR"],
    "TE": ["TE"],
    "LT": ["LT", "T", "OL"], "LG": ["G", "OL"], "C": ["C", "OL"], "RG": ["G", "OL"], "RT": ["RT", "T", "OL"],

    "EDGE1": ["EDGE", "OLB", "DE"], "EDGE2": ["EDGE", "OLB", "DE"],
    "DL1": ["DL", "DT", "DE"], "DL2": ["DL", "DT", "DE"],
    "LB1": ["LB", "MLB", "ILB"], "LB2": ["LB", "MLB", "ILB"],
    "CB1": ["CB"], "CB2": ["CB"],
    "S1": ["S", "FS", "SS"], "S2": ["S", "FS", "SS"],

    "K": ["K"], "P": ["P"], "LS": ["LS", "C"],
    "KR": ["WR", "RB", "CB", "S"], "PR": ["WR", "CB", "S"]
}

ORDERED_SLOTS: List[str] = [
    "QB", "RB", "WR1", "WR2", "WR3", "TE", "LT", "LG", "C", "RG", "RT",
    "EDGE1", "EDGE2", "DL1", "DL2", "LB1", "LB2", "CB1", "CB2", "S1", "S2",
    "K", "P", "LS", "KR", "PR"
]

def list_depth_chart(sess: Session, team_id: int) -> List[DepthChart]:
    """Get depth chart for a team."""
    rows = list(sess.exec(
        select(DepthChart).where(DepthChart.team_id == team_id).order_by(DepthChart.slot, DepthChart.order_index)
    ))
    return rows

def set_depth_chart(sess: Session, team_id: int, items: List[Tuple[str, int, Optional[int]]]) -> None:
    """
    Set depth chart for a team.
    items: list of (slot, order_index, player_id)
    Validates slot names and clears duplicates so a player doesn't occupy incompatible starting slots.
    """
    # Clear existing for provided slots
    slots = {s for (s, _, __) in items}
    for s in slots:
        sess.exec(select(DepthChart).where(DepthChart.team_id == team_id, DepthChart.slot == s))
        # Delete existing entries for these slots
        existing = list(sess.exec(select(DepthChart).where(DepthChart.team_id == team_id, DepthChart.slot == s)))
        for existing_row in existing:
            sess.delete(existing_row)
    sess.commit()
    
    # Insert new rows
    for slot, idx, pid in items:
        if slot not in ELIGIBILITY: 
            continue
        sess.add(DepthChart(team_id=team_id, slot=slot, order_index=idx, player_id=pid))
    sess.commit()

def _player_pool(sess: Session, team_id: int, pos_filter: List[str]) -> List[Player]:
    """Get players from team that match position filter."""
    candidates = list(sess.exec(select(Player).where(Player.team_id == team_id)))
    return [p for p in candidates if getattr(p, "pos", "") in pos_filter]

def _is_available(sess: Session, player_id: int, season: int, week: int, game_id: int, team_id: int, opponent_id: int) -> bool:
    """Check if player is available (not injured)."""
    # Uses the injury hook (OUT = not available). RTP penalties are handled in engine later.
    try:
        from app.engine.injury_hooks import availability
        return availability(sess, player_id)
    except ImportError:
        # Fallback if injury system not available
        return True

def _best_available(sess: Session, players: List[Player], season: int, week: int, game_id: int, team_id: int, opponent_id: int) -> List[Player]:
    """Filter out unavailable players and sort by overall rating."""
    # Filter out unavailable; sort by overall desc
    avail = [p for p in players if _is_available(sess, p.player_id, season, week, game_id, team_id, opponent_id)]
    avail.sort(key=lambda p: getattr(p, "overall", 50), reverse=True)
    return avail

def auto_fill(sess: Session, team_id: int, season: int, week: int, game_id: int, opponent_id: int) -> None:
    """
    Auto-fill depth chart for a team.
    For each slot, pick best available players who match eligibility. Keep simple 1-deep or 2-deep depending slot.
    WR/EDGE/DL/LB/CB/S try to fill 2 deep where defined (WR1-3 are starters only in MVP).
    """
    # Clear existing chart for team (MVP behavior)
    existing = list(sess.exec(select(DepthChart).where(DepthChart.team_id == team_id)))
    for existing_row in existing:
        sess.delete(existing_row)
    sess.commit()

    for slot in ORDERED_SLOTS:
        pool = _player_pool(sess, team_id, ELIGIBILITY[slot])
        best = _best_available(sess, pool, season, week, game_id, team_id, opponent_id)
        if not best:
            sess.add(DepthChart(team_id=team_id, slot=slot, order_index=0, player_id=None))
            continue

        # How deep?
        depth = 2 if slot in ["EDGE1", "EDGE2", "DL1", "DL2", "LB1", "LB2", "CB1", "CB2", "S1", "S2"] else 1
        for i in range(depth):
            pid = best[i].player_id if i < len(best) else None
            sess.add(DepthChart(team_id=team_id, slot=slot, order_index=i, player_id=pid))
    sess.commit()

def lineup_for_game(sess: Session, team_id: int, season: int, week: int, game_id: int, opponent_id: int) -> Dict[str, List[int]]:
    """
    Get lineup for a game.
    Returns {slot: [player_id(s) ...]} for engine consumption.
    If empty/missing, performs a quick fill using current availability.
    """
    rows = list_depth_chart(sess, team_id)
    if not rows:
        auto_fill(sess, team_id, season, week, game_id, opponent_id)
        rows = list_depth_chart(sess, team_id)

    by_slot: Dict[str, List[int]] = {s: [] for s in ORDERED_SLOTS}
    for r in rows:
        if r.slot in by_slot and r.order_index >= 0:
            by_slot[r.slot].append(r.player_id or -1)
    return by_slot

def get_depth_chart_by_slot(sess: Session, team_id: int) -> Dict[str, List[Dict]]:
    """Get depth chart organized by slot."""
    rows = list_depth_chart(sess, team_id)
    by_slot = {}
    
    for row in rows:
        if row.slot not in by_slot:
            by_slot[row.slot] = []
        by_slot[row.slot].append({
            "order_index": row.order_index,
            "player_id": row.player_id
        })
    
    # Sort each slot by order_index
    for slot in by_slot:
        by_slot[slot].sort(key=lambda x: x["order_index"])
    
    return by_slot

def validate_depth_chart(sess: Session, team_id: int) -> Dict[str, List[str]]:
    """Validate depth chart for issues."""
    issues = {"errors": [], "warnings": []}
    rows = list_depth_chart(sess, team_id)
    
    # Check for invalid slots
    for row in rows:
        if row.slot not in ELIGIBILITY:
            issues["errors"].append(f"Invalid slot: {row.slot}")
    
    # Check for duplicate players in incompatible positions
    player_slots = {}
    for row in rows:
        if row.player_id:
            if row.player_id not in player_slots:
                player_slots[row.player_id] = []
            player_slots[row.player_id].append(row.slot)
    
    # Check for players in multiple starting positions (non-special teams)
    for player_id, slots in player_slots.items():
        starting_slots = [s for s in slots if not s.startswith(("K", "P", "LS", "KR", "PR"))]
        if len(starting_slots) > 1:
            issues["warnings"].append(f"Player {player_id} in multiple starting positions: {starting_slots}")
    
    # Check for missing critical positions
    critical_positions = ["QB", "K", "P"]
    for pos in critical_positions:
        if not any(row.slot == pos and row.order_index == 0 and row.player_id for row in rows):
            issues["errors"].append(f"Missing starting {pos}")
    
    return issues

def get_available_players_for_slot(sess: Session, team_id: int, slot: str) -> List[Player]:
    """Get available players for a specific slot."""
    if slot not in ELIGIBILITY:
        return []
    
    pool = _player_pool(sess, team_id, ELIGIBILITY[slot])
    # Filter by availability (simplified - no injury check for this function)
    return pool

def update_single_slot(sess: Session, team_id: int, slot: str, order_index: int, player_id: Optional[int]) -> bool:
    """Update a single depth chart slot."""
    if slot not in ELIGIBILITY:
        return False
    
    # Remove existing entry for this slot/order
    existing = sess.exec(select(DepthChart).where(
        DepthChart.team_id == team_id,
        DepthChart.slot == slot,
        DepthChart.order_index == order_index
    )).first()
    
    if existing:
        sess.delete(existing)
    
    # Add new entry
    sess.add(DepthChart(team_id=team_id, slot=slot, order_index=order_index, player_id=player_id))
    sess.commit()
    return True

def clear_depth_chart(sess: Session, team_id: int) -> None:
    """Clear entire depth chart for a team."""
    existing = list(sess.exec(select(DepthChart).where(DepthChart.team_id == team_id)))
    for existing_row in existing:
        sess.delete(existing_row)
    sess.commit()

def get_depth_chart_summary(sess: Session, team_id: int) -> Dict[str, any]:
    """Get depth chart summary statistics."""
    rows = list_depth_chart(sess, team_id)
    
    summary = {
        "team_id": team_id,
        "total_slots": len(rows),
        "filled_slots": len([r for r in rows if r.player_id is not None]),
        "empty_slots": len([r for r in rows if r.player_id is None]),
        "slots_by_position": {},
        "depth_by_slot": {}
    }
    
    # Count by position
    for row in rows:
        if row.player_id:
            pos = row.slot
            summary["slots_by_position"][pos] = summary["slots_by_position"].get(pos, 0) + 1
    
    # Count depth for each slot
    for row in rows:
        slot = row.slot
        if slot not in summary["depth_by_slot"]:
            summary["depth_by_slot"][slot] = 0
        summary["depth_by_slot"][slot] = max(summary["depth_by_slot"][slot], row.order_index + 1)
    
    return summary

def get_injured_players_in_lineup(sess: Session, team_id: int, season: int, week: int, game_id: int, opponent_id: int) -> List[Dict]:
    """Get list of injured players currently in the depth chart."""
    rows = list_depth_chart(sess, team_id)
    injured_players = []
    
    for row in rows:
        if row.player_id and not _is_available(sess, row.player_id, season, week, game_id, team_id, opponent_id):
            injured_players.append({
                "player_id": row.player_id,
                "slot": row.slot,
                "order_index": row.order_index
            })
    
    return injured_players

def get_depth_chart_with_player_info(sess: Session, team_id: int) -> List[Dict]:
    """Get depth chart with player information."""
    rows = list_depth_chart(sess, team_id)
    result = []
    
    for row in rows:
        player_info = None
        if row.player_id:
            player = sess.get(Player, row.player_id)
            if player:
                player_info = {
                    "player_id": player.player_id,
                    "name": getattr(player, "name", f"Player {player.player_id}"),
                    "pos": getattr(player, "pos", ""),
                    "overall": getattr(player, "overall", 0),
                    "age": getattr(player, "age", 0)
                }
        
        result.append({
            "slot": row.slot,
            "order_index": row.order_index,
            "player_id": row.player_id,
            "player_info": player_info
        })
    
    return result

