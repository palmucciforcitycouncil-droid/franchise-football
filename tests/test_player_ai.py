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


def test_starters_are_the_actual_highest_rated_at_each_position(monkeypatch, tmp_path):
    """Isolated from the real data/saves/depth_chart_overrides.json --
    that file holds a real user-settable override (see
    test_depth_chart_overrides.py), so without redirecting it here a
    manual depth-chart edit made anywhere else (e.g. live UI testing)
    would make this test fail even though nothing is actually broken."""
    from app.core.db import get_session
    from app.models.player import Player, Position
    from app.services import depth_chart_overrides as dco
    from app.services.depth_chart import get_offensive_starters, clear_starters_cache
    from sqlmodel import select

    monkeypatch.setattr(dco, "DEFAULT_PATH", tmp_path / "overrides.json")
    clear_starters_cache()

    with get_session() as s:
        qbs = list(s.exec(select(Player).where(Player.team_abbr == "KC").where(Player.position == Position.QB)))
    best_qb = max(qbs, key=lambda p: p.overall_rating)

    try:
        off = get_offensive_starters("KC")
        assert off.qb.player_id == best_qb.player_id
    finally:
        clear_starters_cache()


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


def _synthetic_player(**overrides):
    """A hand-built Player with every attribute pinned to a fixed
    baseline (75), for tests that need a CONTROLLED matchup rather than
    whatever the live roster DB's ratings currently happen to be. The
    live DB is mutable in this project (Player Progression, item 26,
    permanently ages/develops it every real "Start Next Season") -- a
    test that computes its own expectation from live ratings can start
    failing months later for reasons that have nothing to do with the
    code under test, simply because some other session's live
    verification aged a specific real player's rating far enough to
    change which matchup is "the biggest mismatch" (confirmed: this is
    exactly what happened here, not a regression -- see git history)."""
    from app.models.player import Player, Position

    defaults = dict(
        player_id="synthetic", first_name="Synthetic", last_name="Player",
        position=Position.WR, team_abbr="KC", age=25,
        overall_rating=75, potential=80, morale=75,
        speed=75, acceleration=75, strength=75, agility=75, jumping=75,
        stamina=75, toughness=75, durability=75,
        throw_power=75, throw_accuracy_short=75, throw_accuracy_mid=75, throw_accuracy_deep=75,
        play_action=75, throw_on_the_run=75, throw_under_pressure=75, break_sack=75,
        catching=75, spectacular_catch=75, catch_in_traffic=75,
        short_route_running=75, medium_route_running=75, deep_route_running=75, release=75,
        carrying=75, trucking=75, change_of_direction=75, ball_carrier_vision=75,
        stiff_arm=75, spin_move=75, juke_move=75, break_tackle=75,
        run_block=75, pass_block=75, run_block_power=75, run_block_finesse=75,
        pass_block_power=75, pass_block_finesse=75, lead_block=75, impact_blocking=75,
        tackle=75, hit_power=75, block_shedding=75, pursuit=75, play_recognition=75,
        man_coverage=75, zone_coverage=75, press=75, power_moves=75, finesse_moves=75,
        kick_power=75, kick_accuracy=75, kick_return=75, awareness=75,
    )
    defaults.update(overrides)
    return Player(**defaults)


def test_pass_target_favors_the_biggest_real_mismatch_but_varies():
    """Weighted-random selection (softmax over mismatch scores): the best
    mismatch should win more often than any other receiver, but not
    every single time -- unlike the old pure-argmax version, which sent
    100% of a game's targets to one receiver (a real bug found via the
    box score, see player_ai.choose_pass_target's docstring). Uses
    synthetic players with a CONTROLLED, moderate mismatch gap (not the
    live roster DB -- see _synthetic_player's docstring for why)."""
    from app.services.depth_chart import OffensiveStarters, DefensiveStarters
    from app.engine.player_ai import build_matchup_context, choose_pass_target, route_running_avg, coverage_rating
    from app.engine.rng import RNG

    wr1 = _synthetic_player(player_id="wr1", short_route_running=88, medium_route_running=88, deep_route_running=88)  # the clear best mismatch
    wr2 = _synthetic_player(player_id="wr2")
    te = _synthetic_player(player_id="te")
    cb1 = _synthetic_player(player_id="cb1", position="CB", man_coverage=68, zone_coverage=68)  # a real but moderate mismatch, not an extreme one
    cb2 = _synthetic_player(player_id="cb2", position="CB")
    ss = _synthetic_player(player_id="ss", position="SS")

    off = OffensiveStarters(
        qb=_synthetic_player(player_id="qb", position="QB"), hb=_synthetic_player(player_id="hb", position="HB"),
        wr1=wr1, wr2=wr2, wr3=None, te=te,
        lt=_synthetic_player(player_id="lt", position="LT"), lg=_synthetic_player(player_id="lg", position="LG"),
        c=_synthetic_player(player_id="c", position="C"), rg=_synthetic_player(player_id="rg", position="RG"),
        rt=_synthetic_player(player_id="rt", position="RT"), k=_synthetic_player(player_id="k", position="K"),
    )
    defn = DefensiveStarters(
        dt1=_synthetic_player(player_id="dt1", position="DT"), dt2=_synthetic_player(player_id="dt2", position="DT"),
        le=_synthetic_player(player_id="le", position="LE"), re=_synthetic_player(player_id="re", position="RE"),
        lolb=_synthetic_player(player_id="lolb", position="LOLB"), mlb=_synthetic_player(player_id="mlb", position="MLB"),
        rolb=_synthetic_player(player_id="rolb", position="ROLB"),
        cb1=cb1, cb2=cb2, fs=_synthetic_player(player_id="fs", position="FS"), ss=ss,
    )
    ctx = build_matchup_context(off, defn)

    candidates = [(wr1, cb1), (wr2, cb2), (te, ss)]
    expected_best = max(candidates, key=lambda pair: route_running_avg(pair[0]) - coverage_rating(pair[1]))
    assert expected_best[0] is wr1  # sanity-check the synthetic setup actually produces the intended mismatch

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
