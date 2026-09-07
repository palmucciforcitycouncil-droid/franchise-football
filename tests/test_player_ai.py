"""
Tests for the player-level play-calling AI (app/engine/player_ai.py,
app/services/depth_chart.py) -- the real formulas that replaced the
team-level stand-ins, per GDD Part 1 Sec 6.6.

Requires the imported roster DB (data/franchise_football.db); skips if
it hasn't been built yet via scripts/import_players.py, same as
test_player_model.py's DB-dependent tests.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.core.db import DB_PATH
from app.data.teams import TEAMS

DB_EXISTS = DB_PATH.exists()
pytestmark = pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")


def test_starters_selected_for_every_team():
    """Every team must produce a complete starting lineup with no crash --
    catches a team missing a required position outright (e.g. a roster
    with zero kickers would raise IndexError in _top())."""
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.models.player import Position

    for t in TEAMS:
        off = get_offensive_starters(t.abbr)
        defn = get_defensive_starters(t.abbr)
        assert off.qb.team_abbr == t.abbr
        assert len(off.offensive_line) == 5
        assert len(defn.defensive_line) == 4
        assert len(defn.secondary) == 4
        assert off.k.team_abbr == t.abbr
        assert off.k.position == Position.K


def test_starters_are_the_actual_highest_rated_at_each_position():
    from app.core.db import get_session
    from app.models.player import Player, Position
    from app.services.depth_chart import get_offensive_starters
    from sqlmodel import select

    with get_session() as s:
        qbs = list(s.exec(select(Player).where(Player.team_abbr == "KC").where(Player.position == Position.QB)))
    best_qb = max(qbs, key=lambda p: p.overall_rating)

    off = get_offensive_starters("KC")
    assert off.qb.player_id == best_qb.player_id


def test_matchup_context_composites_are_real_averages():
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context

    off = get_offensive_starters("KC")
    defn = get_defensive_starters("BUF")
    ctx = build_matchup_context(off, defn)

    expected_ol_run_block = sum(p.run_block for p in off.offensive_line) / 5
    assert ctx.ol_run_block == expected_ol_run_block
    assert 0 <= ctx.ol_run_block <= 99
    assert 0 <= ctx.dl_run_stop <= 99
    assert 0 <= ctx.ol_pass_block <= 99
    assert 0 <= ctx.dl_pass_rush <= 99


def test_run_point_of_attack_matches_best_blocking_zone_most_of_the_time():
    """The RB-trait override (agility/strength nudging the choice) means
    this won't be 100% of the time, but the blocking-advantage zone should
    win clearly more often than chance (1/3) across many calls."""
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context, choose_run_point_of_attack
    from app.engine.rng import RNG

    off = get_offensive_starters("KC")
    defn = get_defensive_starters("BUF")
    ctx = build_matchup_context(off, defn)
    best_zone = max(("left", ctx.zones.left), ("center", ctx.zones.center), ("right", ctx.zones.right), key=lambda t: t[1])[0]

    rng = RNG.with_seed(1)
    matches = sum(1 for _ in range(200) if choose_run_point_of_attack(ctx, off.hb, rng).point_of_attack == best_zone)
    assert matches / 200 > 0.4


def test_pass_target_favors_the_biggest_real_mismatch_but_varies():
    """Weighted-random selection (softmax over mismatch scores): the best
    real mismatch should win more often than any other receiver, but not
    every single time -- unlike the old pure-argmax version, which sent
    100% of a game's targets to one receiver (a real bug found via the
    box score, see player_ai.choose_pass_target's docstring)."""
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context, choose_pass_target, route_running_avg, coverage_rating
    from app.engine.rng import RNG

    off = get_offensive_starters("KC")
    defn = get_defensive_starters("BUF")
    ctx = build_matchup_context(off, defn)

    candidates = [
        (off.wr1, defn.cb1), (off.wr2, defn.cb2), (off.te, defn.ss),
    ]
    if off.wr3 is not None:
        candidates.append((off.wr3, defn.fs))
    expected_best = max(candidates, key=lambda pair: route_running_avg(pair[0]) - coverage_rating(pair[1]))

    rng = RNG.with_seed(1)
    targets = [choose_pass_target(ctx, rng, distance=8) for _ in range(200)]
    best_share = sum(1 for t in targets if t.receiver.player_id == expected_best[0].player_id) / 200

    assert best_share > 1 / len(candidates)
    assert best_share < 1.0
    assert len({t.receiver.player_id for t in targets}) > 1


def test_different_matchups_produce_different_advantages():
    """A sanity check that the engine actually differentiates teams --
    KC's offensive line vs. two different defenses shouldn't produce
    identical matchup numbers (would indicate starters or DB lookups
    aren't actually varying by opponent)."""
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context, matchup_adjustment

    off = get_offensive_starters("KC")
    ctx_vs_buf = build_matchup_context(off, get_defensive_starters("BUF"))
    ctx_vs_sf = build_matchup_context(off, get_defensive_starters("SF"))

    assert matchup_adjustment(ctx_vs_buf) != matchup_adjustment(ctx_vs_sf)
