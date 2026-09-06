from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db import get_session
from app.services.expiring_contracts import (
    list_team_expiring, make_resign_offer, cpu_preseason_contract_pass,
    get_trade_block_players, add_to_trade_block, remove_from_trade_block,
    get_contract_summary
)
from app.models.contracts import TeamTradeBlock

router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])

class ExpiringRowDTO(BaseModel):
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

@router.get("/expiring", response_model=List[ExpiringRowDTO])
def expiring(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get all expiring contracts for a team."""
    try:
        rows = list_team_expiring(sess, team_id, season)
        return [ExpiringRowDTO(**r.__dict__) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get expiring contracts: {str(e)}")

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

@router.post("/resign", response_model=OfferRes)
def resign(body: OfferReq, sess: Session = Depends(get_session)):
    """Make a re-signing offer to a player."""
    try:
        res = make_resign_offer(sess, body.season, body.team_id, body.player_id, body.years, body.aav)
        return OfferRes(
            accepted=res.accepted, 
            min_years=res.min_years, 
            min_aav=res.min_aav, 
            reason=res.reason or None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to make resign offer: {str(e)}")

class CpuPassReq(BaseModel):
    season: int
    team_id: int
    seed: int = 12345

class CpuPassRes(BaseModel):
    resign_ids: List[int]
    unlikely_ids: List[int]
    trade_block_ids: List[int]

@router.post("/cpu/preseason_pass", response_model=CpuPassRes)
def cpu_preseason(body: CpuPassReq, sess: Session = Depends(get_session)):
    """Run CPU preseason contract decisions."""
    try:
        out = cpu_preseason_contract_pass(sess, body.season, body.team_id, body.seed)
        return CpuPassRes(**out.__dict__)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run CPU preseason pass: {str(e)}")

@router.get("/trade_block_ids", response_model=List[int])
def trade_block_ids(season: int, team_id: int, sess: Session = Depends(get_session)):
    """Get list of player IDs on the trade block for a team."""
    try:
        ids = get_trade_block_players(sess, season, team_id)
        return ids
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trade block IDs: {str(e)}")

class TradeBlockReq(BaseModel):
    season: int
    team_id: int
    player_id: int
    reason: str = "Manual addition"

class TradeBlockRes(BaseModel):
    success: bool
    message: str

@router.post("/trade_block/add", response_model=TradeBlockRes)
def add_to_trade_block_endpoint(body: TradeBlockReq, sess: Session = Depends(get_session)):
    """Add a player to the trade block."""
    try:
        success = add_to_trade_block(sess, body.season, body.team_id, body.player_id, body.reason)
        if success:
            return TradeBlockRes(success=True, message="Player added to trade block")
        else:
            return TradeBlockRes(success=False, message="Player already on trade block")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add player to trade block: {str(e)}")

class RemoveTradeBlockReq(BaseModel):
    season: int
    team_id: int
    player_id: int

@router.post("/trade_block/remove", response_model=TradeBlockRes)
def remove_from_trade_block_endpoint(body: RemoveTradeBlockReq, sess: Session = Depends(get_session)):
    """Remove a player from the trade block."""
    try:
        success = remove_from_trade_block(sess, body.season, body.team_id, body.player_id)
        if success:
            return TradeBlockRes(success=True, message="Player removed from trade block")
        else:
            return TradeBlockRes(success=False, message="Player not found on trade block")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove player from trade block: {str(e)}")

class ContractSummaryRes(BaseModel):
    team_id: int
    season: int
    expiring_count: int
    trade_block_count: int
    total_ask_value: int
    total_cap_hit: int
    avg_ask_aav: float
    positions: dict

@router.get("/summary", response_model=ContractSummaryRes)
def get_contract_summary_endpoint(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get contract summary for a team."""
    try:
        summary = get_contract_summary(sess, team_id, season)
        return ContractSummaryRes(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contract summary: {str(e)}")

class TradeBlockDetailsRes(BaseModel):
    player_id: int
    season: int
    team_id: int
    reason: str

@router.get("/trade_block/details", response_model=List[TradeBlockDetailsRes])
def get_trade_block_details(season: int, team_id: int, sess: Session = Depends(get_session)):
    """Get detailed trade block information for a team."""
    try:
        from sqlmodel import select
        
        blocks = list(sess.exec(select(TeamTradeBlock).where(
            TeamTradeBlock.season == season,
            TeamTradeBlock.team_id == team_id
        )))
        
        return [
            TradeBlockDetailsRes(
                player_id=block.player_id,
                season=block.season,
                team_id=block.team_id,
                reason=block.reason
            )
            for block in blocks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trade block details: {str(e)}")

class ContractStatsRes(BaseModel):
    total_expiring: int
    total_trade_block: int
    avg_ask_aav: float
    total_ask_value: int
    position_breakdown: dict

@router.get("/stats", response_model=ContractStatsRes)
def get_contract_stats(season: int, sess: Session = Depends(get_session)):
    """Get league-wide contract statistics."""
    try:
        from sqlmodel import select
        from app.models.contracts import PlayerContractAsk, TeamTradeBlock
        
        # Get all expiring contracts across all teams
        all_expiring = []
        for team_id in range(1, 33):  # Assuming 32 teams
            expiring = list_team_expiring(sess, team_id, season)
            all_expiring.extend(expiring)
        
        # Get all trade block players
        trade_blocks = list(sess.exec(select(TeamTradeBlock).where(TeamTradeBlock.season == season)))
        
        # Calculate stats
        total_expiring = len(all_expiring)
        total_trade_block = len(trade_blocks)
        total_ask_value = sum(row.ask_total for row in all_expiring)
        avg_ask_aav = total_ask_value / total_expiring if total_expiring > 0 else 0
        
        # Position breakdown
        position_breakdown = {}
        for row in all_expiring:
            pos = row.pos
            if pos not in position_breakdown:
                position_breakdown[pos] = 0
            position_breakdown[pos] += 1
        
        return ContractStatsRes(
            total_expiring=total_expiring,
            total_trade_block=total_trade_block,
            avg_ask_aav=avg_ask_aav,
            total_ask_value=total_ask_value,
            position_breakdown=position_breakdown
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contract stats: {str(e)}")

class BulkCpuPassReq(BaseModel):
    season: int
    team_ids: List[int]
    seed: int = 12345

class BulkCpuPassRes(BaseModel):
    results: List[CpuPassRes]
    total_resigned: int
    total_trade_block: int

@router.post("/cpu/bulk_preseason_pass", response_model=BulkCpuPassRes)
def bulk_cpu_preseason(body: BulkCpuPassReq, sess: Session = Depends(get_session)):
    """Run CPU preseason contract decisions for multiple teams."""
    try:
        results = []
        total_resigned = 0
        total_trade_block = 0
        
        for team_id in body.team_ids:
            result = cpu_preseason_contract_pass(sess, body.season, team_id, body.seed + team_id)
            results.append(CpuPassRes(**result.__dict__))
            total_resigned += len(result.resign_ids)
            total_trade_block += len(result.trade_block_ids)
        
        return BulkCpuPassRes(
            results=results,
            total_resigned=total_resigned,
            total_trade_block=total_trade_block
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run bulk CPU preseason pass: {str(e)}")

class ContractHistoryRes(BaseModel):
    player_id: int
    contracts: List[dict]

@router.get("/history/{player_id}", response_model=ContractHistoryRes)
def get_player_contract_history(player_id: int, sess: Session = Depends(get_session)):
    """Get contract history for a specific player."""
    try:
        from sqlmodel import select
        from app.models.contracts import PlayerContract
        
        contracts = list(sess.exec(select(PlayerContract).where(
            PlayerContract.player_id == player_id
        ).order_by(PlayerContract.start_season.desc())))
        
        contract_data = [
            {
                "contract_id": c.contract_id,
                "team_id": c.team_id,
                "start_season": c.start_season,
                "end_season": c.end_season,
                "aav": c.aav,
                "guaranteed": c.guaranteed,
                "is_active": c.is_active
            }
            for c in contracts
        ]
        
        return ContractHistoryRes(
            player_id=player_id,
            contracts=contract_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contract history: {str(e)}")

