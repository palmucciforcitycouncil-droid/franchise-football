"""
Tests for the defensive play-calling AI (app/engine/defensive_ai.py),
GDD Part 1 Sec 6.6.3 -- the four-step anticipate/blitz/coverage/
run-tactic decision process, and its real effect on drive_sim.py's
play resolution (not just narration).

Requires the imported roster DB, same as test_player_ai.py.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.core.db import DB_PATH

DB_EXISTS = DB_PATH.exists()
pytestmark = pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")


def test_anticipated_pass_prob_follows_situational_baseline():
    from app.engine.defensive_ai import anticipated_pass_prob, LEAGUE_AVG_YPC, LEAGUE_AVG_YPA

    third_and_long = anticipated_pass_prob(3, 10, trailing=False, is_two_minute=False, off_ypc=LEAGUE_AVG_YPC, off_ypa=LEAGUE_AVG_YPA)
    third_and_short = anticipated_pass_prob(3, 1, trailing=False, is_two_minute=False, off_ypc=LEAGUE_AVG_YPC, off_ypa=LEAGUE_AVG_YPA)
    assert third_and_long > third_and_short


def test_anticipated_pass_prob_reacts_to_in_game_performance():
    """An offense that's gaining a lot per pass attempt relative to per
    carry should read as more pass-likely than a league-average offense
    in the exact same down/distance/situation."""
    from app.engine.defensive_ai import anticipated_pass_prob, LEAGUE_AVG_YPC

    baseline = anticipated_pass_prob(1, 10, trailing=False, is_two_minute=False, off_ypc=LEAGUE_AVG_YPC, off_ypa=7.0)
    pass_heavy = anticipated_pass_prob(1, 10, trailing=False, is_two_minute=False, off_ypc=LEAGUE_AVG_YPC, off_ypa=12.0)
    assert pass_heavy > baseline


def test_choose_primary_thresholds():
    from app.engine.defensive_ai import choose_primary

    assert choose_primary(0.70) == "pass_defense"
    assert choose_primary(0.30) == "run_defense"
    assert choose_primary(0.50) == "standard"


def test_decide_run_tactic_matches_the_offenses_own_best_zone():
    """The defense predicts direction using the SAME zone math the
    offense's play-caller uses (Sec 6.6.3 Step 4) -- center wins should
    map to Plug Gaps, an edge win to Contain Edge."""
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context
    from app.engine.defensive_ai import decide_run_tactic

    ctx = build_matchup_context(get_offensive_starters("KC"), get_defensive_starters("BUF"))
    z = ctx.zones
    best_zone = max(("left", z.left), ("center", z.center), ("right", z.right), key=lambda t: t[1])[0]
    tactic = decide_run_tactic(ctx)
    assert tactic == ("plug_gaps" if best_zone == "center" else "contain_edge")


def test_apply_run_tactic_penalizes_the_targeted_zone_only():
    from app.engine.player_ai import ZoneAdvantage
    from app.engine.defensive_ai import apply_run_tactic

    zones = ZoneAdvantage(left=5.0, center=5.0, right=5.0)

    plugged = apply_run_tactic(zones, "plug_gaps")
    assert plugged.center < zones.center
    assert plugged.left == zones.left and plugged.right == zones.right

    contained = apply_run_tactic(zones, "contain_edge")
    assert contained.left < zones.left and contained.right < zones.right
    assert contained.center == zones.center

    assert apply_run_tactic(zones, None) == zones


def test_decide_blitz_targets_the_weaker_pass_blocking_rb_or_te():
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.defensive_ai import decide_blitz
    from app.engine.rng import RNG

    off = get_offensive_starters("KC")
    defn = get_defensive_starters("BUF")
    expected_target = off.hb if off.hb.pass_block <= off.te.pass_block else off.te

    rng = RNG.with_seed(3)
    # Force the blitz to fire regardless of the probabilistic gate by
    # calling with a red-zone + 3rd & long situation (chance capped at 0.9).
    called = [decide_blitz(defn, off, down=3, distance=8, field_pos=85, rng=rng) for _ in range(60)]
    fired = [c for c in called if c.called]
    assert fired, "expected at least one blitz to fire across 60 high-probability calls"
    for c in fired:
        assert c.target.player_id == expected_target.player_id
        assert c.blitzer in [defn.lolb, defn.mlb, defn.rolb, defn.fs, defn.ss]


def test_decide_coverage_rules():
    from app.engine.defensive_ai import decide_coverage
    from app.engine.rng import RNG

    rng = RNG.with_seed(1)
    assert decide_coverage(down=3, distance=9, field_pos=50, blitz_called=False, rng=rng) == "zone"
    assert decide_coverage(down=1, distance=10, field_pos=92, blitz_called=False, rng=rng) == "man"
    assert decide_coverage(down=2, distance=6, field_pos=50, blitz_called=True, rng=rng) == "man"


def test_decide_defensive_call_is_a_full_package():
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context
    from app.engine.defensive_ai import decide_defensive_call, LEAGUE_AVG_YPC, LEAGUE_AVG_YPA
    from app.engine.rng import RNG

    ctx = build_matchup_context(get_offensive_starters("KC"), get_defensive_starters("BUF"))
    rng = RNG.with_seed(5)
    call = decide_defensive_call(ctx, down=3, distance=2, field_pos=50, trailing=False, is_two_minute=False,
                                  off_ypc=LEAGUE_AVG_YPC, off_ypa=LEAGUE_AVG_YPA, rng=rng)
    assert call.primary in ("pass_defense", "run_defense", "standard")
    assert call.coverage in ("man", "zone")
    if call.primary != "run_defense":
        assert call.run_tactic is None
    assert isinstance(call.description, str) and len(call.description) > 0


def test_blitz_increases_sack_rate_in_the_drive_sim():
    """Integration check: a blitz called every play should produce
    meaningfully more sacks than a coin-flip blitz rate, using the real
    pass-resolution path in drive_sim.py -- not just the defensive_ai
    unit in isolation."""
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.player_ai import build_matchup_context
    from app.engine.defensive_ai import DefensiveCall, BlitzCall
    from app.engine.drive_sim import _resolve_pass
    from app.engine.rng import RNG

    off = get_offensive_starters("KC")
    ctx = build_matchup_context(off, get_defensive_starters("BUF"))
    qb = off.qb

    no_blitz = DefensiveCall(primary="standard", blitz=BlitzCall(called=False), coverage="zone", run_tactic=None)
    blitzer = get_defensive_starters("BUF").mlb
    heavy_blitz = DefensiveCall(
        primary="standard",
        blitz=BlitzCall(called=True, blitzer=blitzer, target=off.te, advantage=20.0),
        coverage="man", run_tactic=None,
    )

    rng_a = RNG.with_seed(42)
    sacks_no_blitz = sum(1 for _ in range(300) if _resolve_pass(rng_a, ctx, qb, no_blitz)[1] == "sack")
    rng_b = RNG.with_seed(42)
    sacks_blitz = sum(1 for _ in range(300) if _resolve_pass(rng_b, ctx, qb, heavy_blitz)[1] == "sack")

    assert sacks_blitz > sacks_no_blitz


def test_decide_blitz_responds_to_weekly_gameplan():
    """GDD Sec 10.4.1: Blitz Heavy + Very Aggressive should call blitz
    noticeably more often than Selective + Very Conservative, in an
    otherwise identical (and low-baseline) situation -- 1st & 10 at
    midfield, where the unmodified base chance is just 15%."""
    from app.services.depth_chart import get_offensive_starters, get_defensive_starters
    from app.engine.defensive_ai import decide_blitz
    from app.engine.gameplan import Gameplan
    from app.engine.rng import RNG

    off = get_offensive_starters("KC")
    defn = get_defensive_starters("BUF")

    passive_gp = Gameplan(defensive_aggressiveness="Very Conservative", blitz="Selective")
    aggressive_gp = Gameplan(defensive_aggressiveness="Very Aggressive", blitz="Blitz Heavy")

    rng_a = RNG.with_seed(7)
    passive_blitzes = sum(
        1 for _ in range(400)
        if decide_blitz(defn, off, down=1, distance=10, field_pos=50, rng=rng_a, gameplan=passive_gp).called
    )
    rng_b = RNG.with_seed(7)
    aggressive_blitzes = sum(
        1 for _ in range(400)
        if decide_blitz(defn, off, down=1, distance=10, field_pos=50, rng=rng_b, gameplan=aggressive_gp).called
    )
    rng_c = RNG.with_seed(7)
    default_blitzes = sum(
        1 for _ in range(400)
        if decide_blitz(defn, off, down=1, distance=10, field_pos=50, rng=rng_c, gameplan=None).called
    )

    assert passive_blitzes < default_blitzes < aggressive_blitzes


def test_decide_coverage_responds_to_weekly_gameplan():
    """GDD Sec 10.4.1: Man-Heavy should call man coverage noticeably more
    than Zone-Heavy in the same neutral (not situationally-forced)
    down/distance/field-position."""
    from app.engine.defensive_ai import decide_coverage
    from app.engine.gameplan import Gameplan
    from app.engine.rng import RNG

    man_heavy = Gameplan(coverage="Man-Heavy")
    zone_heavy = Gameplan(coverage="Zone-Heavy")

    rng_a = RNG.with_seed(11)
    man_calls_man_heavy = sum(
        1 for _ in range(400)
        if decide_coverage(down=1, distance=10, field_pos=50, blitz_called=False, rng=rng_a, gameplan=man_heavy) == "man"
    )
    rng_b = RNG.with_seed(11)
    man_calls_zone_heavy = sum(
        1 for _ in range(400)
        if decide_coverage(down=1, distance=10, field_pos=50, blitz_called=False, rng=rng_b, gameplan=zone_heavy) == "man"
    )

    assert man_calls_man_heavy > man_calls_zone_heavy


def test_decide_coverage_situational_overrides_still_win_over_gameplan():
    """3rd & 8+ always calls zone and a called blitz always calls man,
    regardless of Coverage Scheme -- the gameplan only replaces the
    default 60/40 mix in the 'otherwise' branch, per decide_coverage's
    own docstring."""
    from app.engine.defensive_ai import decide_coverage
    from app.engine.gameplan import Gameplan
    from app.engine.rng import RNG

    rng = RNG.with_seed(1)
    assert decide_coverage(down=3, distance=9, field_pos=50, blitz_called=False, rng=rng,
                            gameplan=Gameplan(coverage="Man-Heavy")) == "zone"
    assert decide_coverage(down=1, distance=10, field_pos=50, blitz_called=True, rng=rng,
                            gameplan=Gameplan(coverage="Zone-Heavy")) == "man"


def test_apply_run_tactic_extra_penalty_from_run_sellout_gameplan():
    from app.engine.defensive_ai import apply_run_tactic
    from app.engine.player_ai import ZoneAdvantage

    zones = ZoneAdvantage(left=5.0, center=5.0, right=5.0)
    base = apply_run_tactic(zones, "plug_gaps")
    with_sellout = apply_run_tactic(zones, "plug_gaps", extra_penalty=4.0)
    assert with_sellout.center < base.center
    assert with_sellout.left == base.left == zones.left  # only the targeted zone is penalized
