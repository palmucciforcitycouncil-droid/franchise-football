from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db import get_session
from app.services.player_fa import (
    list_free_agents, create_player_offer, release_player, list_player_offers,
    get_player_ask, update_player_ask, rescind_offer, get_team_offers,
    get_player_offer_history, get_free_agent_summary, get_player_market_value,
    batch_release_players, get_team_free_agents
)
from app.models.player_market import PlayerOffer

router = APIRouter(prefix="/api/v1/players", tags=["players-fa"])

class FARowDTO(BaseModel):
    player_id: int
    name: str
    pos: str
    age: int
    overall: int
    desired_years: int
    desired_aav: int
    desired_total: int
    competing_offers: int

@router.get("/free_agents", response_model=List[FARowDTO])
def free_agents(season: int, sess: Session = Depends(get_session)):
    """Get list of all free agents with their contract asks and competing offers."""
    try:
        rows = list_free_agents(sess, season)
        return [FARowDTO(**r.__dict__) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get free agents: {str(e)}")

class OfferReq(BaseModel):
    season: int
    team_id: int
    player_id: int
    years: int
    aav: int

class OfferRes(BaseModel):
    accepted: bool
    min_years: int
    min_aav: int
    reason: str | None = None

@router.post("/offer", response_model=OfferRes)
def offer(body: OfferReq, sess: Session = Depends(get_session)):
    """Make a contract offer to a free agent."""
    try:
        res = create_player_offer(sess, body.season, body.team_id, body.player_id, body.years, body.aav)
        return OfferRes(accepted=res.accepted, min_years=res.min_years, min_aav=res.min_aav, reason=res.reason or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to make offer: {str(e)}")

@router.post("/release/{player_id}")
def release(player_id: int, sess: Session = Depends(get_session)):
    """Release a player to free agency."""
    try:
        ok = release_player(sess, player_id)
        return {"ok": ok, "player_id": player_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to release player: {str(e)}")

class OffersListDTO(BaseModel):
    offer_id: int
    season: int
    from_team_id: int
    to_player_id: int
    years: int
    aav: int
    status: str

@router.get("/offers", response_model=List[OffersListDTO])
def offers(season: int, player_id: int, sess: Session = Depends(get_session)):
    """Get all active offers for a specific player."""
    try:
        rows: List[PlayerOffer] = list_player_offers(sess, season, player_id)
        return [
            OffersListDTO(
                offer_id=r.offer_id, 
                season=r.season, 
                from_team_id=r.from_team_id,
                to_player_id=r.to_player_id, 
                years=r.years, 
                aav=r.aav, 
                status=r.status.value
            ) for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get offers: {str(e)}")

@router.get("/offers/history", response_model=List[OffersListDTO])
def offer_history(season: int, player_id: int, sess: Session = Depends(get_session)):
    """Get complete offer history for a player."""
    try:
        rows: List[PlayerOffer] = get_player_offer_history(sess, season, player_id)
        return [
            OffersListDTO(
                offer_id=r.offer_id, 
                season=r.season, 
                from_team_id=r.from_team_id,
                to_player_id=r.to_player_id, 
                years=r.years, 
                aav=r.aav, 
                status=r.status.value
            ) for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get offer history: {str(e)}")

@router.get("/offers/team/{team_id}", response_model=List[OffersListDTO])
def team_offers(season: int, team_id: int, sess: Session = Depends(get_session)):
    """Get all offers made by a team."""
    try:
        rows: List[PlayerOffer] = get_team_offers(sess, season, team_id)
        return [
            OffersListDTO(
                offer_id=r.offer_id, 
                season=r.season, 
                from_team_id=r.from_team_id,
                to_player_id=r.to_player_id, 
                years=r.years, 
                aav=r.aav, 
                status=r.status.value
            ) for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team offers: {str(e)}")

@router.post("/rescind/{offer_id}")
def rescind_offer_endpoint(offer_id: int, sess: Session = Depends(get_session)):
    """Rescind a player offer."""
    try:
        ok = rescind_offer(sess, offer_id)
        return {"ok": ok, "offer_id": offer_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rescind offer: {str(e)}")

class UpdateAskReq(BaseModel):
    player_id: int
    season: int
    years: int
    aav: int

@router.post("/ask/update")
def update_ask(body: UpdateAskReq, sess: Session = Depends(get_session)):
    """Update a player's contract ask."""
    try:
        ok = update_player_ask(sess, body.player_id, body.season, body.years, body.aav)
        return {"ok": ok, "player_id": body.player_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ask: {str(e)}")

@router.get("/ask/{player_id}")
def get_ask(player_id: int, season: int, sess: Session = Depends(get_session)):
    """Get a player's contract ask."""
    try:
        ask = get_player_ask(sess, player_id, season)
        if not ask:
            raise HTTPException(status_code=404, detail="Player ask not found")
        
        return {
            "player_id": player_id,
            "season": season,
            "desired_years": ask.desired_years,
            "desired_aav": ask.desired_aav,
            "desired_total": ask.desired_years * ask.desired_aav,
            "updated_season": ask.updated_season
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ask: {str(e)}")

@router.get("/market_value/{player_id}")
def market_value(player_id: int, season: int, sess: Session = Depends(get_session)):
    """Get market value analysis for a player."""
    try:
        return get_player_market_value(sess, player_id, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get market value: {str(e)}")

@router.get("/summary")
def free_agent_summary(season: int, sess: Session = Depends(get_session)):
    """Get free agency summary statistics."""
    try:
        return get_free_agent_summary(sess, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")

class BatchReleaseReq(BaseModel):
    player_ids: List[int]

@router.post("/batch_release")
def batch_release(body: BatchReleaseReq, sess: Session = Depends(get_session)):
    """Release multiple players in batch."""
    try:
        results = batch_release_players(sess, body.player_ids)
        return {
            "success": results["success"],
            "failed": results["failed"],
            "total_processed": len(body.player_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to batch release: {str(e)}")

@router.get("/team_free_agents/{team_id}", response_model=List[FARowDTO])
def team_free_agents(season: int, team_id: int, sess: Session = Depends(get_session)):
    """Get free agents that were previously on a specific team."""
    try:
        rows = get_team_free_agents(sess, season, team_id)
        return [FARowDTO(**r.__dict__) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team free agents: {str(e)}")

@router.get("/position/{position}", response_model=List[FARowDTO])
def free_agents_by_position(position: str, season: int, sess: Session = Depends(get_session)):
    """Get free agents filtered by position."""
    try:
        rows = list_free_agents(sess, season)
        filtered = [r for r in rows if r.pos.upper() == position.upper()]
        return [FARowDTO(**r.__dict__) for r in filtered]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get free agents by position: {str(e)}")

@router.get("/top/{limit}", response_model=List[FARowDTO])
def top_free_agents(limit: int = 10, season: int = 2024, sess: Session = Depends(get_session)):
    """Get top free agents by overall rating."""
    try:
        rows = list_free_agents(sess, season)
        top_rows = rows[:limit]
        return [FARowDTO(**r.__dict__) for r in top_rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top free agents: {str(e)}")

@router.get("/search")
def search_free_agents(
    season: int, 
    min_overall: Optional[int] = None,
    max_overall: Optional[int] = None,
    position: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    sess: Session = Depends(get_session)
):
    """Search free agents with filters."""
    try:
        rows = list_free_agents(sess, season)
        
        # Apply filters
        filtered = rows
        if min_overall is not None:
            filtered = [r for r in filtered if r.overall >= min_overall]
        if max_overall is not None:
            filtered = [r for r in filtered if r.overall <= max_overall]
        if position is not None:
            filtered = [r for r in filtered if r.pos.upper() == position.upper()]
        if min_age is not None:
            filtered = [r for r in filtered if r.age >= min_age]
        if max_age is not None:
            filtered = [r for r in filtered if r.age <= max_age]
        
        return [FARowDTO(**r.__dict__) for r in filtered]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search free agents: {str(e)}")

@router.get("/offer_stats/{player_id}")
def offer_stats(player_id: int, season: int, sess: Session = Depends(get_session)):
    """Get offer statistics for a player."""
    try:
        offers = get_player_offer_history(sess, season, player_id)
        
        if not offers:
            return {
                "player_id": player_id,
                "season": season,
                "total_offers": 0,
                "active_offers": 0,
                "average_aav": 0,
                "max_aav": 0,
                "min_aav": 0,
                "average_years": 0
            }
        
        active_offers = [o for o in offers if o.status.value == "ACTIVE"]
        aav_values = [o.aav for o in offers]
        years_values = [o.years for o in offers]
        
        return {
            "player_id": player_id,
            "season": season,
            "total_offers": len(offers),
            "active_offers": len(active_offers),
            "average_aav": round(sum(aav_values) / len(aav_values), 0),
            "max_aav": max(aav_values),
            "min_aav": min(aav_values),
            "average_years": round(sum(years_values) / len(years_values), 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get offer stats: {str(e)}")

