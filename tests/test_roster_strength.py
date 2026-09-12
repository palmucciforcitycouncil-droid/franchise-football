"""
Roster Strength tests (docs/handoff_prestige_and_coach_impact.md A1).

Group-aggregation and weighting are pure functions of a player list, so
those are tested with hand-built Player rows and exact expected values
(this suite's existing convention -- see test_coaching.py, test_scouting.py).
The coach blend and the full compute_roster_strength() entry point are
read-only against the real DB, which app/core/db.py's own docstring
establishes as fine unchanged ("every read-only test in this codebase
uses the real DB_PATH unchanged") -- no copy-to-throwaway needed since
nothing here writes.
"""
from __future__ import annotations

from app.data.teams import TEAMS
from app.engine import roster_strength
from app.models.player import Player, Position
from app.services import coach_store


def _player(position: Position, overall: int, player_id: str, team_abbr: str = "ZZ") -> Player:
    return Player(
        player_id=player_id, first_name="Test", last_name=player_id, position=position,
        team_abbr=team_abbr, age=25, overall_rating=overall, potential=overall, morale=70,
        speed=70, acceleration=70, strength=70, agility=70, jumping=70, stamina=70,
        toughness=70, durability=70, throw_power=70, throw_accuracy_short=70,
        throw_accuracy_mid=70, throw_accuracy_deep=70, play_action=70, throw_on_the_run=70,
        throw_under_pressure=70, break_sack=70, catching=70, spectacular_catch=70,
        catch_in_traffic=70, short_route_running=70, medium_route_running=70,
        deep_route_running=70, release=70, carrying=70, trucking=70, change_of_direction=70,
        ball_carrier_vision=70, stiff_arm=70, spin_move=70, juke_move=70, break_tackle=70,
        run_block=70, pass_block=70, run_block_power=70, run_block_finesse=70,
        pass_block_power=70, pass_block_finesse=70, lead_block=70, impact_blocking=70,
        tackle=70, hit_power=70, block_shedding=70, pursuit=70, play_recognition=70,
        man_coverage=70, zone_coverage=70, press=70, power_moves=70, finesse_moves=70,
        kick_power=70, kick_accuracy=70, kick_return=70, awareness=70,
    )


# --------------------------------------------------------------------
# compute_group_ratings -- pure, no DB
# --------------------------------------------------------------------

def test_a_lone_player_at_a_position_gets_the_full_share():
    roster = [_player(Position.QB, 90, "qb1")]
    ratings = roster_strength.compute_group_ratings("ZZ", roster)
    assert ratings["QB"] == 90.0


def test_snap_share_weighting_favors_the_depth_chart_starter():
    """QB uses IRON_MAN_DECAY (0.10, max_depth 2): the backup's rating
    should barely move the group number away from the starter's."""
    roster = [_player(Position.QB, 90, "qb1"), _player(Position.QB, 50, "qb2")]
    ratings = roster_strength.compute_group_ratings("ZZ", roster)
    decay = roster_strength.IRON_MAN_DECAY
    expected = (90 * 1.0 + 50 * decay) / (1.0 + decay)
    assert ratings["QB"] == expected
    # The starter's rating should dominate: closer to 90 than to the
    # midpoint of 90 and 50.
    assert ratings["QB"] > 85


def test_a_third_stringer_beyond_max_depth_never_counts():
    roster = [_player(Position.QB, 90, "qb1"), _player(Position.QB, 60, "qb2"),
              _player(Position.QB, 1, "qb3")]
    with_third = roster_strength.compute_group_ratings("ZZ", roster)
    without_third = roster_strength.compute_group_ratings("ZZ", roster[:2])
    assert with_third["QB"] == without_third["QB"]


def test_multi_position_group_averages_its_constituent_slots_equally():
    """"G" = LG + RG. With one lone player at each slot, the group
    rating is a plain average of the two -- not weighted by anything
    else, since each slot only has its own one starter."""
    roster = [_player(Position.LG, 80, "lg1"), _player(Position.RG, 60, "rg1")]
    ratings = roster_strength.compute_group_ratings("ZZ", roster)
    assert ratings["G"] == 70.0


def test_a_group_with_no_players_at_any_constituent_position_is_omitted():
    roster = [_player(Position.QB, 90, "qb1")]
    ratings = roster_strength.compute_group_ratings("ZZ", roster)
    assert "K" not in ratings
    assert "S" not in ratings


# --------------------------------------------------------------------
# compute_roster_score -- weighted average, renormalized over present groups
# --------------------------------------------------------------------

def test_roster_score_is_the_uniform_value_when_every_group_matches():
    ratings = {g: 75.0 for g in roster_strength.QUOTA_GROUPS}
    assert roster_strength.compute_roster_score(ratings) == 75.0


def test_roster_score_renormalizes_over_only_the_present_groups():
    # Only QB present: its own weight cancels out of the average.
    assert roster_strength.compute_roster_score({"QB": 88.0}) == 88.0


def test_qb_moves_roster_score_more_than_kicker_and_punter_combined():
    base = {g: 70.0 for g in roster_strength.QUOTA_GROUPS}
    boosted_qb = dict(base, QB=99.0)
    boosted_st = dict(base, K=99.0, P=99.0)
    base_score = roster_strength.compute_roster_score(base)
    qb_gain = roster_strength.compute_roster_score(boosted_qb) - base_score
    st_gain = roster_strength.compute_roster_score(boosted_st) - base_score
    assert qb_gain > st_gain


# --------------------------------------------------------------------
# compute_roster_strength -- the coach blend, read-only against the real DB
# --------------------------------------------------------------------

def test_team_rating_blends_roster_score_with_head_coach_overall():
    result = roster_strength.compute_roster_strength("KC")
    hc = coach_store.head_coach("KC")
    if hc is None:
        import pytest
        pytest.skip("this database has no coaches imported")
    assert result.coach_overall == hc.overall
    expected = (1 - roster_strength.COACH_WEIGHT) * result.roster_score + \
        roster_strength.COACH_WEIGHT * hc.overall
    assert result.team_rating == expected
    assert result.team_rating != result.roster_score


def test_no_head_coach_degrades_to_roster_score_alone(monkeypatch):
    monkeypatch.setattr(coach_store, "head_coach", lambda team_abbr: None)
    result = roster_strength.compute_roster_strength("KC")
    assert result.coach_overall is None
    assert result.team_rating == result.roster_score


def test_every_real_team_computes_all_fourteen_groups_within_bounds():
    for team in TEAMS:
        result = roster_strength.compute_roster_strength(team.abbr)
        assert set(result.group_ratings) == set(roster_strength.QUOTA_GROUPS), team.abbr
        for group, rating in result.group_ratings.items():
            assert 0 <= rating <= 99, (team.abbr, group, rating)
        assert 0 <= result.roster_score <= 99, team.abbr
        assert 0 <= result.team_rating <= 99, team.abbr
