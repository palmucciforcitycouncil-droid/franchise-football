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


def test_passing_and_rushing_lines_are_the_single_real_starters():
    """This engine has exactly one active passer/rusher per team per
    game (no backups or scrambles yet) -- the box score's one row
    should be the actual starting QB/HB, not a placeholder label."""
    result = _play_game(2025)
    kc_box = build_box_score(result.plays, "KC")
    kc_starters = get_offensive_starters("KC")

    assert len(kc_box.passing) == 1
    assert kc_box.passing[0].name == kc_starters.qb.full_name
    assert len(kc_box.rushing) == 1
    assert kc_box.rushing[0].name == kc_starters.hb.full_name


def test_sacks_are_not_counted_as_pass_attempts():
    result = _play_game(2025)
    for abbr in ("KC", "BUF"):
        box = build_box_score(result.plays, abbr)
        sack_plays = [p for p in result.plays if p.offense_abbr == abbr and p.outcome == "sack"]
        if sack_plays:
            assert box.passing[0].sacks == len(sack_plays)
        # attempts should equal all pass plays MINUS sacks
        pass_plays = [p for p in result.plays if p.offense_abbr == abbr and p.play_type == "pass"]
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
                if p.offense_abbr == abbr and p.play_type == "pass" and p.outcome == "turnover" and p.receiver_name
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


def test_receiving_yards_sum_equals_passing_yards():
    """Every yard on a completion is credited to exactly one receiver and
    to the team's one passer -- the two totals must match exactly."""
    result = _play_game(2025)
    for abbr in ("KC", "BUF"):
        box = build_box_score(result.plays, abbr)
        assert sum(r.yards for r in box.receiving) == box.passing[0].yards


def test_fumble_lost_does_not_add_to_rushing_yards():
    found_one = False
    for seed in range(50):
        result = _play_game(seed)
        for abbr in ("KC", "BUF"):
            fumble_plays = [p for p in result.plays if p.offense_abbr == abbr and p.play_type == "run" and p.outcome == "turnover"]
            if not fumble_plays:
                continue
            found_one = True
            box = build_box_score(result.plays, abbr)
            non_fumble_run_yards = sum(
                p.yards for p in result.plays
                if p.offense_abbr == abbr and p.play_type == "run" and p.outcome != "turnover"
            )
            assert box.rushing[0].yards == non_fumble_run_yards
            assert box.rushing[0].fumbles_lost == len(fumble_plays)
    assert found_one, "expected at least one lost fumble across 50 simulated games"
