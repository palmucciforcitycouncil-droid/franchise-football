# scripts/test_draft_integration_demo.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.services.draft import generate_draft_class, assign_picks, make_selection
from app.services.draft_integration import finalize_draft_class
from app.models.draft import Prospect, DraftPick
from app.models.core_min import Player
from app.models.contracts import Contract

def main():
    print("=== DRAFT INTEGRATION DEMO ===")
    
    season = 2031
    eng = get_engine()
    
    with Session(eng) as s:
        # Generate draft class and picks
        print("\n1. Generating draft class and picks...")
        generate_draft_class(s, season, seed=777)
        assign_picks(s, season)
        
        # Get best WR and first pick
        wr = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="WR").order_by(Prospect.overall.desc())).first()
        p1 = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==1)).first()
        
        print(f"   Best WR: {wr.name} (overall: {wr.overall})")
        print(f"   First pick team: {p1.team_id}")
        
        # Make selection
        print("\n2. Making selection...")
        make_selection(s, season, 1, wr.id, p1.team_id)
        print(f"   Selected {wr.name} with pick 1")
        
        # Finalize
        print("\n3. Finalizing draft...")
        res = finalize_draft_class(s, season, seed=777)
        print(f"   Result: {res}")
        
        # Check what was created
        print("\n4. Checking created players and contracts...")
        players = s.exec(select(Player).where(Player.team_id==p1.team_id)).all()
        print(f"   Players on team {p1.team_id}: {len(players)}")
        
        for player in players:
            print(f"     Player: {getattr(player, 'name', 'Unknown')} (ID: {getattr(player, 'id', 'Unknown')})")
            if hasattr(player, 'is_rookie'):
                print(f"       is_rookie: {player.is_rookie}")
            if hasattr(player, 'rookie_season'):
                print(f"       rookie_season: {player.rookie_season}")
        
        contracts = s.exec(select(Contract).where(Contract.start_season==season)).all()
        print(f"   Contracts for season {season}: {len(contracts)}")
        
        for contract in contracts:
            print(f"     Contract: player_id={contract.player_id}, team_id={contract.team_id}, aav={contract.aav}, years={contract.years}, is_rookie={contract.is_rookie}")
        
        # Check if there's a contract for our player
        if players:
            player = players[0]
            player_id = getattr(player, "player_id", getattr(player, "id", None))
            print(f"\n   Looking for contract with player_id={player_id}")
            contract = s.exec(select(Contract).where(Contract.player_id==player_id, Contract.start_season==season)).first()
            if contract:
                print(f"   Found contract: {contract}")
            else:
                print(f"   No contract found for player_id={player_id}")

if __name__ == "__main__":
    main()
