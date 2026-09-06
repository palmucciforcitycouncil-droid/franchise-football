# scripts/test_draft_compare_demo.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import get_engine
from app.services.draft import generate_draft_class, assign_picks
from app.models.draft import Prospect
from app.services.draft_compare import compare_prospects, board_score

def main():
    print("=== Draft Comparison Demo ===\n")
    
    # Create a test draft class
    season = 2025
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=12345)
        assign_picks(s, season)
        
        # Get some prospects for comparison
        prospects = s.exec(select(Prospect).where(Prospect.season == season)).all()
        
        if len(prospects) >= 3:
            # Test board score calculation
            print("1. Board Score Calculation:")
            for i, prospect in enumerate(prospects[:3]):
                score = board_score(prospect)
                print(f"  {i+1}. {prospect.name} ({prospect.pos}) - Overall: {prospect.overall}, Board Score: {score:.2f}")
            
            # Test prospect comparison
            print("\n2. Prospect Comparison:")
            ids = [prospects[0].id, prospects[1].id, prospects[2].id]
            
            result = compare_prospects(s, season, ids)
            
            print(f"Season: {result['season']}")
            print(f"Count: {result['count']}")
            print(f"Items: {len(result['items'])}")
            
            print("\nProspect Details:")
            for i, item in enumerate(result['items']):
                print(f"  {i+1}. {item['name']} ({item['pos']})")
                print(f"     Overall: {item['metrics']['overall']}, Potential: {item['metrics']['potential']}")
                print(f"     Board Score: {item['board_score']}")
                print(f"     Positional Percentiles:")
                for field, pct in item['percentiles_pos'].items():
                    print(f"       {field}: {pct}%")
                print()
            
            # Test diff table
            print("3. Comparison Deltas:")
            diff = result['diff']
            print(f"Baseline: {diff['baseline_id']}")
            for row in diff['rows']:
                print(f"  {row['name']} ({row['pos']}):")
                for field, delta in row['deltas'].items():
                    print(f"    {field}: {delta:+}")
                print()
            
            # Test API endpoint simulation
            print("4. API Endpoint Test:")
            print(f"GET /draft/{season}/board/compare?ids={','.join(map(str, ids))}")
            print("Response structure:")
            print(f"  - season: {result['season']}")
            print(f"  - count: {result['count']}")
            print(f"  - items: {len(result['items'])} prospects")
            print(f"  - diff: {len(diff['rows'])} comparisons")
            
        else:
            print("Not enough prospects generated for testing")
    
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    main()
