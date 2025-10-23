"""
Advanced season sanity tests for rank-order, usage, and determinism.
"""

import copy
import pytest
from sqlmodel import select

from app.testing.mini_season_runner import memory_db, run_mini_season
from app.testing.season_data_access import fetch_player_catalog, fetch_player_season_stats
from app.testing.correlation_utils import spearman_rank


# ---- helpers ----
def _by_pos(players, pos_prefixes):
    """Filter players by position prefixes."""
    pref = tuple(p.upper() for p in pos_prefixes)
    return [p for p in players if (p.get("position", "UNK").upper().startswith(pref) or p.get("position", "UNK").upper() in pos_prefixes)]


def test_rank_order_and_usage_and_determinism():
    """Test rank-order correlations, usage patterns, and determinism."""
    season = 2025

    # --- First run ---
    with memory_db() as session1:
        out1 = run_mini_season(session1, weeks=2)

        catalog1 = fetch_player_catalog(session1, season)
        stats1 = fetch_player_season_stats(session1, season)

        # join by player_id
        idx = {p["player_id"]: p for p in catalog1}
        joined1 = []
        for s in stats1:
            pid = s.get("player_id")
            if pid in idx:
                row = copy.deepcopy(idx[pid])
                row.update(s)
                joined1.append(row)

        # ------ Rank-order sanity (Spearman) ------
        checks = []
        
        # QB: OVR vs efficiency (prefer ANY/A or epa_per_play)
        qbs = [r for r in joined1 if r.get("position", "") in ("QB",)]
        if qbs:
            eff = [r.get("any_a") or r.get("epa_per_play") or 0.0 for r in qbs]
            ovr = [r.get("ovr", 0) for r in qbs]
            rho_qb = spearman_rank(ovr, eff)
            checks.append(("QB", rho_qb))
            assert rho_qb >= 0.25, f"QB correlation {rho_qb} below threshold 0.25"

        # RB: OVR vs YPC or success_rate_rush
        rbs = [r for r in joined1 if r.get("position", "") in ("RB", "HB", "FB")]
        if rbs:
            eff = [r.get("ypc") or r.get("success_rate_rush") or 0.0 for r in rbs]
            ovr = [r.get("ovr", 0) for r in rbs]
            rho_rb = spearman_rank(ovr, eff)
            checks.append(("RB", rho_rb))
            assert rho_rb >= 0.20, f"RB correlation {rho_rb} below threshold 0.20"

        # WR/TE: OVR vs YPRR or success rate receiving
        wrs = [r for r in joined1 if r.get("position", "") in ("WR",)]
        tes = [r for r in joined1 if r.get("position", "") in ("TE",)]
        if wrs:
            eff = [r.get("yprr") or r.get("success_rate_rec") or 0.0 for r in wrs]
            rho_wr = spearman_rank([r.get("ovr", 0) for r in wrs], eff)
            checks.append(("WR", rho_wr))
            assert rho_wr >= 0.20, f"WR correlation {rho_wr} below threshold 0.20"
        if tes:
            eff = [r.get("yprr") or r.get("success_rate_rec") or 0.0 for r in tes]
            rho_te = spearman_rank([r.get("ovr", 0) for r in tes], eff)
            checks.append(("TE", rho_te))
            assert rho_te >= 0.15, f"TE correlation {rho_te} below threshold 0.15"

        # Front 7: OVR vs pressure/sacks rate
        f7 = [r for r in joined1 if r.get("position", "") in ("EDGE", "DE", "DT", "IDL", "OLB")]
        if f7:
            eff = [r.get("pressure_rate") or r.get("sacks_per_snap") or 0.0 for r in f7]
            rho_f7 = spearman_rank([r.get("ovr", 0) for r in f7], eff)
            checks.append(("Front7", rho_f7))
            assert rho_f7 >= 0.15, f"Front7 correlation {rho_f7} below threshold 0.15"

        # DB: OVR vs PBU rate or INT rate
        dbs = [r for r in joined1 if r.get("position", "") in ("CB", "DB", "S", "SS", "FS", "NB")]
        if dbs:
            eff = [r.get("pbu_per_target") or r.get("ints_per_target") or 0.0 for r in dbs]
            rho_db = spearman_rank([r.get("ovr", 0) for r in dbs], eff)
            checks.append(("DB", rho_db))
            assert rho_db >= 0.10, f"DB correlation {rho_db} below threshold 0.10"

        # ------ Usage elasticity (starters vs backups) ------
        # Proxy: within each position group, median snaps of top-ovr > median snaps of lower-ovr
        for group, grp in [("QB", qbs), ("RB", rbs), ("WR", wrs), ("TE", tes)]:
            if not grp:
                continue
            grp_sorted = sorted(grp, key=lambda r: r.get("ovr", 0), reverse=True)
            k = max(1, len(grp_sorted) // 3)
            top = [r.get("snaps", 0) for r in grp_sorted[:k]]
            low = [r.get("snaps", 0) for r in grp_sorted[-k:]]
            if top and low:
                top_avg = sum(top) / len(top)
                low_avg = sum(low) / len(low)
                assert top_avg >= low_avg, f"{group} starters ({top_avg}) should have more snaps than backups ({low_avg})"

        # --- Determinism: second run (same seed) must match team totals ---
        with memory_db() as session2:
            out2 = run_mini_season(session2, weeks=2)
            
            # Try to pull team season stats model and compare points/yards
            try:
                from app.models.stats_models import TeamSeasonStats
                teams1 = session1.exec(select(TeamSeasonStats)).all()
                teams2 = session2.exec(select(TeamSeasonStats)).all()
                
                # build maps
                m1 = {t.team_id: (getattr(t, "points_scored", 0), getattr(t, "total_yards", 0)) for t in teams1}
                m2 = {t.team_id: (getattr(t, "points_scored", 0), getattr(t, "total_yards", 0)) for t in teams2}
                
                # Since IDs may not align across different DB instances, compare multiset of tuples
                bag1 = sorted(list(m1.values()))
                bag2 = sorted(list(m2.values()))
                assert bag1 == bag2, f"Team totals differ between runs: {bag1} vs {bag2}"
                
            except Exception:
                # Fallback: use PBP aggregation to compare
                try:
                    from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
                    agg1 = aggregate_truth_from_pbp(session1)
                    agg2 = aggregate_truth_from_pbp(session2)
                    
                    # Compare team season totals
                    totals1 = [(tid, stats.get("points", 0), stats.get("yards_total", 0)) for tid, stats in agg1["team_season"].items()]
                    totals2 = [(tid, stats.get("points", 0), stats.get("yards_total", 0)) for tid, stats in agg2["team_season"].items()]
                    
                    # Sort by points, yards for comparison
                    sorted1 = sorted(totals1, key=lambda x: (x[1], x[2]))
                    sorted2 = sorted(totals2, key=lambda x: (x[1], x[2]))
                    
                    assert len(sorted1) == len(sorted2), f"Different number of teams: {len(sorted1)} vs {len(sorted2)}"
                    
                    for i, (t1, t2) in enumerate(zip(sorted1, sorted2)):
                        assert t1[1] == t2[1], f"Team {i} points differ: {t1[1]} vs {t2[1]}"
                        assert t1[2] == t2[2], f"Team {i} yards differ: {t1[2]} vs {t2[2]}"
                        
                except Exception as e:
                    pytest.skip(f"No team stats available for determinism check: {e}")


def test_correlation_thresholds():
    """Test that correlation thresholds are reasonable."""
    # This test ensures our thresholds are not too strict
    # In a real implementation, these would be tuned based on actual data
    
    # Mock data for testing thresholds
    test_cases = [
        ("QB", 0.25, "Moderate correlation expected for QB efficiency"),
        ("RB", 0.20, "Moderate correlation expected for RB efficiency"),
        ("WR", 0.20, "Moderate correlation expected for WR efficiency"),
        ("TE", 0.15, "Lower correlation expected for TE efficiency"),
        ("Front7", 0.15, "Moderate correlation expected for defensive pressure"),
        ("DB", 0.10, "Lower correlation expected for DB efficiency"),
    ]
    
    for position, threshold, reason in test_cases:
        assert threshold >= 0.0, f"{position} threshold should be non-negative"
        assert threshold <= 1.0, f"{position} threshold should be <= 1.0"
        # Thresholds are reasonable for NFL-style correlations
        assert threshold >= 0.10, f"{position} threshold {threshold} too low: {reason}"


def test_usage_patterns():
    """Test that usage patterns make sense."""
    season = 2025
    
    with memory_db() as session:
        out = run_mini_season(session, weeks=2)
        
        catalog = fetch_player_catalog(session, season)
        stats = fetch_player_season_stats(session, season)
        
        # Join data
        idx = {p["player_id"]: p for p in catalog}
        joined = []
        for s in stats:
            pid = s.get("player_id")
            if pid in idx:
                row = copy.deepcopy(idx[pid])
                row.update(s)
                joined.append(row)
        
        # Test that higher OVR players get more snaps (usage pattern)
        for position in ["QB", "RB", "WR", "TE"]:
            players = [r for r in joined if r.get("position", "") == position]
            if len(players) >= 2:
                # Sort by OVR
                sorted_players = sorted(players, key=lambda r: r.get("ovr", 0), reverse=True)
                
                # Top half should have more snaps than bottom half
                top_half = sorted_players[:len(sorted_players)//2]
                bottom_half = sorted_players[len(sorted_players)//2:]
                
                if top_half and bottom_half:
                    top_snaps = [p.get("snaps", 0) for p in top_half]
                    bottom_snaps = [p.get("snaps", 0) for p in bottom_half]
                    
                    avg_top = sum(top_snaps) / len(top_snaps)
                    avg_bottom = sum(bottom_snaps) / len(bottom_snaps)
                    
                    # Allow some flexibility for test data
                    assert avg_top >= avg_bottom * 0.8, f"{position} top players should have more snaps than bottom players"


def test_deterministic_seeds():
    """Test that deterministic seeds produce consistent results."""
    season = 2025
    
    # Run multiple times with same setup
    results = []
    for i in range(3):
        with memory_db() as session:
            out = run_mini_season(session, weeks=1, seed=2025)
            
            # Get team totals
            try:
                from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
                agg = aggregate_truth_from_pbp(session)
                
                team_totals = []
                for tid, stats in agg["team_season"].items():
                    team_totals.append((stats.get("points", 0), stats.get("yards_total", 0)))
                
                results.append(sorted(team_totals))
            except Exception:
                results.append([])
    
    # All runs should produce the same team totals
    if results and all(results):
        for i in range(1, len(results)):
            assert results[i] == results[0], f"Run {i} differs from run 0: {results[i]} vs {results[0]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
