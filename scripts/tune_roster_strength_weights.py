"""
A3 (docs/handoff_prestige_and_coach_impact.md) -- the roster_strength.py
positional-weight tuning pass.

A1's `POSITION_WEIGHTS` were a documented first-pass CLAIM about what
matters (only "QB > K+P combined" was actually asserted). This script is
the real check the handoff's own A3 section calls for: does the sim's
actual sensitivity agree, in ordering and rough magnitude, with that
claim? Two experiments:

1. **Correlation.** Real player/coach data never changes mid-season in
   this engine (progression only runs at season rollover, which this
   script never triggers), so every team's preseason `team_rating` is
   fixed across every simulated season. For N_CORR_SEEDS different
   LEAGUE_SEEDs, simulate a full 18-week regular season against the REAL,
   UNMODIFIED database (read-only per app/core/db.py's own documented
   convention -- nothing here writes to Player/Coach), and correlate the
   fixed preseason `team_rating`/`roster_score` against that season's
   final win_pct and final power_rating (Elo). Pooling (team, seed) pairs
   across many seeds gives more statistical power than any one season,
   without conflating "does this predict outcomes" with "how much
   variance the RNG itself contributes" -- the latter is exactly what
   shows up as noise around the trend line.

2. **Sensitivity.** For a sample of position groups spanning
   POSITION_WEIGHTS' current claimed range (QB highest, K lowest, a few
   in between), swap a fixed mid-pack baseline team's REAL roster at that
   ONE group with the league's actual best team's REAL players at the
   same group -- never synthetic/out-of-range attributes, an upgrade
   built entirely from real Madden-derived data already in the DB --
   re-simulate the SAME seed with and without the swap, and measure the
   shift in the baseline team's win_pct/power_rating. Comparing shift
   size across groups tests A3's own example directly: does upgrading QB
   move outcomes more than upgrading K (the one thing POSITION_WEIGHTS
   currently asserts) actually hold in the live sim?

Every DB mutation in experiment 2 happens against a throwaway copy of the
database, restored before/after each trial -- never the real file. See
ROADMAP.md Sec 2b's two real data-persistence incidents for why that is
non-negotiable. Every season-state path (save/history/gameplan/power-rank)
is also redirected per run, the same convention tests/test_coaching.py's
`completed_season` fixture already establishes.

This is a first real tuning pass, not a final calibration. 2 seeds per
sensitivity trial catches an ordering that's badly wrong; it does not pin
exact weight values to two decimal places -- see the printed caveats at
the end of the run.

Usage:
    .venv/Scripts/python.exe scripts/tune_roster_strength_weights.py
"""
from __future__ import annotations
import os
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("LEAGUE_SEED", "2025")

from sqlmodel import select  # noqa: E402

from app.core import db as db_module  # noqa: E402
from app.data.teams import TEAMS  # noqa: E402
from app.engine import roster_strength  # noqa: E402
from app.engine.position_groups import POSITION_TO_GROUP  # noqa: E402
from app.engine.schedule import N_WEEKS  # noqa: E402
from app.models.player import Player  # noqa: E402
from app.services import coach_store, depth_chart  # noqa: E402

REAL_DB_PATH = db_module.DB_PATH
SCRATCH_DB_PATH = Path("data/_tune_scratch.db")

N_CORR_SEEDS = 14
CORR_SEED_START = 5000  # distinct range from any seed used in tests/fixtures

SENSITIVITY_GROUPS = ["QB", "T", "WR", "DE", "LB", "K"]
SENSITIVITY_SEEDS = [6001, 6002, 6003]


def _positions_for_group(group: str) -> list:
    return [p for p, g in POSITION_TO_GROUP.items() if g == group]


def _dispose_engine() -> None:
    """Windows keeps a SQLite file locked as long as SQLAlchemy's
    connection pool holds it open -- just dropping our reference
    (`_engine = None`) doesn't synchronously close pooled connections, so
    a following unlink()/copy() over the same path can hit a real
    WinError 32. `.dispose()` closes the pool immediately; caught this
    via a real crash on this script's own first fixed-bug run."""
    if db_module._engine is not None:
        db_module._engine.dispose()
    db_module._engine = None


def _use_scratch_db() -> None:
    _dispose_engine()
    shutil.copy(REAL_DB_PATH, SCRATCH_DB_PATH)
    db_module.DB_PATH = SCRATCH_DB_PATH
    depth_chart.clear_starters_cache()
    coach_store.clear_cache()


def _restore_real_db() -> None:
    _dispose_engine()
    db_module.DB_PATH = REAL_DB_PATH
    depth_chart.clear_starters_cache()
    coach_store.clear_cache()
    SCRATCH_DB_PATH.unlink(missing_ok=True)


def _run_season(seed: int, tag: str) -> dict[str, tuple[float, float]]:
    """Returns {team_abbr: (final_win_pct, final_power_rating)}."""
    os.environ["LEAGUE_SEED"] = str(seed)
    from app.services import gameplan_store, history_store, power_rank_history, save_service, season_state

    paths = [
        Path(f"data/saves/_tune_{tag}_season.json"),
        Path(f"data/saves/_tune_{tag}_history.json"),
        Path(f"data/saves/_tune_{tag}_gameplans.json"),
        Path(f"data/saves/_tune_{tag}_power_rank.json"),
    ]
    save_service.DEFAULT_SAVE_PATH, history_store.DEFAULT_PATH, \
        gameplan_store.DEFAULT_PATH, power_rank_history.DEFAULT_PATH = paths
    for p in paths:
        p.unlink(missing_ok=True)

    season_state.reset_season()
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    season = season_state.get_season()
    result = {abbr: (r.win_pct, r.power_rating) for abbr, r in season.records.items()}

    for p in paths:
        p.unlink(missing_ok=True)
    return result


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    return cov / ((vx * vy) ** 0.5) if vx and vy else 0.0


def _rank(vals: list[float]) -> list[float]:
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def _spearman(xs: list[float], ys: list[float]) -> float:
    return _pearson(_rank(xs), _rank(ys))


def correlation_study() -> None:
    print("\n=== Part 1: Correlation study ===")
    strengths = roster_strength.compute_all([t.abbr for t in TEAMS])
    team_rating = {a: r.team_rating for a, r in strengths.items()}
    roster_score = {a: r.roster_score for a, r in strengths.items()}

    tr_wp, tr_pow, rs_wp = [], [], []
    for i in range(N_CORR_SEEDS):
        seed = CORR_SEED_START + i
        t0 = time.time()
        result = _run_season(seed, f"corr{i}")
        print(f"  seed {seed} ({i + 1}/{N_CORR_SEEDS}) simulated in {time.time() - t0:.1f}s")
        for abbr, (win_pct, power) in result.items():
            tr_wp.append((team_rating[abbr], win_pct))
            tr_pow.append((team_rating[abbr], power))
            rs_wp.append((roster_score[abbr], win_pct))

    def report(label: str, pairs: list[tuple[float, float]]) -> None:
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        print(f"  {label}: n={len(xs)}  pearson r={_pearson(xs, ys):+.3f}  spearman rho={_spearman(xs, ys):+.3f}")

    report("team_rating  vs win_pct     ", tr_wp)
    report("team_rating  vs power_rating", tr_pow)
    report("roster_score vs win_pct     ", rs_wp)


def sensitivity_study() -> dict[str, float]:
    print("\n=== Part 2: Position-group sensitivity ===")
    strengths = roster_strength.compute_all([t.abbr for t in TEAMS])
    median_rating = sorted(r.team_rating for r in strengths.values())[16]
    baseline_abbr = min(strengths, key=lambda a: abs(strengths[a].team_rating - median_rating))
    print(f"  baseline team: {baseline_abbr} (team_rating={strengths[baseline_abbr].team_rating:.1f}, "
          f"league median={median_rating:.1f})")

    shifts: dict[str, list[tuple[float, float]]] = {g: [] for g in SENSITIVITY_GROUPS}
    for group in SENSITIVITY_GROUPS:
        ranked_by_group = sorted(strengths, key=lambda a: -strengths[a].group_ratings.get(group, 0.0))
        donor_abbr = ranked_by_group[0] if ranked_by_group[0] != baseline_abbr else ranked_by_group[1]
        positions = _positions_for_group(group)
        print(f"\n  group {group}: donor={donor_abbr} "
              f"({group} rating {strengths[donor_abbr].group_ratings[group]:.1f} vs "
              f"baseline's {strengths[baseline_abbr].group_ratings[group]:.1f})")

        for seed in SENSITIVITY_SEEDS:
            _use_scratch_db()
            before = _run_season(seed, f"sens_{group}_{seed}_before")[baseline_abbr]

            # A real two-way SWAP, not a one-way theft: moving donor's
            # players out with nothing given back leaves donor with ZERO
            # players at this position, which crashes depth_chart._top()
            # the instant donor's own game gets simulated (every team
            # plays every week) -- caught via a real IndexError on the
            # first live run of this script. Swapping keeps both rosters
            # populated; donor's own record moving too is fine, since
            # only baseline's outcome is measured.
            with db_module.get_session() as s:
                baseline_players = list(s.exec(
                    select(Player).where(Player.team_abbr == baseline_abbr, Player.position.in_(positions))
                ))
                donor_players = list(s.exec(
                    select(Player).where(Player.team_abbr == donor_abbr, Player.position.in_(positions))
                ))
                assert baseline_players, f"baseline {baseline_abbr} has no players at {group} ({positions})"
                assert donor_players, f"donor {donor_abbr} has no players at {group} ({positions})"
                for p in baseline_players:
                    p.team_abbr = donor_abbr
                    s.add(p)
                for p in donor_players:
                    p.team_abbr = baseline_abbr
                    s.add(p)
                s.commit()
            depth_chart.clear_starters_cache()

            after_group_ratings = roster_strength.compute_group_ratings(baseline_abbr)
            after = _run_season(seed, f"sens_{group}_{seed}_after")[baseline_abbr]
            shifts[group].append((after[0] - before[0], after[1] - before[1]))
            print(f"    seed {seed}: {group} rating {strengths[baseline_abbr].group_ratings[group]:.1f} -> "
                  f"{after_group_ratings.get(group, 0.0):.1f}  |  "
                  f"win_pct {before[0]:.3f} -> {after[0]:.3f}  "
                  f"power_rating {before[1]:.1f} -> {after[1]:.1f}")

            _restore_real_db()

    print("\n  --- avg shift from upgrading ONE group to the league's best real unit ---")
    avg_power_shift: dict[str, float] = {}
    for group in SENSITIVITY_GROUPS:
        wp_shift = sum(s[0] for s in shifts[group]) / len(shifts[group])
        pow_shift = sum(s[1] for s in shifts[group]) / len(shifts[group])
        avg_power_shift[group] = pow_shift
        print(f"  {group:>3}: avg win_pct shift {wp_shift:+.3f}   avg power_rating shift {pow_shift:+.1f}   "
              f"(current weight {roster_strength.POSITION_WEIGHTS[group]:.2f})")
    return avg_power_shift


if __name__ == "__main__":
    avg_power_shift: dict[str, float] = {}
    try:
        correlation_study()
        avg_power_shift = sensitivity_study()
    finally:
        _restore_real_db()

    print("\n=== Ordering check: current POSITION_WEIGHTS vs observed sensitivity ===")
    by_shift = sorted(avg_power_shift, key=lambda g: -avg_power_shift[g])
    by_weight = sorted(avg_power_shift, key=lambda g: -roster_strength.POSITION_WEIGHTS[g])
    print(f"  by observed power_rating shift: {by_shift}")
    print(f"  by current POSITION_WEIGHTS:    {by_weight}")

    print("\n=== Caveats ===")
    print("  - 2 seeds/group is enough to catch a badly wrong ORDERING, not to pin")
    print("    exact weight VALUES -- a stochastic sim's per-season win_pct variance")
    print("    is large relative to one team's group-strength swap.")
    print("  - power_rating (Elo) is the steadier signal here; win_pct over one 18-")
    print("    game season is noisier by nature (any real NFL team's record swings a")
    print("    lot year to year even with a stable roster) -- weight the power_rating")
    print("    shift column more than the win_pct one when reading this.")
    print("  - The swap always upgrades TO the league's actual best real unit at that")
    print("    group, so shift size also reflects how far apart the league's best and")
    print("    the baseline team happen to be at that group today, not a fixed-size")
    print("    intervention -- read this as 'does the ordering make sense', not as a")
    print("    precise per-point weight-to-outcome conversion rate.")
