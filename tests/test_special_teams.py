"""
Tests for app/engine/special_teams.py -- kickoffs (existing, previously
only exercised indirectly via full-game sims in test_drive_sim.py/
test_box_score.py) and R2b's real punt-return yardage + tackle
attribution (new).
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.core.db import DB_PATH
from app.engine.rng import RNG
from app.engine import special_teams
from app.services.depth_chart import get_offensive_starters, get_defensive_starters

DB_EXISTS = DB_PATH.exists()
pytestmark = pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")

KC = get_offensive_starters("KC")
BUF = get_offensive_starters("BUF")


# --- Kickoffs (existing behavior, now also carrying a real tackler) --------

def test_kickoff_result_is_deterministic():
    r1 = special_teams.kickoff_result(RNG.with_seed(42), KC, BUF)
    r2 = special_teams.kickoff_result(RNG.with_seed(42), KC, BUF)
    assert r1 == r2


def test_kickoff_touchback_has_no_returner_or_tackler():
    for seed in range(200):
        r = special_teams.kickoff_result(RNG.with_seed(seed), KC, BUF)
        if r.kind == "touchback":
            assert r.returner_name == ""
            assert r.tackler_name == ""
            return
    pytest.fail("no touchback in 200 seeds -- KICKOFF_TOUCHBACK_PROB may be broken")


def test_kickoff_return_credits_a_real_tackler_from_the_kicking_teams_wr_depth():
    kicking_wrs = {p.full_name for p in KC.wr_depth} | ({KC.wr1.full_name} if KC.wr1 else set())
    for seed in range(200):
        r = special_teams.kickoff_result(RNG.with_seed(seed), BUF, KC)
        if r.kind == "return":
            assert r.tackler_name in kicking_wrs, f"tackler {r.tackler_name!r} not in KC's WR pool"
            return
    pytest.fail("no plain return in 200 seeds")


def test_kickoff_return_td_has_no_tackler():
    for seed in range(2000):
        r = special_teams.kickoff_result(RNG.with_seed(seed), BUF, KC)
        if r.kind == "return_td":
            assert r.tackler_name == ""
            return
    pytest.fail("no return_td in 2000 seeds -- RETURN_TD probabilities may be broken")


# --- R2b: punt returns -------------------------------------------------------

def test_punt_return_result_is_deterministic():
    r1 = special_teams.punt_return_result(RNG.with_seed(7), BUF, KC, return_distance=70)
    r2 = special_teams.punt_return_result(RNG.with_seed(7), BUF, KC, return_distance=70)
    assert r1 == r2


def test_punt_return_no_return_case_has_no_returner_or_yards():
    for seed in range(200):
        r = special_teams.punt_return_result(RNG.with_seed(seed), BUF, KC, return_distance=70)
        if r.kind == "no_return":
            assert r.return_yards == 0
            assert r.returner_name == ""
            assert r.tackler_name == ""
            return
    pytest.fail("no 'no_return' outcome in 200 seeds -- PUNT_RETURN_PROB may be broken")


def test_punt_return_credits_a_real_returner_and_tackler():
    receiving_pool = {p.full_name for p in BUF.wr_depth + BUF.hb_depth}
    punting_pool = {p.full_name for p in KC.wr_depth} | ({KC.wr1.full_name} if KC.wr1 else set())
    for seed in range(300):
        r = special_teams.punt_return_result(RNG.with_seed(seed), BUF, KC, return_distance=70)
        if r.kind == "return":
            assert r.returner_name in receiving_pool
            assert r.tackler_name in punting_pool
            return
    pytest.fail("no plain 'return' outcome in 300 seeds")


def test_punt_return_distribution_is_realistically_weighted_toward_short_gains():
    """Real NFL punt returns cluster heavily in the 0-15 yard band --
    across many real returns, the large majority should land there, with
    only a small tail of longer ones."""
    returns = []
    for seed in range(500):
        r = special_teams.punt_return_result(RNG.with_seed(seed), BUF, KC, return_distance=70)
        if r.kind in ("return", "return_td"):
            returns.append(r.return_yards)
    assert len(returns) > 50, "expected a meaningful sample of real returns across 500 seeds"
    short = sum(1 for y in returns if y <= 15)
    assert short / len(returns) >= 0.7, f"only {short}/{len(returns)} returns were <=15 yards -- distribution too hot"
    assert max(returns) <= 100  # theoretical ceiling, never fabricated beyond a real football field


def test_punt_return_touchdowns_are_rare_but_possible():
    kinds = [special_teams.punt_return_result(RNG.with_seed(seed), BUF, KC, return_distance=70).kind
             for seed in range(3000)]
    td_count = kinds.count("return_td")
    assert 0 < td_count < len(kinds) * 0.05, f"{td_count}/3000 return_td outcomes -- expected rare, not {td_count}"


def test_punt_return_td_probability_decreases_with_distance():
    from app.engine.special_teams import _punt_return_td_probability
    assert _punt_return_td_probability(10) > _punt_return_td_probability(90)
