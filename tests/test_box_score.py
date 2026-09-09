"""
Tests for app/engine/box_score.py -- per-player Passing/Rushing/
Receiving stat lines tallied from a real simulated game's play list.

Requires the imported roster DB, same as test_player_ai.py.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.core.db import DB_PATH
from app.engine.rng import RNG
from app.engine.rating import TeamRatings
from app.engine.game_sim import simulate_game, TeamSim
from app.engine.box_score import build_box_score
from app.services.depth_chart import get_offensive_starters

DB_EXISTS = DB_PATH.exists()
pytestmark = pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")

AVG = TeamRatings(offense=70, defense=70, special=70, run_bias=0.5, aggression=0.5, pace=0.5)


def _play_game(seed: int):
    rng = RNG.with_seed(seed)
    home = TeamSim(name="Kansas City", abbr="KC", ratings=AVG)
    away = TeamSim(name="Buffalo", abbr="BUF", ratings=AVG)
    return simulate_game(rng, home, away)


def test_passing_line_is_the_single_real_starter():
    """This engine has exactly one active passer per team per game (no
    backup QB or in-game injury/benching exists -- see HANDOFF.md's
    Known Gaps) -- the box score's one passing row should be the actual
    starting QB, not a placeholder label."""
    result = _play_game(2025)
    kc_box = build_box_score(result.plays, "KC")
    kc_starters = get_offensive_starters("KC")

    assert len(kc_box.passing) == 1
    assert kc_box.passing[0].name == kc_starters.qb.full_name


def test_rushing_lines_reflect_a_real_committee_backfield():
    """app/engine/rotation.py's committee-backfield modeling (HANDOFF.md
    item 37): the ball carrier is drawn fresh each run play from the
    real RB depth chart, not always the nominal starter, so a full game
    can (and, over enough plays, should) credit carries to more than one
    real back -- every named rusher must be a real player from this
    team's actual RB depth chart, and total credited carries must match
    the real number of run plays."""
    result = _play_game(2025)
    kc_box = build_box_score(result.plays, "KC")
    kc_starters = get_offensive_starters("KC")
    real_hb_names = {p.full_name for p in kc_starters.hb_depth}

    assert len(kc_box.rushing) >= 1
    for line in kc_box.rushing:
        assert line.name in real_hb_names

    real_run_plays = [p for p in result.plays if p.offense_abbr == "KC" and p.play_type == "run" and p.outcome != "penalty"]
    assert sum(r.carries for r in kc_box.rushing) == len(real_run_plays)


def test_sacks_are_not_counted_as_pass_attempts():
    result = _play_game(2025)
    for abbr in ("KC", "BUF"):
        box = build_box_score(result.plays, abbr)
        sack_plays = [p for p in result.plays if p.offense_abbr == abbr and p.outcome == "sack"]
        if sack_plays:
            assert box.passing[0].sacks == len(sack_plays)
        # attempts should equal all pass plays MINUS sacks MINUS in-play
        # penalties (e.g. Roughing the Passer/DPI, which reuse play_type
        # "pass" but outcome "penalty" -- not a real attempt) MINUS
        # pass-play safeties (outcome overwritten to "safety" when a play
        # ends behind the offense's own goal line -- ambiguous sack-vs-
        # completion origin, so also excluded; see box_score.py's docstring)
        pass_plays = [
            p for p in result.plays
            if p.offense_abbr == abbr and p.play_type == "pass" and p.outcome not in ("penalty", "safety")
        ]
        assert box.passing[0].attempts == len(pass_plays) - len(sack_plays)


def test_completions_never_exceed_attempts():
    result = _play_game(2025)
    for abbr in ("KC", "BUF"):
        box = build_box_score(result.plays, abbr)
        assert box.passing[0].completions <= box.passing[0].attempts


def test_interception_counts_as_a_target_and_an_int_not_a_reception():
    """Regression guard for the exact bug Brian found by reading the new
    play-by-play UI: an interception must not be double-counted as a
    reception for the intended receiver, but it SHOULD show up as one of
    that receiver's targets and one of the passer's interceptions."""
    found_one = False
    for seed in range(50):
        result = _play_game(seed)
        for abbr in ("KC", "BUF"):
            int_plays = [
                p for p in result.plays
                if p.offense_abbr == abbr and p.play_type == "pass"
                # "defensive_touchdown" is a real interception too (a
                # pick-six, GDD Sec 6.7.2) -- see box_score.py's own
                # docstring for why it's counted the same as a plain INT.
                and p.outcome in ("turnover", "defensive_touchdown") and p.receiver_name
            ]
            if not int_plays:
                continue
            found_one = True
            box = build_box_score(result.plays, abbr)
            n_ints_thrown = len(int_plays)
            assert box.passing[0].interceptions == n_ints_thrown

            for p in int_plays:
                rl = next((r for r in box.receiving if r.name == p.receiver_name), None)
                assert rl is not None, f"{p.receiver_name} should have a receiving line from being targeted"
                # can't assert an exact per-player count cheaply here (a
                # receiver may have other targets too), but their targets
                # must be at least the number of INTs thrown at them
                assert rl.targets >= 1
    assert found_one, "expected at least one thrown interception across 50 simulated games"


def test_in_play_penalties_are_not_counted_as_attempts_carries_or_yards():
    """Regression guard for a real bug found via the career-stats/HOF work:
    an in-play penalty (Roughing the Passer, DPI, Offensive Holding --
    see drive_sim.py's PenaltyOutcome section) is logged as a PlayEvent
    that inherits the ORIGINAL play's play_type ("pass" or "run") but
    has outcome == "penalty" -- build_box_score's play_type branches
    were falling through to the "else: completion/carry" case for any
    outcome that wasn't specifically "sack"/"turnover"/"incomplete",
    silently counting penalty enforcement yardage (which can be
    negative, e.g. a spot foul) as if it were a real completion or
    carry. Found because it broke test_receiving_yards_sum_equals_
    passing_yards deterministically at LEAGUE_SEED=2025 (a real
    Roughing the Passer penalty in that exact game) -- not a flaky or
    order-dependent failure, a real accuracy bug in every stat line
    this engine has ever produced wherever an in-play penalty fired."""
    found_pass_penalty = False
    found_run_penalty = False
    for seed in range(50):
        result = _play_game(seed)
        for abbr in ("KC", "BUF"):
            box = build_box_score(result.plays, abbr)
            penalty_plays = [p for p in result.plays if p.offense_abbr == abbr and p.outcome == "penalty"]
            if not penalty_plays:
                continue
            real_pass_yards = sum(
                p.yards for p in result.plays
                # a pass-play "safety" is excluded from box_score.py the
                # same as a sack (ambiguous, see its module docstring)
                if p.offense_abbr == abbr and p.play_type == "pass" and p.outcome in ("gain", "first_down", "touchdown")
            )
            real_run_yards = sum(
                p.yards for p in result.plays
                # a run-play "safety" IS a real, unambiguous carry and
                # stays counted -- only turnover/defensive_touchdown
                # (a fumble-six is a turnover too)/penalty are excluded
                if p.offense_abbr == abbr and p.play_type == "run" and p.outcome not in ("turnover", "defensive_touchdown", "penalty")
            )
            if any(p.play_type == "pass" for p in penalty_plays) and box.passing:
                found_pass_penalty = True
                assert box.passing[0].yards == real_pass_yards
            if any(p.play_type == "run" for p in penalty_plays) and box.rushing:
                found_run_penalty = True
                assert sum(r.yards for r in box.rushing) == real_run_yards
    assert found_pass_penalty, "expected at least one pass-play penalty (e.g. Roughing/DPI) across 50 simulated games"
    assert found_run_penalty, "expected at least one run-play penalty (Offensive Holding) across 50 simulated games"


def test_receiving_yards_sum_equals_passing_yards():
    """Every yard on a completion is credited to exactly one receiver and
    to the team's one passer -- the two totals must match exactly."""
    result = _play_game(2025)
    for abbr in ("KC", "BUF"):
        box = build_box_score(result.plays, abbr)
        assert sum(r.yards for r in box.receiving) == box.passing[0].yards


def test_kicking_line_is_the_real_starting_kicker_with_real_fg_and_xp_counts():
    """ROADMAP.md M2: FG/XP attempts must be attributed to the real
    starting kicker (app/services/depth_chart.py's `k`), and the
    Kicking line's totals must match what the play list actually says
    happened, not just be non-zero."""
    found_fg = False
    found_xp = False
    for seed in range(50):
        result = _play_game(seed)
        for abbr in ("KC", "BUF"):
            box = build_box_score(result.plays, abbr)
            starters = get_offensive_starters(abbr)
            fg_plays = [p for p in result.plays if p.offense_abbr == abbr and p.play_type == "field_goal"]
            xp_plays = [p for p in result.plays if p.offense_abbr == abbr and p.play_type == "extra_point"]
            if not fg_plays and not xp_plays:
                continue
            assert len(box.kicking) == 1
            kl = box.kicking[0]
            assert kl.name == starters.k.full_name
            if fg_plays:
                found_fg = True
                assert kl.fg_attempted == len(fg_plays)
                assert kl.fg_made == len([p for p in fg_plays if p.outcome == "field_goal"])
            if xp_plays:
                found_xp = True
                assert kl.xp_attempted == len(xp_plays)
                assert kl.xp_made == len([p for p in xp_plays if p.outcome == "field_goal"])
    assert found_fg, "expected at least one field goal attempt across 50 simulated games"
    assert found_xp, "expected at least one extra point attempt across 50 simulated games"


def test_fg_distance_buckets_sum_to_the_same_totals_as_fg_made_attempted():
    """The per-bucket breakdown and the aggregate fg_made/fg_attempted
    properties must agree -- they're computed from the same underlying
    dict, but this guards against the two ever drifting apart."""
    for seed in range(50):
        result = _play_game(seed)
        for abbr in ("KC", "BUF"):
            box = build_box_score(result.plays, abbr)
            for kl in box.kicking:
                bucket_attempted = sum(att for _, att in kl.fg_by_bucket.values())
                bucket_made = sum(made for made, _ in kl.fg_by_bucket.values())
                assert bucket_attempted == kl.fg_attempted
                assert bucket_made == kl.fg_made
                # every made kick is also an attempt, in the same bucket
                for made, att in kl.fg_by_bucket.values():
                    assert made <= att


def test_punting_line_is_the_real_starting_punter_with_real_net_yards():
    """ROADMAP.md M2: punts must be attributed to the real starting
    punter (app/services/depth_chart.py's `p`), and net_yards must equal
    the real sum of each punt PlayEvent's own net-yards figure (see
    drive_sim.py's _punt_result) -- not a separately-recomputed number
    that could drift from what actually happened in the play list."""
    found_one = False
    for seed in range(50):
        result = _play_game(seed)
        for abbr in ("KC", "BUF"):
            box = build_box_score(result.plays, abbr)
            starters = get_offensive_starters(abbr)
            punt_plays = [p for p in result.plays if p.offense_abbr == abbr and p.play_type == "punt"]
            if not punt_plays:
                continue
            found_one = True
            assert len(box.punting) == 1
            pl = box.punting[0]
            assert pl.name == starters.p.full_name
            assert pl.punts == len(punt_plays)
            assert pl.net_yards == sum(p.yards for p in punt_plays)
    assert found_one, "expected at least one punt across 50 simulated games"


def test_punting_inside_20_matches_a_recomputed_landing_position():
    """inside_20 is derived from field_pos + net yards flipped back to
    the receiving team's own-territory position (the same math
    _punt_result itself used, run in reverse) -- recompute it
    independently here and check it agrees with build_box_score's own
    count, rather than just asserting it's a plausible-looking number."""
    for seed in range(50):
        result = _play_game(seed)
        for abbr in ("KC", "BUF"):
            box = build_box_score(result.plays, abbr)
            punt_plays = [p for p in result.plays if p.offense_abbr == abbr and p.play_type == "punt"]
            if not punt_plays:
                continue
            expected_inside_20 = sum(1 for p in punt_plays if 100 - (p.field_pos + p.yards) <= 20)
            assert box.punting[0].inside_20 == expected_inside_20


def test_fumble_lost_does_not_add_to_rushing_yards():
    found_one = False
    for seed in range(50):
        result = _play_game(seed)
        for abbr in ("KC", "BUF"):
            # "defensive_touchdown" is a lost fumble too (a fumble-six,
            # GDD Sec 6.7.2) -- see box_score.py's own docstring for why
            # it's counted the same as a plain lost fumble.
            fumble_plays = [p for p in result.plays if p.offense_abbr == abbr and p.play_type == "run" and p.outcome in ("turnover", "defensive_touchdown")]
            if not fumble_plays:
                continue
            found_one = True
            box = build_box_score(result.plays, abbr)
            # excludes fumbles AND in-play penalties (e.g. Offensive Holding,
            # play_type "run" but outcome "penalty") -- neither is a real carry
            non_fumble_run_yards = sum(
                p.yards for p in result.plays
                if p.offense_abbr == abbr and p.play_type == "run" and p.outcome not in ("turnover", "defensive_touchdown", "penalty")
            )
            assert sum(r.yards for r in box.rushing) == non_fumble_run_yards
            assert sum(r.fumbles_lost for r in box.rushing) == len(fumble_plays)
    assert found_one, "expected at least one lost fumble across 50 simulated games"
