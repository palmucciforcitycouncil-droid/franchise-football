# scripts/test_pipeline_and_ratings.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.models.draft import Prospect
from app.models.core_min import Player
from app.services.draft_pipeline import seed_four_year_pipeline, rollover_draft_pipeline, finalize_draft_year

def test_pipeline_and_get_ratings():
    print("=== Testing 4-Year Draft Pipeline ===\n")
    
    season = 2028
    eng = get_engine()
    with Session(eng) as s:
        # 1. Seed the pipeline
        print("1. Seeding 4-year pipeline...")
        res = seed_four_year_pipeline(s, season, master_seed=2025)
        print(f"   Created: {res['created']} prospects")
        
        # 2. Show initial prospect distribution
        print("\n2. Initial prospect distribution:")
        for class_year in ["FR", "SO", "JR", "SR"]:
            count = len(s.exec(select(Prospect).where(Prospect.class_year==class_year)).all())
            print(f"   {class_year}: {count} prospects")
        
        # 3. Show some sample prospects with ratings
        print("\n3. Sample prospects by class:")
        for class_year in ["FR", "SO", "JR", "SR"]:
            prospects = s.exec(select(Prospect).where(Prospect.class_year==class_year).order_by(Prospect.overall.desc()).limit(5)).all()
            print(f"\n   {class_year} Class (Top 5):")
            for p in prospects:
                print(f"     {p.name} ({p.pos}) - Overall: {p.overall}, Age: {p.age}")
        
        # 4. Rollover to next season
        print(f"\n4. Rolling over to season {season+1}...")
        res = rollover_draft_pipeline(s, season+1, master_seed=2025)
        print(f"   Status: {res['status']}")
        print(f"   Early declared: {res['early_declared']}")
        print(f"   Promotions: {res['promoted']}")
        
        # 5. Show SR class after rollover
        print(f"\n5. SR class (eligible for {season+1} draft):")
        srs = s.exec(select(Prospect).where(
            Prospect.class_year=="SR", 
            Prospect.eligible_season==season+1
        ).order_by(Prospect.overall.desc())).all()
        
        print(f"   Total SR prospects: {len(srs)}")
        print("   Top 10 SR prospects:")
        for i, p in enumerate(srs[:10], 1):
            print(f"     {i:2d}. {p.name} ({p.pos}) - Overall: {p.overall}, Age: {p.age}")
        
        # 6. Show all prospect ratings by class
        print(f"\n6. All prospect ratings by class:")
        all_prospects = s.exec(select(Prospect).order_by(Prospect.class_year, Prospect.overall.desc())).all()
        
        class_ratings = {"FR": [], "SO": [], "JR": [], "SR": []}
        for p in all_prospects:
            if p.class_year in class_ratings:
                class_ratings[p.class_year].append(p.overall)
        
        for class_year, ratings in class_ratings.items():
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                min_rating = min(ratings)
                max_rating = max(ratings)
                print(f"   {class_year}: {len(ratings)} prospects, Avg: {avg_rating:.1f}, Range: {min_rating}-{max_rating}")
        
        # 7. Test UDFA promotion
        print(f"\n7. Testing UDFA promotion...")
        # Mark some SRs as undrafted
        undrafted_count = 0
        for p in srs[:10]:  # Take first 10 SRs as undrafted
            if p.drafted_by_team_id is None:
                undrafted_count += 1
        
        print(f"   Undrafted SRs available: {undrafted_count}")
        
        # Promote UDFAs
        res = finalize_draft_year(s, season+1)
        print(f"   UDFAs promoted: {res['udfa_promoted']}")
        print(f"   Prospects deleted: {res['prospects_deleted']}")
        
        # 8. Show player ratings (including UDFAs)
        print(f"\n8. Player ratings (including UDFAs):")
        players = s.exec(select(Player).order_by(Player.overall.desc())).all()
        
        if players:
            print(f"   Total players: {len(players)}")
            print("   Top 20 players by overall rating:")
            for i, p in enumerate(players[:20], 1):
                name = getattr(p, 'name', f"Player {p.id}")
                pos = getattr(p, 'position', getattr(p, 'pos', 'Unknown'))
                overall = getattr(p, 'overall', 'N/A')
                team_id = getattr(p, 'team_id', 'FA')
                print(f"     {i:2d}. {name} ({pos}) - Overall: {overall}, Team: {team_id}")
            
            # Show rating distribution
            ratings = [getattr(p, 'overall', 0) for p in players if getattr(p, 'overall', None) is not None]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                min_rating = min(ratings)
                max_rating = max(ratings)
                print(f"\n   Player rating stats:")
                print(f"     Average: {avg_rating:.1f}")
                print(f"     Range: {min_rating}-{max_rating}")
                print(f"     Count: {len(ratings)}")
        else:
            print("   No players found")
        
        # 9. Show final pipeline state
        print(f"\n9. Final pipeline state:")
        remaining_prospects = s.exec(select(Prospect)).all()
        print(f"   Remaining prospects: {len(remaining_prospects)}")
        
        for class_year in ["FR", "SO", "JR", "SR"]:
            count = len(s.exec(select(Prospect).where(Prospect.class_year==class_year)).all())
            print(f"   {class_year}: {count} prospects")
    
    print("\n=== Pipeline Test Complete ===")

if __name__ == "__main__":
    test_pipeline_and_get_ratings()


