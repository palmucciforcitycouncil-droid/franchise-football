# scripts/draft_pipeline_demo.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.models.draft import Prospect
from app.services.draft_pipeline import seed_four_year_pipeline, rollover_draft_pipeline, finalize_draft_year

def main():
    print("=== 4-Year Draft Pipeline Demo ===\n")
    
    season = 2028
    eng = get_engine()
    with Session(eng) as s:
        # 1. Seed initial 4-year pipeline
        print("1. Seeding 4-year pipeline for season", season)
        res = seed_four_year_pipeline(s, season, master_seed=2025)
        print(f"   Created: {res['created']} prospects")
        print(f"   Classes: {res['classes']}")
        
        # Show initial distribution
        print("\n2. Initial class distribution:")
        for class_year in ["FR", "SO", "JR", "SR"]:
            count = len(s.exec(select(Prospect).where(Prospect.class_year==class_year)).all())
            print(f"   {class_year}: {count} prospects")
        
        # Show some FR prospects
        print("\n3. Sample FR prospects:")
        frs = s.exec(select(Prospect).where(Prospect.class_year=="FR").limit(5)).all()
        for p in frs:
            print(f"   {p.name} ({p.pos}) - Overall: {p.overall}, Age: {p.age}")
        
        # 4. Rollover to next season
        print(f"\n4. Rolling over to season {season+1}")
        res = rollover_draft_pipeline(s, season+1, master_seed=2025)
        print(f"   Status: {res['status']}")
        print(f"   Early declared: {res['early_declared']}")
        print(f"   Promotions: {res['promoted']}")
        
        # Show SR class (eligible for draft)
        print(f"\n5. SR class (eligible for {season+1} draft):")
        srs = s.exec(select(Prospect).where(
            Prospect.class_year=="SR", 
            Prospect.eligible_season==season+1
        ).order_by(Prospect.overall.desc()).limit(10)).all()
        
        for p in srs:
            print(f"   {p.name} ({p.pos}) - Overall: {p.overall}, Age: {p.age}")
        
        # Show position distribution in SR class
        print(f"\n6. SR class position distribution:")
        pos_counts = {}
        for p in srs:
            pos_counts[p.pos] = pos_counts.get(p.pos, 0) + 1
        
        all_srs = s.exec(select(Prospect).where(
            Prospect.class_year=="SR", 
            Prospect.eligible_season==season+1
        )).all()
        
        for pos in ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "K", "P"]:
            count = len([p for p in all_srs if p.pos == pos])
            if count > 0:
                print(f"   {pos}: {count}")
        
        # 7. Show watchlist functionality
        print(f"\n7. Watchlist functionality:")
        # Add some prospects to watchlist
        watchlist_prospects = s.exec(select(Prospect).where(Prospect.class_year=="JR").limit(3)).all()
        for p in watchlist_prospects:
            p.watchlist = True
            s.add(p)
        s.commit()
        
        watchlist = s.exec(select(Prospect).where(Prospect.watchlist==True)).all()
        print(f"   Watchlisted prospects: {len(watchlist)}")
        for p in watchlist[:3]:
            print(f"   - {p.name} ({p.pos}) - Overall: {p.overall}")
        
        # 8. Show UDFA promotion (simulate undrafted SRs)
        print(f"\n8. UDFA promotion simulation:")
        # Mark some SRs as undrafted
        undrafted_srs = s.exec(select(Prospect).where(
            Prospect.class_year=="SR", 
            Prospect.eligible_season==season+1
        ).limit(5)).all()
        
        for p in undrafted_srs:
            p.drafted_by_team_id = None  # Ensure they're undrafted
        
        res = finalize_draft_year(s, season+1)
        print(f"   UDFAs promoted: {res['udfa_promoted']}")
        print(f"   Prospects deleted: {res['prospects_deleted']}")
        
        # 9. Show final pipeline state
        print(f"\n9. Final pipeline state:")
        for class_year in ["FR", "SO", "JR", "SR"]:
            count = len(s.exec(select(Prospect).where(Prospect.class_year==class_year)).all())
            print(f"   {class_year}: {count} prospects")
        
        # Show new FR class
        new_frs = s.exec(select(Prospect).where(
            Prospect.class_year=="FR",
            Prospect.expected_draft_season==season+4
        ).limit(3)).all()
        
        print(f"\n10. New FR class (for {season+4} draft):")
        for p in new_frs:
            print(f"   {p.name} ({p.pos}) - Overall: {p.overall}, Age: {p.age}")
    
    print("\n=== Demo Complete ===")
    print("\nKey features demonstrated:")
    print("+ 4-year pipeline seeding (SR/JR/SO/FR)")
    print("+ Seasonal rollover with development")
    print("+ Early declaration logic")
    print("+ Position distribution management")
    print("+ Watchlist functionality")
    print("+ UDFA auto-promotion")
    print("+ Age progression")
    print("+ OVR recalculation")

if __name__ == "__main__":
    main()


