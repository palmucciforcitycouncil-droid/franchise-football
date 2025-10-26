from __future__ import annotations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models.database import get_session
from app.services.trade_engine import propose, accept, list_trade_block, evaluate
from app.models.team import Team
from app.models.player import Player
from app.services.trade import evaluate_trade, EvaluationInputs
from app.services.trade.schemas import TradeOffer, TradeSide

router = APIRouter(prefix="/api/v1/trades", tags=["trades"])
teams_router = APIRouter(prefix="/api/v1/teams", tags=["teams"])
season_router = APIRouter(prefix="/api/v1/season", tags=["season"])

class Assets(BaseModel):
    players: List[int] = []
    picks: List[dict] = []  # {"round":1,"slot":3}

class ProposeReq(BaseModel):
    season: int
    from_team_id: int
    to_team_id: int
    from_assets: Assets
    to_assets: Assets

@router.post("/propose")
def api_propose(body: ProposeReq, sess: Session = Depends(get_session)):
    return propose(sess, season=body.season, from_team_id=body.from_team_id, to_team_id=body.to_team_id,
                   from_assets=body.from_assets.dict(), to_assets=body.to_assets.dict())

class AcceptReq(BaseModel):
    proposal_id: int

@router.post("/accept")
def api_accept(body: AcceptReq, sess: Session = Depends(get_session)):
    return accept(sess, proposal_id=body.proposal_id)

@router.get("/value_preview")
def api_value_preview(
    season: int, 
    from_team_id: int, 
    to_team_id: int,
    from_players: Optional[str] = Query(""),
    to_players: Optional[str] = Query(""),
    from_picks: Optional[str] = Query(""),
    to_picks: Optional[str] = Query(""),
    sess: Session = Depends(get_session)
):
    # players: "1,2,3", picks: "1-3,2-14" (round-slot)
    def parse_players(s: str) -> List[int]:
        return [int(x) for x in s.split(",") if x.strip().isdigit()]
    def parse_picks(s: str) -> List[dict]:
        arr = []
        for tok in s.split(","):
            tok = tok.strip()
            if not tok or "-" not in tok: continue
            r,sl = tok.split("-",1)
            arr.append({"round": int(r), "slot": int(sl)})
        return arr

    fa = {"players": parse_players(from_players or ""), "picks": parse_picks(from_picks or "")}
    ta = {"players": parse_players(to_players or ""), "picks": parse_picks(to_picks or "")}
    return evaluate(sess, season=season, from_team_id=from_team_id, to_team_id=to_team_id, from_assets=fa, to_assets=ta)

# Trade block browse
@router.get("/block")
def api_trade_block(season: int, sess: Session = Depends(get_session)):
    return list_trade_block(sess, season)

# CPU Trade Evaluation endpoint
@router.post("/simulate")
def api_simulate(body: ProposeReq, sess: Session = Depends(get_session)):
    """Simulate a trade to get CPU evaluation decision and explanation."""
    # Construct TradeOffer for evaluator
    offer = TradeOffer(
        from_side=TradeSide(
            team_id=body.from_team_id,
            player_ids=body.from_assets.players,
            picks=[{"season": body.season, "round": p["round"], "slot": p["slot"]} for p in body.from_assets.picks],
            cash=0
        ),
        to_side=TradeSide(
            team_id=body.to_team_id,
            player_ids=body.to_assets.players,
            picks=[{"season": body.season, "round": p["round"], "slot": p["slot"]} for p in body.to_assets.picks],
            cash=0
        )
    )
    
    # Default evaluation inputs
    inputs = EvaluationInputs(
        season_year=body.season,
        salary_cap=200_000_000  # Placeholder
    )
    
    # Evaluate from CPU (to_team) perspective
    result = evaluate_trade(sess, offer, inputs, cpu_team_id=body.to_team_id)
    
    return {
        "fairness": float(result.fairness),
        "cpu_surplus": float(result.cpu_surplus),
        "human_surplus": float(result.human_surplus),
        "cpu_accepts": result.cpu_accepts,
        "hard_veto": result.hard_veto,
        "need_gain": result.need_gain,
        "explanation": result.explanation,
        "counter_suggestion": result.counter_suggestion
    }


# New endpoints for frontend data fetching

@teams_router.get("/")
def get_all_teams(sess: Session = Depends(get_session)):
    """Get all teams for trade partner selection"""
    teams = sess.exec(select(Team)).all()
    return [
        {
            "id": t.id,
            "name": f"{t.location_name} {t.nickname or ''}".strip(),
            "city": t.location_name,
            "abbreviation": t.abbr or ""
        }
        for t in teams
    ]

@teams_router.get("/{team_id}/roster")
def get_team_roster(team_id: int, season: int = Query(2025), sess: Session = Depends(get_session)):
    """Get team roster for trade asset selection"""
    players = sess.exec(
        select(Player).where(Player.team_id == team_id)
    ).all()
    return [
        {
            "id": p.id,
            "name": getattr(p, 'first_name', '') + " " + getattr(p, 'last_name', ''),
            "position": getattr(p, 'position', ''),
            "overall": getattr(p, 'overall', 0) if hasattr(p, 'overall') else 50,
            "age": getattr(p, 'age', 0)
        }
        for p in players
    ]

@teams_router.get("/{team_id}/picks")
def get_team_picks(team_id: int, season: int = Query(2025), sess: Session = Depends(get_session)):
    """Get team draft picks for trade asset selection"""
    from app.models.draft import DraftPickInventory
    picks = sess.exec(
        select(DraftPickInventory).where(
            DraftPickInventory.owning_team_id == team_id,
            DraftPickInventory.season == season
        )
    ).all()
    return [
        {
            "round": p.round,
            "slot": p.slot,
            "year": p.season
        }
        for p in picks
    ]

@season_router.get("/current")
def get_current_season(sess: Session = Depends(get_session)):
    """Get current season context"""
    # TODO: Get from actual game state
    return {
        "season": 2025,
        "week": 1,
        "current_user_team_id": 1  # TODO: Get from auth/session
    }
