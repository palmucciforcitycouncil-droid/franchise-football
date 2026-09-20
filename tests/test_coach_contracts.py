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

def test_market_value_maps_the_overall_percentile_onto_the_role_range():
    """2026-09-14: priced on Brian's real 2026 role range (HC $4M-$10M,
    median $7M), not on whatever peers happen to be paid right now."""
    peers = [
        _peer("p1", CoachRole.HC, salary=1_000_000, overall_ratings=40),
        _peer("p2", CoachRole.HC, salary=5_000_000, overall_ratings=60),
        _peer("p3", CoachRole.HC, salary=10_000_000, overall_ratings=90),
    ]
    # The best-rated peer sits at the 100th percentile -> the range max.
    assert coach_contracts.coach_market_value(peers[2], peers) == pytest.approx(10_000_000)
    # Rated below every peer -> the range floor.
    below_all = _peer("outsider", CoachRole.HC, salary=0, overall_ratings=10)
    assert coach_contracts.coach_market_value(below_all, peers) == pytest.approx(4_000_000)


def test_market_value_only_compares_within_the_same_tier():
    """An HC and an AC with identical ratings must NOT be valued the
    same -- each is priced on its own role's range."""
    hc_peers = [_peer("hc1", CoachRole.HC, salary=10_000_000, overall_ratings=70)]
    ac_peers = [_peer("ac1", CoachRole.AC, salary=500_000, overall_ratings=70)]
    hc = _coach(CoachRole.HC, discipline=70, player_dev_offense=70, player_dev_defense=70,
                motivation_chemistry=70, red_zone_offense=70, red_zone_defense=70, reputation=70)
    ac = _coach(CoachRole.AC, discipline=70, player_dev_offense=70, player_dev_defense=70,
                motivation_chemistry=70, red_zone_offense=70, red_zone_defense=70, reputation=70)
    assert coach_contracts.coach_market_value(hc, hc_peers) == pytest.approx(10_000_000)
    assert coach_contracts.coach_market_value(ac, ac_peers) == pytest.approx(800_000)


def test_market_value_with_no_peers_uses_overall_on_the_rating_scale():
    """A pool candidate (salary_aav 0 at seed) must still get a real,
    in-range market salary -- Brian's "$0/yr" report.

    2026-09-20 fix: the no-peers fallback now reads `overall` against
    THIS role's own real REPUTATION_TIER_BAND (AC 35-58), not the old
    universal 40-99 scale -- so this test's `overall` must be a value
    that's actually plausible for an AC post-fix (`_coach()`'s default
    reputation/ratings of 70 is now ABOVE the entire AC band, which
    isn't a realistic AC to begin with)."""
    coach = _coach(
        CoachRole.AC, salary_aav=0, reputation=45,
        discipline=45, player_dev_offense=45, player_dev_defense=45,
        motivation_chemistry=45, red_zone_offense=45, red_zone_defense=45,
    )
    value = coach_contracts.coach_market_value(coach, peers=[])
    assert 200_000 < value < 800_000


def test_market_value_escalates_with_the_salary_cap_every_season():
    from app.config import season_year
    from app.engine import contracts
    peers = [_peer("p1", CoachRole.HC, salary=0, overall_ratings=70)]
    coach = peers[0]
    base_season = next(n for n in range(0, 60) if season_year(n) == 2026)
    v2026 = coach_contracts.coach_market_value(coach, peers, season_number=base_season)
    v2027 = coach_contracts.coach_market_value(coach, peers, season_number=base_season + 1)
    assert v2027 == pytest.approx(v2026 * (1 + contracts.SALARY_CAP_GROWTH))
    assert contracts.coach_salary_cap_for_season(base_season + 1) == pytest.approx(
        contracts.coach_salary_cap_for_season(base_season) * (1 + contracts.SALARY_CAP_GROWTH))


def test_affordable_salary_trims_to_cap_room_but_never_below_the_role_floor():
    assert coach_contracts.affordable_salary(CoachRole.AC, 600_000, 450_000, None) == pytest.approx(450_000)
    assert coach_contracts.affordable_salary(CoachRole.AC, 600_000, 5_000_000, None) == pytest.approx(600_000)
    assert coach_contracts.affordable_salary(CoachRole.AC, 600_000, -1, None) == pytest.approx(200_000)


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
