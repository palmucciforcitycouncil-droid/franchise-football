# app/services/contracts_service.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from sqlmodel import Session, select
from app.models.contracts import PlayerContract, PlayerContractAsk, TeamTradeBlock
from app.models.core_min import Player

@dataclass
class ExpiringDTO:
    player_id: int
    name: str
    pos: str
    team_id: int
    cap_hit_current: int
    desired_years: int
    desired_total: int
    desired_aav: int
    on_trade_block: bool

def current_contract(sess: Session, player_id: int) -> Optional[PlayerContract]:
    """Get the current active contract for a player."""
    return sess.exec(select(PlayerContract).where(PlayerContract.player_id==player_id, PlayerContract.is_active==True)).first()

def get_or_create_ask(sess: Session, player_id: int, season: int) -> PlayerContractAsk:
    """Get or create a contract ask for a player, updating it if needed."""
    ask = sess.exec(select(PlayerContractAsk).where(PlayerContractAsk.player_id==player_id)).first()
    if not ask:
        ask = PlayerContractAsk(player_id=player_id, updated_season=season)
        sess.add(ask)
        sess.commit()
        sess.refresh(ask)
    if ask.updated_season != season:
        # Simple year-over-year inflation by 3% (placeholder); you can plug a performance model here
        ask.desired_aav = max(1_000_000, int(ask.desired_aav * 1.03))
        ask.desired_total = ask.desired_aav * ask.desired_years
        ask.updated_season = season
        sess.add(ask)
        sess.commit()
    return ask

def is_expiring(sess: Session, contract: PlayerContract, season: int) -> bool:
    """Check if a contract is expiring in the given season."""
    return contract and contract.is_active and contract.end_season == season

def list_expiring_for_team(sess: Session, team_id: int, season: int) -> List[ExpiringDTO]:
    """Get all expiring contracts for a team."""
    rows: List[ExpiringDTO] = []
    players = list(sess.exec(select(Player).where(Player.team_id==team_id)))
    tblock_ids = {tb.player_id for tb in sess.exec(select(TeamTradeBlock).where(
        TeamTradeBlock.team_id==team_id, TeamTradeBlock.season==season, TeamTradeBlock.is_active==True))}
    for p in players:
        con = current_contract(sess, p.id)  # Using p.id instead of p.player_id
        if not con or not is_expiring(sess, con, season):
            continue
        ask = get_or_create_ask(sess, p.id, season)  # Using p.id instead of p.player_id
        rows.append(ExpiringDTO(
            player_id=p.id, name=p.name, pos=p.pos, team_id=team_id,
            cap_hit_current=p.cap_hit_current or con.aav,  # Simple proxy
            desired_years=ask.desired_years, desired_total=ask.desired_total, desired_aav=ask.desired_aav,
            on_trade_block=p.id in tblock_ids
        ))
    return rows

def release_player(sess: Session, player_id: int):
    """Release a player to free agency."""
    p = sess.get(Player, player_id)
    if not p:
        return
    con = current_contract(sess, player_id)
    if con:
        con.is_active = False
        sess.add(con)
    p.team_id = None
    p.cap_hit_current = 0
    sess.add(p)
    sess.commit()

def resign_player(sess: Session, player_id: int, team_id: int, season: int, years: int, total: int):
    """Re-sign a player to a new contract."""
    con = current_contract(sess, player_id)
    if con:
        con.is_active = False
        sess.add(con)
    aav = int(total / years)
    new_con = PlayerContract(player_id=player_id, team_id=team_id, start_season=season, end_season=season+years-1, aav=aav, is_active=True)
    p = sess.get(Player, player_id)
    p.team_id = team_id
    p.cap_hit_current = aav
    ask = get_or_create_ask(sess, player_id, season)
    ask.desired_years = years
    ask.desired_total = total
    ask.desired_aav = aav
    sess.add(new_con)
    sess.add(p)
    sess.add(ask)
    sess.commit()