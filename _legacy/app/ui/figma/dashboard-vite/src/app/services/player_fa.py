from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from sqlmodel import Session, select
from app.models.player import Player
from app.models.contracts import PlayerContract, PlayerContractAsk
from app.services.cap_compliance import can_afford, roster_has_room

# ---------- Helpers ----------
def _current_contract(sess: Session, player_id: int) -> Optional[PlayerContract]:
    """Get current active contract for a player."""
    return sess.exec(select(PlayerContract).where(
        PlayerContract.player_id == player_id, 
        PlayerContract.is_active == True  # noqa: E712
    )).first()

def _position_mult(pos: str) -> float:
    """Get position multiplier for salary calculations."""
    tbl = {
        "QB": 2.1, "WR": 1.25, "EDGE": 1.35, "LT": 1.30, "CB": 1.25,
        "RB": 0.75, "TE": 0.95, "S": 0.92, "LB": 0.95, "DL": 1.00,
        "K": 0.45, "P": 0.45, "LS": 0.3
    }
    return tbl.get(pos, 1.0)

def get_or_update_player_ask(sess: Session, p: Player, season: int) -> PlayerContractAsk:
    """Get or create/update player contract ask."""
    ask = sess.exec(select(PlayerContractAsk).where(PlayerContractAsk.player_id == p.player_id)).first()
    if not ask:
        ask = PlayerContractAsk(player_id=p.player_id, updated_season=season)
        sess.add(ask)
        sess.commit()
        sess.refresh(ask)

    if ask.updated_season != season or ask.desired_aav <= 0:
        ov = getattr(p, "overall", 68)
        age = getattr(p, "age", 26)
        pos = getattr(p, "pos", "")
        pos_mult = _position_mult(pos)

        years = 3
        if age <= 24: 
            years = 4
        if age >= 30: 
            years = 2
        if age >= 33: 
            years = 1

        base_aav = int((ov / 100.0) * 11_000_000 * pos_mult)
        ask.desired_years = years
        ask.desired_aav = max(900_000, int(base_aav * 1.02))
        ask.updated_season = season
        sess.add(ask)
        sess.commit()
    return ask

@dataclass
class FARow:
    """Free agent row data."""
    player_id: int
    name: str
    pos: str
    age: int
    overall: int
    desired_years: int
    desired_aav: int
    desired_total: int
    competing_offers: int

# ---------- Queries ----------
def list_free_agents(sess: Session, season: int) -> List[FARow]:
    """List all free agents with their contract asks and competing offers."""
    rows: List[FARow] = []
    fa = list(sess.exec(select(Player).where(Player.team_id == None)))  # noqa: E711
    
    for p in fa:
        ask = get_or_update_player_ask(sess, p, season)
        offers = list(sess.exec(select(PlayerOffer).where(
            PlayerOffer.season == season, 
            PlayerOffer.to_player_id == p.player_id, 
            PlayerOffer.status == PlayerOfferStatus.ACTIVE
        )))
        
        rows.append(FARow(
            player_id=p.player_id,
            name=getattr(p, "name", f"P{p.player_id}"),
            pos=getattr(p, "pos", ""),
            age=getattr(p, "age", 26),
            overall=getattr(p, "overall", 65),
            desired_years=ask.desired_years,
            desired_aav=ask.desired_aav,
            desired_total=ask.desired_years * ask.desired_aav,
            competing_offers=len(offers)
        ))
    
    # High overall → top; tie by higher ask
    rows.sort(key=lambda r: (r.overall, r.desired_aav), reverse=True)
    return rows

# ---------- Offer acceptance ----------
@dataclass
class OfferResult:
    """Result of a player offer."""
    accepted: bool
    min_years: int
    min_aav: int
    reason: str = ""

def _accept_threshold(ask: PlayerContractAsk) -> Tuple[int, int]:
    """Calculate acceptance threshold for a player ask."""
    # MVP: Years >= ask-1, AAV >= 97% of ask
    return max(1, ask.desired_years - 1), int(ask.desired_aav * 0.97)

def create_player_offer(sess: Session, season: int, from_team_id: int, to_player_id: int, years: int, aav: int) -> OfferResult:
    """Create a player offer and handle instant acceptance."""
    p = sess.get(Player, to_player_id)
    if not p: 
        return OfferResult(False, 0, 0, "Player not found")
    if p.team_id is not None:
        return OfferResult(False, 0, 0, "Player is under contract (not a FA)")

    ask = get_or_update_player_ask(sess, p, season)
    min_years, min_aav = _accept_threshold(ask)
    accepted = (years >= min_years and aav >= min_aav)

    # Compliance: must have roster room and cap for AAV if instantly accepted
    if not roster_has_room(sess, from_team_id):
        return OfferResult(False, 0, 0, "Roster is full (53)")

    if accepted:
        if not can_afford(sess, season, from_team_id, aav):
            return OfferResult(False, min_years, min_aav, "Cap space insufficient")
        # Create active contract + assign to team; deactivate any phantom old contract
        old = _current_contract(sess, p.player_id)
        if old: 
            old.is_active = False
            sess.add(old)
        
        new_con = PlayerContract(
            player_id=p.player_id, 
            team_id=from_team_id,
            start_season=season, 
            end_season=season + years - 1, 
            aav=aav, 
            is_active=True
        )
        
        # Move player to team
        p.team_id = from_team_id
        sess.add(p)
        sess.add(new_con)

        # Cancel other active offers
        others = list(sess.exec(select(PlayerOffer).where(
            PlayerOffer.season == season, 
            PlayerOffer.to_player_id == p.player_id, 
            PlayerOffer.status == PlayerOfferStatus.ACTIVE
        )))
        for o in others:
            o.status = PlayerOfferStatus.CONSUMMATED
            sess.add(o)
        
        sess.commit()
        
        # Emit signing event
        try:
            from app.services.event_log_service import emit_event
            emit_event(sess, season=season, week=0, event_type="SIGNING", team_id=from_team_id, player_id=p.player_id, payload={"years": years, "aav": aav, "source": "FA"})
        except Exception:
            pass  # Safe if event logging fails
        
        return OfferResult(True, min_years, min_aav)

    # Store active offer
    offer = PlayerOffer(
        season=season, 
        from_team_id=from_team_id, 
        to_player_id=to_player_id, 
        years=years, 
        aav=aav
    )
    sess.add(offer)
    sess.commit()
    return OfferResult(False, min_years, min_aav, "Below threshold")

def list_player_offers(sess: Session, season: int, player_id: int) -> List[PlayerOffer]:
    """List all active offers for a player."""
    return list(sess.exec(select(PlayerOffer).where(
        PlayerOffer.season == season, 
        PlayerOffer.to_player_id == player_id, 
        PlayerOffer.status == PlayerOfferStatus.ACTIVE
    )))

# ---------- Release ----------
def release_player(sess: Session, player_id: int) -> bool:
    """Release a player to free agency."""
    p = sess.get(Player, player_id)
    if not p: 
        return False
    
    # End active contract if any
    con = _current_contract(sess, player_id)
    if con:
        con.is_active = False
        sess.add(con)
    
    # Move to FA
    p.team_id = None
    sess.add(p)
    sess.commit()
    
    # Emit release event
    try:
        from app.services.event_log_service import emit_event
        emit_event(sess, season=0, week=0, event_type="RELEASE", team_id=getattr(p, "team_id", None), player_id=p.player_id)
    except Exception:
        pass  # Safe if event logging fails
    
    return True

# ---------- Additional Functions ----------
def get_player_ask(sess: Session, player_id: int, season: int) -> Optional[PlayerContractAsk]:
    """Get player contract ask."""
    return sess.exec(select(PlayerContractAsk).where(PlayerContractAsk.player_id == player_id)).first()

def update_player_ask(sess: Session, player_id: int, season: int, years: int, aav: int) -> bool:
    """Update player contract ask."""
    ask = get_player_ask(sess, player_id, season)
    if not ask:
        return False
    
    ask.desired_years = years
    ask.desired_aav = aav
    ask.updated_season = season
    sess.add(ask)
    sess.commit()
    return True

def rescind_offer(sess: Session, offer_id: int) -> bool:
    """Rescind a player offer."""
    offer = sess.get(PlayerOffer, offer_id)
    if not offer:
        return False
    
    offer.status = PlayerOfferStatus.RESCINDED
    sess.add(offer)
    sess.commit()
    return True

def get_team_offers(sess: Session, season: int, team_id: int) -> List[PlayerOffer]:
    """Get all offers made by a team."""
    return list(sess.exec(select(PlayerOffer).where(
        PlayerOffer.season == season,
        PlayerOffer.from_team_id == team_id,
        PlayerOffer.status == PlayerOfferStatus.ACTIVE
    )))

def get_player_offer_history(sess: Session, season: int, player_id: int) -> List[PlayerOffer]:
    """Get complete offer history for a player."""
    return list(sess.exec(select(PlayerOffer).where(
        PlayerOffer.season == season,
        PlayerOffer.to_player_id == player_id
    )))

def get_free_agent_summary(sess: Session, season: int) -> dict:
    """Get free agency summary statistics."""
    fa_players = list(sess.exec(select(Player).where(Player.team_id == None)))  # noqa: E711
    active_offers = list(sess.exec(select(PlayerOffer).where(
        PlayerOffer.season == season,
        PlayerOffer.status == PlayerOfferStatus.ACTIVE
    )))
    
    # Calculate statistics
    total_fa = len(fa_players)
    total_offers = len(active_offers)
    avg_overall = sum(getattr(p, "overall", 65) for p in fa_players) / max(1, total_fa)
    
    # Position breakdown
    positions = {}
    for p in fa_players:
        pos = getattr(p, "pos", "Unknown")
        positions[pos] = positions.get(pos, 0) + 1
    
    return {
        "season": season,
        "total_free_agents": total_fa,
        "total_active_offers": total_offers,
        "average_overall": round(avg_overall, 1),
        "position_breakdown": positions,
        "offers_per_player": round(total_offers / max(1, total_fa), 2)
    }

def get_player_market_value(sess: Session, player_id: int, season: int) -> dict:
    """Get market value analysis for a player."""
    p = sess.get(Player, player_id)
    if not p:
        return {"error": "Player not found"}
    
    ask = get_or_update_player_ask(sess, p, season)
    offers = list_player_offers(sess, season, player_id)
    
    # Calculate market metrics
    offer_values = [o.aav for o in offers]
    avg_offer = sum(offer_values) / max(1, len(offer_values))
    max_offer = max(offer_values) if offer_values else 0
    
    return {
        "player_id": player_id,
        "player_name": getattr(p, "name", f"P{player_id}"),
        "position": getattr(p, "pos", ""),
        "overall": getattr(p, "overall", 65),
        "age": getattr(p, "age", 26),
        "desired_years": ask.desired_years,
        "desired_aav": ask.desired_aav,
        "desired_total": ask.desired_years * ask.desired_aav,
        "competing_offers": len(offers),
        "average_offer": round(avg_offer, 0),
        "max_offer": max_offer,
        "market_demand": "High" if len(offers) >= 3 else "Medium" if len(offers) >= 1 else "Low"
    }

def batch_release_players(sess: Session, player_ids: List[int]) -> dict:
    """Release multiple players in batch."""
    results = {"success": [], "failed": []}
    
    for player_id in player_ids:
        if release_player(sess, player_id):
            results["success"].append(player_id)
        else:
            results["failed"].append(player_id)
    
    return results

def get_team_free_agents(sess: Session, season: int, team_id: int) -> List[FARow]:
    """Get free agents that were previously on a specific team."""
    # This would require tracking previous team relationships
    # For MVP, we'll return all free agents
    return list_free_agents(sess, season)
