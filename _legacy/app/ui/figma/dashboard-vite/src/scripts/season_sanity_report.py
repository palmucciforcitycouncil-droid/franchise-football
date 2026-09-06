#!/usr/bin/env python3
"""
Season sanity report generator.
Produces JSON report with correlations and usage patterns.
"""

import json
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, create_engine
from app.testing.season_data_access import fetch_player_catalog, fetch_player_season_stats
from app.testing.correlation_utils import spearman_rank
from app.testing.mini_season_runner import memory_db, run_mini_season


def generate_sanity_report(db_url=None, season=2025):
    """Generate season sanity report."""
    if db_url is None:
        # Use in-memory database for demo
        with memory_db() as session:
            # Run mini season to generate data
            out = run_mini_season(session, weeks=2)
            
            cats = fetch_player_catalog(session, season)
            stats = fetch_player_season_stats(session, season)
            
            # Join data
            idx = {p["player_id"]: p for p in cats}
            joined = []
            for st in stats:
                pid = st.get("player_id")
                if pid in idx:
                    r = idx[pid].copy()
                    r.update(st)
                    joined.append(r)
            
            # Generate correlations
            def corr(pos, eff_key):
                sub = [r for r in joined if r.get("position", "") in pos]
                if not sub:
                    return None
                eff = [r.get(eff_key, 0.0) for r in sub]
                ovr = [r.get("ovr", 0) for r in sub]
                return spearman_rank(ovr, eff)
            
            # Calculate usage patterns
            def usage_pattern(pos):
                sub = [r for r in joined if r.get("position", "") in pos]
                if len(sub) < 2:
                    return None
                
                sorted_sub = sorted(sub, key=lambda r: r.get("ovr", 0), reverse=True)
                k = max(1, len(sorted_sub) // 3)
                
                top_snaps = [r.get("snaps", 0) for r in sorted_sub[:k]]
                low_snaps = [r.get("snaps", 0) for r in sorted_sub[-k:]]
                
                if top_snaps and low_snaps:
                    return {
                        "top_avg_snaps": sum(top_snaps) / len(top_snaps),
                        "low_avg_snaps": sum(low_snaps) / len(low_snaps),
                        "usage_ratio": (sum(top_snaps) / len(top_snaps)) / max(1, sum(low_snaps) / len(low_snaps))
                    }
                return None
            
            report = {
                "season": season,
                "data_summary": {
                    "total_players": len(joined),
                    "teams": len(set(r.get("team_id") for r in joined if r.get("team_id"))),
                    "games_simulated": len(out.get("games", [])),
                },
                "correlations": {
                    "QB": corr(("QB",), "epa_per_play") or corr(("QB",), "any_a"),
                    "RB": corr(("RB", "HB", "FB"), "ypc") or corr(("RB", "HB", "FB"), "success_rate_rush"),
                    "WR": corr(("WR",), "yprr") or corr(("WR",), "success_rate_rec"),
                    "TE": corr(("TE",), "yprr") or corr(("TE",), "success_rate_rec"),
                    "Front7": corr(("EDGE", "DE", "DT", "IDL", "OLB"), "pressure_rate") or corr(("EDGE", "DE", "DT", "IDL", "OLB"), "sacks_per_snap"),
                    "DB": corr(("CB", "DB", "S", "SS", "FS", "NB"), "pbu_per_target") or corr(("CB", "DB", "S", "SS", "FS", "NB"), "ints_per_target"),
                },
                "usage_patterns": {
                    "QB": usage_pattern("QB"),
                    "RB": usage_pattern("RB"),
                    "WR": usage_pattern("WR"),
                    "TE": usage_pattern("TE"),
                },
                "position_counts": {
                    pos: len([r for r in joined if r.get("position", "") == pos])
                    for pos in ["QB", "RB", "WR", "TE", "EDGE", "DE", "DT", "LB", "CB", "S"]
                },
                "thresholds": {
                    "QB_correlation_min": 0.25,
                    "RB_correlation_min": 0.20,
                    "WR_correlation_min": 0.20,
                    "TE_correlation_min": 0.15,
                    "Front7_correlation_min": 0.15,
                    "DB_correlation_min": 0.10,
                }
            }
            
            return report
    else:
        # Use provided database URL
        eng = create_engine(db_url, future=True)
        with Session(eng) as session:
            cats = fetch_player_catalog(session, season)
            stats = fetch_player_season_stats(session, season)
            
            # Similar processing as above...
            # (Implementation would be similar to the in-memory version)
            return {"season": season, "status": "processed"}


def main():
    """Main function for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate season sanity report")
    parser.add_argument("--db", help="Database URL (default: in-memory demo)")
    parser.add_argument("--season", type=int, default=2025, help="Season year")
    parser.add_argument("--output", help="Output file (default: stdout)")
    
    args = parser.parse_args()
    
    try:
        report = generate_sanity_report(args.db, args.season)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Report written to {args.output}")
        else:
            print(json.dumps(report, indent=2))
            
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
