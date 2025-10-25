from __future__ import annotations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session
from app.models.database import get_session
from app.services.trade_engine import propose, accept, list_trade_block
from app.services.trade_value import evaluate as eval_value

router = APIRouter(prefix="/api/v1/trades", tags=["trades"])

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
    return eval_value(sess, season=season, from_team_id=from_team_id, to_team_id=to_team_id, from_assets=fa, to_assets=ta)

# Trade block browse
@router.get("/block")
def api_trade_block(season: int, sess: Session = Depends(get_session)):
    return list_trade_block(sess, season)
