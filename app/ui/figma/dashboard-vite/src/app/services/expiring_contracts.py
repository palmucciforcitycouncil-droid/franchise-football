from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from random import Random
from sqlmodel import Session, select
from app.models.contracts import PlayerContract, PlayerContractAsk, TeamTradeBlock
from app.services.cap_compliance import can_afford

# ---- Helpers ----
def _current_contract(sess: Session, player_id: int) -> Optional[PlayerContract]:
    """Get the current active contract for a player."""
    return sess.exec(select(PlayerContract).where(
        PlayerContract.player_id == player_id, 
        PlayerContract.is_active == True  # noqa: E712
    )).first()

def is_expiring_this_season(contract: PlayerContract, season: int) -> bool:
    """Check if a contract expires this season."""
    return contract.is_active and contract.end_season == season

def _position_multiplier(pos: str) -> float:
    """Get position-based salary multiplier."""
    # Simple market multipliers (MVP)
    table = {
        "QB": 2.0, "WR": 1.25, "EDGE": 1.35, "LT": 1.30,
        "RB": 0.8, "TE": 0.95, "CB": 1.25, "S": 0.9, "LB": 0.95, "DL": 1.0,
        "K": 0.5, "P": 0.45, "LS": 0.3
    }
    return table.get(pos, 1.0)

def get_or_update_ask(sess: Session, player, season: int) -> PlayerContractAsk:
    """Get or create/update a player's contract ask."""
    ask = sess.exec(select(PlayerContractAsk).where(PlayerContractAsk.player_id == player.player_id)).first()
    if not ask:
        ask = PlayerContractAsk(player_id=player.player_id, updated_season=season)
        sess.add(ask)
        sess.commit()
        sess.refresh(ask)

    if ask.updated_season != season:
        # Derive ask from overall/age/pos (MVP)
        pos_mult = _position_multiplier(getattr(player, "pos", ""))
        
        # Prime years roughly 25–29; older → shorter years, lower AAV; very young → longer
        age = getattr(player, "age", 26)
        ov = getattr(player, "overall", 70)
        
        years = 4
        if age >= 30: 
            years = 2
        if age >= 33: 
            years = 1
        if age <= 24: 
            years = 5

        base_aav = int((ov / 100.0) * 12_000_000 * pos_mult)  # cap-light scale; tweak later
        # Slight inflation from last season
        desired_aav = max(1_000_000, int(base_aav * 1.03))
        
        ask.desired_years = years
        ask.desired_aav = desired_aav
        ask.updated_season = season
        sess.add(ask)
        sess.commit()
    
    return ask

@dataclass
class ExpiringRow:
    """Data structure for expiring contract information."""
    player_id: int
    name: str
    pos: str
    age: int
    team_id: int
    cap_hit: int
    current_years_left: int
    ask_years: int
    ask_total: int
    ask_aav: int

def list_team_expiring(sess: Session, team_id: int, season: int) -> List[ExpiringRow]:
    """List all expiring contracts for a team."""
    out: List[ExpiringRow] = []
    
    try:
        # Find active players on team
        from app.models.player import Player
        players = list(sess.exec(select(Player).where(Player.team_id == team_id)))
        
        for p in players:
            con = _current_contract(sess, p.player_id)
            if not con: 
                continue
            
            if is_expiring_this_season(con, season):
                ask = get_or_update_ask(sess, p, season)
                out.append(ExpiringRow(
                    player_id=p.player_id,
                    name=getattr(p, "name", f"P{p.player_id}"),
                    pos=getattr(p, "pos", ""),
                    age=getattr(p, "age", 26),
                    team_id=team_id,
                    cap_hit=getattr(p, "cap_hit", getattr(con, "aav", 0)),
                    current_years_left=max(0, con.end_season - season),
                    ask_years=ask.desired_years,
                    ask_total=ask.desired_years * ask.desired_aav,
                    ask_aav=ask.desired_aav
                ))
    except ImportError:
        # Fallback if Player model doesn't exist
        pass
    
    # Sort: biggest ask first
    out.sort(key=lambda r: (r.ask_aav, r.ask_years), reverse=True)
    return out

# ---- Negotiation ----
@dataclass
class OfferResult:
    """Result of a contract offer."""
    accepted: bool
    min_years: int
    min_aav: int
    reason: str = ""

def _accept_threshold(ask: PlayerContractAsk) -> Tuple[int, int]:
    """Calculate minimum acceptable offer terms."""
    # You can tune these globally; MVP: 98% of AAV; years >= ask - 1
    return max(1, ask.desired_years - 1), int(ask.desired_aav * 0.98)

def make_resign_offer(sess: Session, season: int, team_id: int, player_id: int, years: int, aav: int) -> OfferResult:
    """Make a re-signing offer to a player."""
    try:
        from app.models.player import Player
        p = sess.get(Player, player_id)
        if not p: 
            return OfferResult(False, 0, 0, "Player not found")
        
        if p.team_id != team_id: 
            return OfferResult(False, 0, 0, "Player is not on your team")

        con = _current_contract(sess, player_id)
        if not con or not is_expiring_this_season(con, season):
            return OfferResult(False, 0, 0, "Not an expiring contract")

        ask = get_or_update_ask(sess, p, season)
        min_years, min_aav = _accept_threshold(ask)
        accepted = (years >= min_years and aav >= min_aav)

        if accepted:
            if not can_afford(sess, season, team_id, aav):
                return OfferResult(False, min_years, min_aav, "Cap space insufficient")
            # End old, create new
            con.is_active = False
            sess.add(con)
            
            new_con = PlayerContract(
                player_id=player_id, 
                team_id=team_id, 
                start_season=season, 
                end_season=season + years - 1, 
                aav=aav, 
                is_active=True
            )
            sess.add(new_con)
            
            # Slightly raise future ask baseline to what the market just paid
            ask.desired_years = years
            ask.desired_aav = aav
            ask.updated_season = season
            sess.add(ask)
            sess.commit()
            
            # Emit resign event
            try:
                from app.services.event_log_service import emit_event
                emit_event(sess, season=season, week=0, event_type="RESIGN", team_id=team_id, player_id=player_id, payload={"years": years, "aav": aav})
            except Exception:
                pass  # Safe if event logging fails
            
            return OfferResult(True, min_years, min_aav)
        else:
            # Store only as "last offer" on ask (MVP) so UI can show competing/last offer
            ask.updated_season = season
            sess.add(ask)
            sess.commit()
            
            return OfferResult(False, min_years, min_aav, "Below threshold")
    
    except ImportError:
        return OfferResult(False, 0, 0, "Player model not available")

# ---- CPU Preseason decisions ----
@dataclass
class TeamDecision:
    """CPU team decision for contract management."""
    resign_ids: List[int]
    unlikely_ids: List[int]  # won't pay ask
    trade_block_ids: List[int]  # subset (≤25%)

def _will_team_pay(p, ask: PlayerContractAsk) -> bool:
    """Determine if a CPU team will pay a player's asking price."""
    # MVP heuristic: pay if (overall >= 78) or (pos premium and ov >= 75) and ask fits rough tier
    pos = getattr(p, "pos", "")
    ov = getattr(p, "overall", 70)
    pos_premium = _position_multiplier(pos) >= 1.25
    
    # Frugal if age > 30 and ask years >= 4
    age = getattr(p, "age", 26)
    if age > 30 and ask.desired_years >= 4: 
        return False
    
    return (ov >= 78) or (pos_premium and ov >= 75)

def cpu_preseason_contract_pass(sess: Session, season: int, team_id: int, seed: int = 12345) -> TeamDecision:
    """CPU preseason contract decision making."""
    rnd = Random(seed + team_id * 13)
    exp = list_team_expiring(sess, team_id, season)
    resign, unlikely = [], []
    
    try:
        from app.models.player import Player
        
        for row in exp:
            p = sess.get(Player, row.player_id)
            if not p:
                continue
                
            ask = get_or_update_ask(sess, p, season)
            if _will_team_pay(p, ask):
                resign.append(row.player_id)
            else:
                unlikely.append(row.player_id)

        # Place at most 25% of "unlikely" on trade block. Choose by lowest overall first; tie-break by highest ask AAV.
        max_block = max(0, int(len(unlikely) * 0.25))
        
        # Sort by desirability to move: low OV, high ask first
        sorted_unlikely = sorted(unlikely, key=lambda pid: (
            getattr(sess.get(Player, pid), "overall", 0), 
            -getattr(get_or_update_ask(sess, sess.get(Player, pid), season), "desired_aav", 0)
        ))
        trade_block_ids = sorted_unlikely[:max_block]

        # Write trade block rows
        for pid in trade_block_ids:
            # Avoid duplicates
            exists = sess.exec(select(TeamTradeBlock).where(
                TeamTradeBlock.season == season, 
                TeamTradeBlock.team_id == team_id, 
                TeamTradeBlock.player_id == pid
            )).first()
            
            if not exists:
                sess.add(TeamTradeBlock(
                    season=season, 
                    team_id=team_id, 
                    player_id=pid, 
                    reason="Expiring/Unlikely to re-sign"
                ))
        
        sess.commit()
        
    except ImportError:
        # Fallback if Player model doesn't exist
        resign = []
        unlikely = []
        trade_block_ids = []
    
    return TeamDecision(resign_ids=resign, unlikely_ids=unlikely, trade_block_ids=trade_block_ids)

def get_trade_block_players(sess: Session, season: int, team_id: int) -> List[int]:
    """Get list of player IDs on the trade block for a team."""
    blocks = list(sess.exec(select(TeamTradeBlock).where(
        TeamTradeBlock.season == season,
        TeamTradeBlock.team_id == team_id
    )))
    return [block.player_id for block in blocks]

def add_to_trade_block(sess: Session, season: int, team_id: int, player_id: int, reason: str = "Manual addition") -> bool:
    """Add a player to the trade block."""
    # Check if already on trade block
    exists = sess.exec(select(TeamTradeBlock).where(
        TeamTradeBlock.season == season,
        TeamTradeBlock.team_id == team_id,
        TeamTradeBlock.player_id == player_id
    )).first()
    
    if exists:
        return False
    
    # Add to trade block
    sess.add(TeamTradeBlock(
        season=season,
        team_id=team_id,
        player_id=player_id,
        reason=reason
    ))
    sess.commit()
    return True

def remove_from_trade_block(sess: Session, season: int, team_id: int, player_id: int) -> bool:
    """Remove a player from the trade block."""
    block = sess.exec(select(TeamTradeBlock).where(
        TeamTradeBlock.season == season,
        TeamTradeBlock.team_id == team_id,
        TeamTradeBlock.player_id == player_id
    )).first()
    
    if not block:
        return False
    
    sess.delete(block)
    sess.commit()
    return True

def get_contract_summary(sess: Session, team_id: int, season: int) -> dict:
    """Get contract summary for a team."""
    expiring = list_team_expiring(sess, team_id, season)
    trade_block = get_trade_block_players(sess, season, team_id)
    
    total_ask_value = sum(row.ask_total for row in expiring)
    total_cap_hit = sum(row.cap_hit for row in expiring)
    
    return {
        "team_id": team_id,
        "season": season,
        "expiring_count": len(expiring),
        "trade_block_count": len(trade_block),
        "total_ask_value": total_ask_value,
        "total_cap_hit": total_cap_hit,
        "avg_ask_aav": total_ask_value / len(expiring) if expiring else 0,
        "positions": {
            pos: len([r for r in expiring if r.pos == pos])
            for pos in set(r.pos for r in expiring)
        }
    }
