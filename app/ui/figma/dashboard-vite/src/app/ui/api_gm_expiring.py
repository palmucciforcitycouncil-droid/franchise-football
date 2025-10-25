# app/ui/api_gm_expiring.py
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db import get_session
from app.services.contracts_service import list_expiring_for_team, resign_player, release_player
from app.services.trade_valuation import player_trade_value
from app.services.expiring_ai import preseason_sweep_mark_trade_block
from random import Random

router = APIRouter(prefix="/api/v1/gm", tags=["gm"])

class ExpiringRow(BaseModel):
    player_id: int
    name: str
    pos: str
    team_id: int
    cap_hit_current: int
    desired_years: int
    desired_total: int
    desired_aav: int
    on_trade_block: bool

@router.get("/expiring", response_model=List[ExpiringRow])
def expiring(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get all expiring contracts for a team."""
    rows = list_expiring_for_team(sess, team_id, season)
    return [ExpiringRow(**r.__dict__) for r in rows]

class OfferReq(BaseModel):
    years: int
    total: int
    season: int

class OfferResult(BaseModel):
    accepted: bool
    min_years: int
    min_total: int

def _accept_logic(desired_years: int, desired_total: int, offer_years: int, offer_total: int) -> OfferResult:
    """Determine if a contract offer is accepted based on player's demands."""
    min_years = max(1, desired_years - 1)
    min_total = int(desired_total * 0.96)
    accepted = (offer_years >= min_years and offer_total >= min_total)
    return OfferResult(accepted=accepted, min_years=min_years, min_total=min_total)

@router.post("/negotiate/{player_id}", response_model=OfferResult)
def negotiate(player_id: int, team_id: int, body: OfferReq, sess: Session = Depends(get_session)):
    """Negotiate a contract with an expiring player."""
    # Fetch desired from cache in contracts_service
    from app.services.contracts_service import get_or_create_ask
    ask = get_or_create_ask(sess, player_id, body.season)
    res = _accept_logic(ask.desired_years, ask.desired_total, body.years, body.total)
    if res.accepted:
        resign_player(sess, player_id, team_id, body.season, body.years, body.total)
    return res

@router.post("/release/{player_id}")
def release(player_id: int, sess: Session = Depends(get_session)):
    """Release a player to free agency."""
    release_player(sess, player_id)
    return {"ok": True}

class TradeQuote(BaseModel):
    ask_value_units: int
    discounted: bool

@router.get("/trade/quote/{player_id}", response_model=TradeQuote)
def trade_quote(player_id: int, season: int, sess: Session = Depends(get_session)):
    """Get trade value quote for a player."""
    val = player_trade_value(sess, player_id, season)
    from app.models.core_min import Player
    p = sess.get(Player, player_id)
    discounted = False
    if p and p.team_id is not None:
        # Compare discounted vs baseline quickly
        # Baseline without discount:
        from app.services.expiring_ai import is_more_willing_to_trade
        from app.services.contracts_service import current_contract, is_expiring
        con = current_contract(sess, player_id)
        if con and is_expiring(sess, con, season) and is_more_willing_to_trade(sess, p.team_id, season, player_id):
            discounted = True
    return TradeQuote(ask_value_units=val, discounted=discounted)

@router.post("/preseason/expiring_ai_sweep")
def preseason_ai_sweep(season: int, seed: Optional[int] = None, sess: Session = Depends(get_session)):
    """Run preseason AI sweep to mark players on trade block."""
    rng = Random(seed if seed is not None else season)
    preseason_sweep_mark_trade_block(sess, season, rng)
    return {"ok": True}


