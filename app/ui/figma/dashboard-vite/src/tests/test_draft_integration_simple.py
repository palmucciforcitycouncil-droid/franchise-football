# tests/test_draft_integration_simple.py
from sqlmodel import Session, select
from app.db import get_engine
from app.services.draft import generate_draft_class, assign_picks
from app.services.draft_integration import finalize_draft_class
from app.models.draft import Prospect, DraftPick
from app.models.core_min import Player
from app.models.contracts import Contract
import os

def _clear_db():
    """Clear the database for clean tests."""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Remove existing database
    if os.path.exists("franchise.db"):
        try:
            os.remove("franchise.db")
        except:
            pass
    
    # Create fresh database
    from scripts.create_tables import main as create_tables_main
    create_tables_main()

def test_finalize_promotes_and_contracts():
    """Test that finalize promotes prospects to players and creates contracts."""
    _clear_db()
    season = 2032
    eng = get_engine()
    with Session(eng) as s:
        # build class + picks
        generate_draft_class(s, season, seed=777)
        assign_picks(s, season)
        # pick best WR for pick 1
        wr = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="WR").order_by(Prospect.overall.desc())).first()
        p1 = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==1)).first()
        from app.services.draft import make_selection
        make_selection(s, season, 1, wr.id, p1.team_id)

        res = finalize_draft_class(s, season, seed=777)
        assert res["status"] == "ok"
        assert res["players_created"] > 0
        assert res["contracts_created"] > 0
        
        # verify a Player exists on that team with rookie flags
        pl = s.exec(select(Player).where(Player.team_id==p1.team_id)).first()
        assert pl is not None
        if hasattr(pl, "is_rookie"):
            assert pl.is_rookie is True
        if hasattr(pl, "rookie_season"):
            assert pl.rookie_season == season
        
        # Contract exists
        player_id = getattr(pl, "player_id", getattr(pl, "id", None))
        c = s.exec(select(Contract).where(Contract.player_id==player_id, Contract.start_season==season)).first()
        assert c is not None and c.is_rookie is True and c.years >= 4

def test_draft_integration_idempotency():
    """Test that finalize is idempotent - running multiple times doesn't duplicate players/contracts."""
    _clear_db()
    season = 2033
    eng = get_engine()
    with Session(eng) as s:
        # Generate draft class and picks
        generate_draft_class(s, season, seed=2025)
        assign_picks(s, season)
        
        # Make a selection
        wr = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="WR").order_by(Prospect.overall.desc())).first()
        p1 = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==1)).first()
        from app.services.draft import make_selection
        make_selection(s, season, 1, wr.id, p1.team_id)
        
        # First finalize
        res1 = finalize_draft_class(s, season, seed=2025)
        assert res1["status"] == "ok"
        players_created_1 = res1["players_created"]
        contracts_created_1 = res1["contracts_created"]
        
        # Second finalize (should be idempotent)
        res2 = finalize_draft_class(s, season, seed=2025)
        assert res2["status"] == "ok"
        players_created_2 = res2["players_created"]
        contracts_created_2 = res2["contracts_created"]
        
        # Should not create additional players/contracts
        assert players_created_2 == 0
        assert contracts_created_2 == 0

def test_rookie_wage_scale():
    """Test that rookie contracts follow the wage scale."""
    _clear_db()
    season = 2034
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=2025)
        assign_picks(s, season)
        
        # Make selections for different rounds
        prospects = s.exec(select(Prospect).where(Prospect.season==season).order_by(Prospect.overall.desc())).all()
        picks = s.exec(select(DraftPick).where(DraftPick.season==season).order_by(DraftPick.overall_pick)).all()
        
        # Pick first 5 prospects
        from app.services.draft import make_selection
        for i in range(5):
            make_selection(s, season, picks[i].overall_pick, prospects[i].id, picks[i].team_id)
        
        # Finalize
        finalize_draft_class(s, season, seed=2025)
        
        # Check contracts
        contracts = s.exec(select(Contract).where(Contract.start_season==season)).all()
        assert len(contracts) == 5
        
        # First pick should have highest AAV (round 1)
        first_contract = contracts[0]
        assert first_contract.is_rookie is True
        assert first_contract.years == 4
        assert first_contract.aav > 500  # Should be high for first round
        
        # All should be rookie contracts
        for contract in contracts:
            assert contract.is_rookie is True
            assert contract.years == 4
            assert contract.aav >= 80  # Minimum wage

def test_prospect_to_player_mapping():
    """Test that prospect attributes are correctly mapped to player attributes."""
    _clear_db()
    season = 2036
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=2025)
        assign_picks(s, season)
        
        # Get a QB prospect
        qb_prospect = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="QB").order_by(Prospect.overall.desc())).first()
        pick = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==1)).first()
        
        from app.services.draft import make_selection
        make_selection(s, season, 1, qb_prospect.id, pick.team_id)
        
        # Finalize
        finalize_draft_class(s, season, seed=2025)
        
        # Check that the player was created with correct attributes
        # Find the player that was just created (should be the only rookie on this team for this season)
        players = s.exec(select(Player).where(Player.team_id==pick.team_id)).all()
        rookie_players = [p for p in players if hasattr(p, 'is_rookie') and p.is_rookie and hasattr(p, 'rookie_season') and p.rookie_season == season]
        assert len(rookie_players) == 1
        player = rookie_players[0]
        
        # Check position mapping
        if hasattr(player, "pos"):
            assert player.pos == qb_prospect.pos
        elif hasattr(player, "position"):
            assert player.position == qb_prospect.pos
        
        # Check that QB-specific attributes are set
        if hasattr(player, "throw_power"):
            assert player.throw_power > 50  # Should be higher for QB
        if hasattr(player, "throw_accuracy"):
            assert player.throw_accuracy > 50  # Should be higher for QB
        
        # Check age
        if hasattr(player, "age"):
            assert player.age == 22  # Rookie age
        
        # Check rookie flags
        if hasattr(player, "is_rookie"):
            assert player.is_rookie is True
        if hasattr(player, "rookie_season"):
            assert player.rookie_season == season
