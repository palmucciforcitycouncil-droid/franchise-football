# scripts/debug_draft_integration.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.services.draft import generate_draft_class, assign_picks, make_selection
from app.services.draft_integration import finalize_draft_class
from app.models.draft import Prospect, DraftPick
from app.models.core_min import Player

def main():
    season = 2042
    eng = get_engine()
    with Session(eng) as s:
        # Generate draft class and picks
        generate_draft_class(s, season, seed=2025)
        assign_picks(s, season)
        
        # Get a QB prospect and first pick
        qb_prospect = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="QB").order_by(Prospect.overall.desc())).first()
        pick = s.exec(select(DraftPick).where(DraftPick.season==season, DraftPick.overall_pick==1)).first()
        
        print(f"QB prospect: {qb_prospect.name} (drafted_by_team_id: {qb_prospect.drafted_by_team_id})")
        print(f"Pick team: {pick.team_id}")
        
        # Check existing players on this team
        existing_players = s.exec(select(Player).where(Player.team_id==pick.team_id)).all()
        print(f"Existing players on team {pick.team_id}: {len(existing_players)}")
        for p in existing_players:
            print(f"  {p.name} - rookie: {getattr(p, 'is_rookie', 'N/A')} - season: {getattr(p, 'rookie_season', 'N/A')}")
        
        # Make selection
        make_selection(s, season, 1, qb_prospect.id, pick.team_id)
        print(f"After selection - drafted_by_team_id: {qb_prospect.drafted_by_team_id}")
        
        # Finalize
        res = finalize_draft_class(s, season, seed=2025)
        print(f"Finalize result: {res}")
        
        # Check players after finalize
        players_after = s.exec(select(Player).where(Player.team_id==pick.team_id)).all()
        print(f"Players after finalize: {len(players_after)}")
        for p in players_after:
            print(f"  {p.name} - rookie: {getattr(p, 'is_rookie', 'N/A')} - season: {getattr(p, 'rookie_season', 'N/A')}")

if __name__ == "__main__":
    main()

