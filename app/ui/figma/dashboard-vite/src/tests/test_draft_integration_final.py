# tests/test_draft_integration_final.py
from sqlmodel import Session, select
from app.db import get_engine
from app.services.draft import generate_draft_class, assign_picks
from app.services.draft_integration import finalize_draft_class
from app.models.draft import Prospect, DraftPick
from app.models.core_min import Player
from app.models.contracts import Contract

def test_draft_integration_complete_flow():
    """Test the complete draft integration flow."""
    season = 2043  # Use a higher season number to avoid conflicts
    eng = get_engine()
    with Session(eng) as s:
        # Generate draft class and picks
        generate_draft_class(s, season, seed=2025)
        assign_picks(s, season)
        
        # Get a QB prospect and use a different team (team 2)
        qb_prospect = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="QB").order_by(Prospect.overall.desc())).first()
        pick = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==2)).first()  # Use pick 2 instead of pick 1
        
        # Make selection
        from app.services.draft import make_selection
        make_selection(s, season, 2, qb_prospect.id, pick.team_id)  # Use pick 2
        
        # Finalize
        res = finalize_draft_class(s, season, seed=2025)
        assert res["status"] == "ok"
        assert res["players_created"] > 0
        assert res["contracts_created"] > 0
        
        # Check that the player was created with correct attributes
        players = s.exec(select(Player).where(Player.team_id==pick.team_id)).all()
        rookie_players = [p for p in players if hasattr(p, 'is_rookie') and p.is_rookie and hasattr(p, 'rookie_season') and p.rookie_season == season]
        assert len(rookie_players) == 1
        player = rookie_players[0]
        
        # Check position mapping
        assert player.pos == qb_prospect.pos
        
        # Check that QB-specific attributes are set
        assert player.throw_power > 50  # Should be higher for QB
        assert player.throw_accuracy > 50  # Should be higher for QB
        
        # Check age
        assert player.age == 22  # Rookie age
        
        # Check rookie flags
        assert player.is_rookie is True
        assert player.rookie_season == season
        
        # Check contract
        contracts = s.exec(select(Contract).where(Contract.start_season==season)).all()
        assert len(contracts) == 1
        contract = contracts[0]
        assert contract.is_rookie is True
        assert contract.years == 4
        assert contract.aav > 500  # Should be high for first round
        
        # Test idempotency
        res2 = finalize_draft_class(s, season, seed=2025)
        assert res2["status"] == "ok"
        assert res2["players_created"] == 0
        assert res2["contracts_created"] == 0
