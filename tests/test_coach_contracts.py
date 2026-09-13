"""
Coach Contract Realism + "Extend Contract" tests
(docs/R3d_COACHING_SYSTEM_SPECIFICATION.md Sec 11).

Style follows tests/test_coach_hiring.py's own convention: hand-built,
exact-value tests for the pure functions; DB-backed assertions only
where a DB is genuinely what's under test.
"""
from __future__ import annotations

import pytest

from app.engine import coach_contracts
from app.engine.coach_hiring import contract_modifier
from app.models.coach import Coach, CoachRole


def _coach(role: CoachRole, **overrides) -> Coach:
    defaults = dict(
        coach_id="test_coach", first_name="Test", last_name="Coach", role=role,
        team_abbr="KC", reputation=70, salary_aav=1_000_000,
        player_dev_offense=70, player_dev_defense=70, discipline=70,
        motivation_chemistry=70, red_zone_offense=70, red_zone_defense=70,
    )
    defaults.update(overrides)
    return Coach(**defaults)


def _peer(coach_id: str, role: CoachRole, salary: int, overall_ratings: int) -> Coach:
    """A synthetic peer whose SIX performance ratings + reputation are
    all set to `overall_ratings`, so `.overall` (0.5*perf + 0.5*reputation)
    lands exactly on that number -- makes the percentile math in these
    tests exact, not approximate."""
    return Coach(
        coach_id=coach_id, first_name="P", last_name=coach_id, role=role,
        team_abbr="ZZZ", salary_aav=salary, reputation=overall_ratings,
        player_dev_offense=overall_ratings, player_dev_defense=overall_ratings,
        discipline=overall_ratings, motivation_chemistry=overall_ratings,
        red_zone_offense=overall_ratings, red_zone_defense=overall_ratings,
    )


# --------------------------------------------------------------------
# coach_market_value()
# --------------------------------------------------------------------

def test_market_value_is_the_salary_at_the_matching_overall_percentile():
    peers = [
        _peer("p1", CoachRole.HC, salary=1_000_000, overall_ratings=40),
        _peer("p2", CoachRole.HC, salary=5_000_000, overall_ratings=60),
        _peer("p3", CoachRole.HC, salary=10_000_000, overall_ratings=90),
    ]
    # The best-rated peer's own value should map to the highest salary.
    best = peers[2]
    assert coach_contracts.coach_market_value(best, peers) == pytest.approx(10_000_000)
    # A coach rated below every one of these three peers (not one of them
    # itself, avoiding the "at-or-below" percentile's own self-inclusion --
    # same technique reputation_from_salary() already uses at import time)
    # should map to the lowest salary.
    below_all = _peer("outsider", CoachRole.HC, salary=0, overall_ratings=10)
    assert coach_contracts.coach_market_value(below_all, peers) == pytest.approx(1_000_000)


def test_market_value_only_compares_within_the_same_tier():
    """An HC and an AC with identical ratings must NOT be valued the
    same -- comparing an assistant's pay to a head coach's would be
    meaningless (same reasoning reputation_from_salary() already uses
    at import time)."""
    hc_peers = [_peer("hc1", CoachRole.HC, salary=10_000_000, overall_ratings=70)]
    ac_peers = [_peer("ac1", CoachRole.AC, salary=500_000, overall_ratings=70)]
    hc = _coach(CoachRole.HC, discipline=70, player_dev_offense=70, player_dev_defense=70,
                motivation_chemistry=70, red_zone_offense=70, red_zone_defense=70, reputation=70)
    ac = _coach(CoachRole.AC, discipline=70, player_dev_offense=70, player_dev_defense=70,
                motivation_chemistry=70, red_zone_offense=70, red_zone_defense=70, reputation=70)
    assert coach_contracts.coach_market_value(hc, hc_peers) == pytest.approx(10_000_000)
    assert coach_contracts.coach_market_value(ac, ac_peers) == pytest.approx(500_000)


def test_market_value_falls_back_to_own_salary_with_no_real_peers():
    coach = _coach(CoachRole.HC, salary_aav=3_000_000)
    assert coach_contracts.coach_market_value(coach, peers=[]) == pytest.approx(3_000_000)


# --------------------------------------------------------------------
# evaluate_extension()
# --------------------------------------------------------------------

def test_extension_at_full_market_value_and_full_years_is_accepted():
    peers = [_peer("p1", CoachRole.HC, salary=10_000_000, overall_ratings=70)]
    coach = _coach(CoachRole.HC, discipline=70, player_dev_offense=70, player_dev_defense=70,
                   motivation_chemistry=70, red_zone_offense=70, red_zone_defense=70, reputation=70)
    market = coach_contracts.coach_market_value(coach, peers)
    result = coach_contracts.evaluate_extension(coach, offered_aav=market, offered_years=5, team_win_pct=1.0, peers=peers)
    assert result.verdict == coach_contracts.ExtensionVerdict.ACCEPT


def test_a_lowball_extension_offer_is_rejected():
    peers = [_peer("p1", CoachRole.HC, salary=10_000_000, overall_ratings=70)]
    coach = _coach(CoachRole.HC, discipline=70, player_dev_offense=70, player_dev_defense=70,
                   motivation_chemistry=70, red_zone_offense=70, red_zone_defense=70, reputation=70)
    result = coach_contracts.evaluate_extension(coach, offered_aav=1.0, offered_years=1, team_win_pct=0.0, peers=peers)
    assert result.verdict == coach_contracts.ExtensionVerdict.REJECT


def test_a_middling_offer_counters_toward_the_accepting_aav():
    peers = [_peer("p1", CoachRole.HC, salary=10_000_000, overall_ratings=70)]
    coach = _coach(CoachRole.HC, discipline=70, player_dev_offense=70, player_dev_defense=70,
                   motivation_chemistry=70, red_zone_offense=70, red_zone_defense=70, reputation=70)
    market = coach_contracts.coach_market_value(coach, peers)
    result = coach_contracts.evaluate_extension(coach, offered_aav=market * 0.85, offered_years=5, team_win_pct=1.0, peers=peers)
    assert result.verdict == coach_contracts.ExtensionVerdict.COUNTER
    assert result.counter_aav > market * 0.85
    # Resubmitting the counter must clear ACCEPT this time.
    resubmit = coach_contracts.evaluate_extension(
        coach, offered_aav=result.counter_aav, offered_years=result.counter_years, team_win_pct=1.0, peers=peers)
    assert resubmit.verdict == coach_contracts.ExtensionVerdict.ACCEPT


def test_a_better_team_situation_lowers_the_bar_to_accept():
    peers = [_peer("p1", CoachRole.HC, salary=10_000_000, overall_ratings=70)]
    coach = _coach(CoachRole.HC, discipline=70, player_dev_offense=70, player_dev_defense=70,
                   motivation_chemistry=70, red_zone_offense=70, red_zone_defense=70, reputation=70)
    market = coach_contracts.coach_market_value(coach, peers)
    good_team = coach_contracts.evaluate_extension(coach, offered_aav=market * 0.9, offered_years=5, team_win_pct=1.0, peers=peers)
    bad_team = coach_contracts.evaluate_extension(coach, offered_aav=market * 0.9, offered_years=5, team_win_pct=0.0, peers=peers)
    assert good_team.offer_score > bad_team.offer_score


# --------------------------------------------------------------------
# contract_modifier() -- the real "reduce JSS volatility" mechanic
# --------------------------------------------------------------------

def test_a_fresh_contract_is_more_protected_than_an_expired_one():
    assert contract_modifier(4) < contract_modifier(1) < contract_modifier(0)


def test_contract_modifier_floors_and_never_goes_negative():
    assert contract_modifier(50) >= 0.6
    assert contract_modifier(0) > 0
