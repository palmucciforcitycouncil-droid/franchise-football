"""
Free Agency tests (ROADMAP.md R4b; GDD Part 1 Sec 8.4). Style follows
this suite's existing convention -- hand-built fixtures, exact/
directional expected values for the pure functions. See
app/engine/free_agency.py's own module docstring for the real,
disclosed scope cut (no multi-team AI bidding) from the GDD's fuller
design.
"""
from __future__ import annotations

from app.engine import free_agency
from app.models.player import Player, Position


def _player(position: Position, overall: int, player_id: str, age: int = 26,
            years_pro: int = 4, salary: int = 5_000_000, team_abbr: str | None = None,
            contract_years_remaining: int = 1) -> Player:
    return Player(
        player_id=player_id, first_name="Test", last_name=player_id, position=position,
        team_abbr=team_abbr, age=age, overall_rating=overall, potential=overall, morale=70,
        years_pro=years_pro, salary=salary, contract_years_remaining=contract_years_remaining,
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


def test_role_fit_is_starter_when_the_free_agent_clearly_upgrades_the_position():
    player = _player(Position.WR, 90, "wr1")
    assert free_agency.role_fit_for(player, current_group_rating=70.0) == free_agency.RoleFit.STARTER


def test_role_fit_is_depth_when_the_team_is_already_much_better_there():
    player = _player(Position.WR, 60, "wr1")
    assert free_agency.role_fit_for(player, current_group_rating=85.0) == free_agency.RoleFit.DEPTH


def test_role_fit_is_starter_when_the_team_has_nobody_at_the_position_at_all():
    player = _player(Position.K, 70, "k1")
    assert free_agency.role_fit_for(player, current_group_rating=None) == free_agency.RoleFit.STARTER


def test_an_offer_over_cap_space_is_rejected_as_over_cap_not_a_normal_reject():
    player = _player(Position.QB, 90, "qb1")
    roster = [_player(Position.WR, 80, f"w{i}", salary=90_000_000, team_abbr="ZZ") for i in range(10)]
    result = free_agency.evaluate_fa_offer(
        player, "ZZ", offered_aav=50_000_000, offered_years=4, season_number=0,
        team_rating=90.0, current_group_rating=60.0, team_players_for_cap=roster,
    )
    assert result.verdict == free_agency.FAOfferVerdict.OVER_CAP


def test_a_strong_offer_to_a_cap_healthy_team_is_accepted():
    player = _player(Position.WR, 80, "wr1")
    from app.engine import contracts
    expected = contracts.expected_market_value(player, 0)
    result = free_agency.evaluate_fa_offer(
        player, "ZZ", offered_aav=expected * 1.3, offered_years=5, season_number=0,
        team_rating=95.0, current_group_rating=None, team_players_for_cap=[],
    )
    assert result.verdict == free_agency.FAOfferVerdict.ACCEPT


def test_release_expired_contracts_frees_only_players_at_zero_years():
    roster = [
        _player(Position.WR, 80, "wr1", team_abbr="ZZ", contract_years_remaining=0),
        _player(Position.QB, 90, "qb1", team_abbr="ZZ", contract_years_remaining=2),
    ]
    released = free_agency.release_expired_contracts(roster)
    assert released == 1
    assert roster[0].team_abbr is None
    assert roster[1].team_abbr == "ZZ"


def test_release_expired_contracts_is_a_noop_on_a_healthy_roster():
    roster = [_player(Position.WR, 80, "wr1", team_abbr="ZZ", contract_years_remaining=3)]
    assert free_agency.release_expired_contracts(roster) == 0
    assert roster[0].team_abbr == "ZZ"


def test_fill_roster_gaps_signs_the_best_available_free_agent_at_an_empty_position():
    """The exact failure mode this function exists to prevent: a real
    IndexError crash when depth_chart.py unconditionally indexes an
    empty position, caught on this chunk's own first real two-season
    test run (a team with zero punters after enough contract churn)."""
    roster = [_player(Position.QB, 80, "qb1", team_abbr="ZZ")]  # no punter at all
    pool = [
        _player(Position.P, 60, "p_weak", team_abbr=None),
        _player(Position.P, 75, "p_strong", team_abbr=None),
    ]
    signed = free_agency.fill_roster_gaps("ZZ", roster, pool, season_number=0)
    assert len(signed) == 1
    assert signed[0].player_id == "p_strong"  # best-rated, not first
    assert signed[0].team_abbr == "ZZ"
    assert signed[0] not in pool  # removed from the shared pool


def test_fill_roster_gaps_never_signs_a_player_twice_across_two_teams_sharing_one_pool():
    team_a_roster: list[Player] = []
    team_b_roster: list[Player] = []
    shared_pool = [_player(Position.K, 70, "k1", team_abbr=None)]

    signed_a = free_agency.fill_roster_gaps("AA", team_a_roster, shared_pool, season_number=0)
    signed_b = free_agency.fill_roster_gaps("BB", team_b_roster, shared_pool, season_number=0)

    assert len(signed_a) == 1
    assert signed_b == []  # nobody left in the shared pool for team B


def test_fill_roster_gaps_leaves_a_position_unfilled_when_the_league_has_nobody_left():
    roster: list[Player] = []
    signed = free_agency.fill_roster_gaps("ZZ", roster, free_agent_pool=[], season_number=0)
    assert signed == []  # disclosed gap, not a crash -- nobody to sign
