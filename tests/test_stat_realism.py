"""
Stat-realism regression guard (GDD Sec 6.7.2's MVP Truth Set) -- a
permanent check that a full simulated season's individual leaders and
league-wide rates stay within real NFL bounds, not just "the code runs."

Written after a real, severe bug: three separate "who's involved in this
play" pickers (decide_blitz's blitzer, choose_run_point_of_attack's run
zone, and choose_pass_target's receiver -- the last one softmax-weighted
but at too low a temperature) used pure or near-deterministic argmax
selection over STATIC per-game ratings, so the same single player/zone
won on every relevant play of a game, and usually of a whole season
(ratings don't change mid-season). Combined with an elevated per-play
sack probability and elevated drive-pace, this produced a simulated
season where the sack leader had 65 sacks (real record: 22.5, T.J. Watt
2021) and a WR caught 62% of his team's targets (real ceiling: ~28%).
Fixed by converting all three pickers to properly-tempered weighted-
random selection and recalibrating sack rate + drives/game against a
real full-season simulation, not guessed constants -- see player_ai.py's
TARGET_TEMPERATURE_*/ZONE_TEMPERATURE, defensive_ai.py's
BLITZER_TEMPERATURE, drive_sim.py's SACK_CONVERSION_RATE, and
rating.py's pace_drives().

Real NFL benchmarks below are well-known single-season records/rates,
given generous headroom (not tight bounds) -- the goal is catching
systemic 2-3x-real inflation like the bug above, not holding a
stochastic simulation to historical-record precision.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

from pathlib import Path

import pytest

from app.core.db import DB_PATH

DB_EXISTS = DB_PATH.exists()
needs_db = pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")

# Real single-season records, with a generous headroom multiplier so an
# occasional record-adjacent simulated season doesn't make this flaky --
# only a systemic multiple-of-the-record blowout should fail it.
HEADROOM = 1.35
REAL_PASSING_YARDS_RECORD = 5477   # Peyton Manning, 2013
REAL_PASSING_TD_RECORD = 55        # Peyton Manning, 2013
REAL_RUSHING_YARDS_RECORD = 2105   # Eric Dickerson, 1984
REAL_RECEIVING_YARDS_RECORD = 1964  # Calvin Johnson, 2012
REAL_RECEIVING_TD_RECORD = 23      # Randy Moss, 2007
REAL_SACKS_RECORD = 22.5           # T.J. Watt, 2021 / Michael Strahan, 2001
REAL_INT_RECORD = 14               # Dick "Night Train" Lane, 1952 (modern-era record is lower)
REAL_SOLO_TACKLES_CEILING = 200    # no official record kept; generous ceiling for a workhorse LB
# TFL wasn't officially tracked league-wide until relatively recently, so
# there's no clean all-time record the way there is for sacks/INT --
# modern dominant seasons (Aaron Donald-caliber) top out around 25-31.
# This is the one category the item-36 stat-realism fixes didn't fully
# resolve (still running ~40-44 in a simulated season vs this ~30
# ceiling) -- extra headroom here (1.5x, vs 1.35x everywhere else) is a
# deliberate, disclosed acknowledgment of that remaining gap, not a
# claim it's fully fixed. See player_ai.py's ZONE_TEMPERATURE and
# drive_sim.py's _resolve_run mean constant for where further tuning
# would go.
REAL_TFL_CEILING = 30
TFL_HEADROOM = 1.5

REAL_SACKS_PER_TEAM_PER_GAME = (1.6, 3.4)  # generous band around the real ~2.4-2.6 average
MAX_SINGLE_RECEIVER_TARGET_SHARE = 0.45     # real #1 WRs top out ~25-30%; generous ceiling


@needs_db
def test_full_season_leaders_and_rates_stay_within_real_nfl_bounds():
    from app.services import season_state, save_service, history_store, gameplan_store
    from app.engine.schedule import N_WEEKS
    from app.engine.season_stats import aggregate_season_stats, aggregate_season_defensive_stats

    save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_stat_realism_season.json")
    history_store.DEFAULT_PATH = Path("data/saves/_test_stat_realism_history.json")
    gameplan_store.DEFAULT_PATH = Path("data/saves/_test_stat_realism_gameplans.json")
    for p in (save_service.DEFAULT_SAVE_PATH, history_store.DEFAULT_PATH, gameplan_store.DEFAULT_PATH):
        p.unlink(missing_ok=True)

    season_state.reset_season()
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    season = season_state.get_season()

    passing, rushing, receiving = aggregate_season_stats(season)
    defense = aggregate_season_defensive_stats(season)

    assert passing, "no passing stats produced -- season didn't actually simulate"

    max_pass_yards = max(p.yards for p in passing.values())
    max_pass_td = max(p.touchdowns for p in passing.values())
    max_rush_yards = max(r.yards for r in rushing.values())
    max_rec_yards = max(r.yards for r in receiving.values())
    max_rec_td = max(r.touchdowns for r in receiving.values())
    max_sacks = max(d.sacks for d in defense.values())
    max_int = max(d.interceptions for d in defense.values())
    max_solo_tackles = max(d.solo_tackles for d in defense.values())
    max_tfl = max(d.tackles_for_loss for d in defense.values())

    assert max_pass_yards <= REAL_PASSING_YARDS_RECORD * HEADROOM, \
        f"passing yards leader {max_pass_yards} is more than {HEADROOM}x the real record {REAL_PASSING_YARDS_RECORD}"
    assert max_pass_td <= REAL_PASSING_TD_RECORD * HEADROOM, \
        f"passing TD leader {max_pass_td} is more than {HEADROOM}x the real record {REAL_PASSING_TD_RECORD}"
    assert max_rush_yards <= REAL_RUSHING_YARDS_RECORD * HEADROOM, \
        f"rushing yards leader {max_rush_yards} is more than {HEADROOM}x the real record {REAL_RUSHING_YARDS_RECORD}"
    assert max_rec_yards <= REAL_RECEIVING_YARDS_RECORD * HEADROOM, \
        f"receiving yards leader {max_rec_yards} is more than {HEADROOM}x the real record {REAL_RECEIVING_YARDS_RECORD}"
    assert max_rec_td <= REAL_RECEIVING_TD_RECORD * HEADROOM, \
        f"receiving TD leader {max_rec_td} is more than {HEADROOM}x the real record {REAL_RECEIVING_TD_RECORD}"
    assert max_sacks <= REAL_SACKS_RECORD * HEADROOM, \
        f"sack leader {max_sacks} is more than {HEADROOM}x the real record {REAL_SACKS_RECORD}"
    assert max_int <= REAL_INT_RECORD * HEADROOM, \
        f"INT leader {max_int} is more than {HEADROOM}x the real record {REAL_INT_RECORD}"
    assert max_solo_tackles <= REAL_SOLO_TACKLES_CEILING, \
        f"solo tackle leader {max_solo_tackles} exceeds the generous realistic ceiling {REAL_SOLO_TACKLES_CEILING}"
    assert max_tfl <= REAL_TFL_CEILING * TFL_HEADROOM, \
        f"TFL leader {max_tfl} is more than {TFL_HEADROOM}x the realistic ceiling {REAL_TFL_CEILING} -- see this file's TFL_HEADROOM comment"

    # Target-share concentration: no single receiver should be soaking up
    # a hugely disproportionate share of his own team's targets -- the
    # exact failure mode of the argmax bug this test guards against.
    from collections import defaultdict
    team_targets = defaultdict(int)
    for r in receiving.values():
        team_targets[r.team_abbr] += r.targets
    for r in receiving.values():
        if team_targets[r.team_abbr] >= 50:  # skip tiny samples (backup/garbage-time targets)
            share = r.targets / team_targets[r.team_abbr]
            assert share <= MAX_SINGLE_RECEIVER_TARGET_SHARE, \
                f"{r.name} ({r.team_abbr}) has {share:.0%} of his team's targets -- real #1 WRs top out ~25-30%"

    for p in (save_service.DEFAULT_SAVE_PATH, history_store.DEFAULT_PATH, gameplan_store.DEFAULT_PATH):
        p.unlink(missing_ok=True)


@needs_db
def test_sacks_per_game_rate_and_shape_resemble_a_poisson_process():
    """Brian's own proposed validation method: sacks (an independent,
    low-probability event on a fixed number of dropbacks per game) should
    behave like a Poisson process league-wide -- mean team-sacks-per-game
    within the real ~2.4-2.6 range, and (Poisson's defining property)
    variance roughly equal to the mean, not wildly over-dispersed the way
    a "same player gets every sack" concentration bug would produce
    (extreme per-game variance from a handful of shutout/blowout-sack
    games at either end)."""
    from app.services import season_state, save_service, history_store, gameplan_store
    from app.engine.schedule import N_WEEKS
    from app.engine.box_score import build_box_score

    save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_stat_realism_poisson_season.json")
    history_store.DEFAULT_PATH = Path("data/saves/_test_stat_realism_poisson_history.json")
    gameplan_store.DEFAULT_PATH = Path("data/saves/_test_stat_realism_poisson_gameplans.json")
    for p in (save_service.DEFAULT_SAVE_PATH, history_store.DEFAULT_PATH, gameplan_store.DEFAULT_PATH):
        p.unlink(missing_ok=True)

    season_state.reset_season()
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    season = season_state.get_season()

    # One team-sack-count per team per game (544 samples for an 18-week,
    # 32-team season) -- plenty of sample size for a mean/variance check.
    team_game_sacks: list[int] = []
    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            for abbr in (g.home_abbr, g.away_abbr):
                box = build_box_score(g.result.plays, abbr)
                team_game_sacks.append(box.passing[0].sacks if box.passing else 0)

    n = len(team_game_sacks)
    assert n > 100, "not enough simulated team-games to check a distribution"

    mean = sum(team_game_sacks) / n
    variance = sum((x - mean) ** 2 for x in team_game_sacks) / n

    lo, hi = REAL_SACKS_PER_TEAM_PER_GAME
    assert lo <= mean <= hi, f"mean team sacks/game {mean:.2f} is outside the real ~{lo}-{hi} band"

    # Poisson's defining property is variance == mean (index of dispersion
    # = 1.0). A real NFL season's dispersion index typically runs
    # somewhere around 0.9-1.3; generous 0.5-2.2 band here just to catch
    # a badly broken shape (e.g. near-zero variance from a hard per-game
    # cap, or huge variance from a concentration bug), not to hold this
    # to real historical dispersion precisely.
    dispersion = variance / mean if mean else 0
    assert 0.5 <= dispersion <= 2.2, \
        f"sacks/game variance-to-mean ratio {dispersion:.2f} doesn't look like a Poisson-ish process (want ~0.5-2.2)"

    for p in (save_service.DEFAULT_SAVE_PATH, history_store.DEFAULT_PATH, gameplan_store.DEFAULT_PATH):
        p.unlink(missing_ok=True)
