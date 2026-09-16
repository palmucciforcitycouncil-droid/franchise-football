"""
Preseason roster gate, AI hole filling, free-agent pool guarantee, the
Staff-stage offseason gate, and the combined Roster/Depth Chart page
(Brian's Sept 14 2026 asks). DB/store isolation comes from tests/conftest.py
(per-test golden DB copy + session-scoped throwaway JSON stores).
"""
from __future__ import annotations

import os

os.environ.setdefault("LEAGUE_SEED", "2025")

from fastapi.testclient import TestClient
from sqlmodel import select

from app.core.db import get_session
from app.data.teams import TEAMS
from app.engine import draft, free_agency
from app.main import app
from app.models.injury import Injury, InjurySeverity, InjuryType
from app.models.player import Player, Position, RosterStatus
from app.services import injury_store, roster_prep, season_state, undrafted_pool

client = TestClient(app)


def _player(position: Position, overall: int, player_id: str, salary: int = 1_000_000,
            team_abbr: str | None = None, years_pro: int = 3) -> Player:
    attrs = {name: 60 for name in draft.ALL_ATTR_FIELDS}
    return Player(
        player_id=player_id, first_name="T", last_name=player_id, position=position, team_abbr=team_abbr,
        age=25, overall_rating=overall, potential=overall, morale=70, years_pro=years_pro, salary=salary,
        contract_years_remaining=2, **attrs,
    )


# --- pure engine -----------------------------------------------------------

def test_roster_requirements_are_never_below_the_sim_hard_minimums():
    for pos, hard_min in free_agency.MIN_ROSTER_COUNTS.items():
        assert free_agency.ROSTER_REQUIREMENTS[pos] >= hard_min


def test_roster_shortfall_lists_only_short_positions():
    roster = [_player(Position.QB, 70, "qb1"), _player(Position.QB, 70, "qb2"), _player(Position.K, 70, "k1")]
    short = free_agency.roster_shortfall(roster)
    assert Position.QB not in short and Position.K not in short
    assert short[Position.WR] == 5 and short[Position.EDGE] == 3


def test_fill_roster_gaps_respects_the_cap_by_taking_an_affordable_player():
    """A capped-out team can't afford the star -- it signs the playable,
    affordable option instead of blowing through the cap."""
    from app.engine import contracts
    season_number = 24
    cap = contracts.salary_cap_for_season(season_number)
    star = _player(Position.P, 95, "p_star")
    cheap = _player(Position.P, 50, "p_cheap")
    room = contracts.expected_market_value(cheap, season_number) + 10_000
    roster = [_player(Position.QB, 80, "qb", salary=round(cap - room), team_abbr="ZZ")]
    assert contracts.expected_market_value(star, season_number) > room

    signed = free_agency.fill_roster_gaps("ZZ", roster, [star, cheap], season_number,
                                           requirements={Position.P: 1})
    assert [p.player_id for p in signed] == ["p_cheap"]
    assert signed[0].salary <= room


def test_fill_roster_gaps_still_fills_a_hole_when_nobody_is_affordable():
    from app.engine import contracts
    season_number = 24
    cap = contracts.salary_cap_for_season(season_number)
    roster = [_player(Position.QB, 80, "qb", salary=round(cap), team_abbr="ZZ")]  # zero cap room
    pool = [_player(Position.K, 70, "k_a"), _player(Position.K, 55, "k_b")]
    signed = free_agency.fill_roster_gaps("ZZ", roster, pool, season_number, requirements={Position.K: 1})
    assert len(signed) == 1
    assert signed[0].salary >= round(contracts.veteran_minimum(0, season_number))


def test_fill_roster_gaps_stamps_acquisition_fields():
    pool = [_player(Position.K, 60, "k_udfa"), _player(Position.P, 60, "p_vet")]
    signed = free_agency.fill_roster_gaps("ZZ", [], pool, 24, requirements={Position.K: 1, Position.P: 1},
                                           undrafted_ids={"k_udfa"})
    by_id = {p.player_id: p for p in signed}
    assert by_id["k_udfa"].acquisition_type == "Undrafted FA"
    assert by_id["p_vet"].acquisition_type == "Free Agent"
    assert by_id["p_vet"].acquisition_season == 2026


def test_supplemental_udfa_is_deterministic_and_in_the_low_rating_band():
    a = draft.supplemental_udfa_player(Position.EDGE, 3, 2025, 25)
    b = draft.supplemental_udfa_player(Position.EDGE, 3, 2025, 25)
    assert a.player_id == b.player_id and a.overall_rating == b.overall_rating and a.last_name == b.last_name
    assert a.player_id.startswith("udfa_25_EDGE_003_")
    assert a.team_abbr is None and a.position is Position.EDGE
    for ordinal in range(40):
        p = draft.supplemental_udfa_player(Position.CB, ordinal, 2025, 25)
        lo, hi = draft.SUPPLEMENTAL_UDFA_OVR_RANGE
        assert lo <= p.overall_rating <= hi
        assert p.age <= 24


# --- DB-backed services -----------------------------------------------------

def _release_all(team_abbr: str, position: Position) -> int:
    with get_session() as s:
        rows = list(s.exec(select(Player).where(Player.team_abbr == team_abbr, Player.position == position)))
        for p in rows:
            p.team_abbr = None
            s.add(p)
        s.commit()
    return len(rows)


def _trim_active_to(team_abbr: str, target: int) -> None:
    """Releases this team's worst-rated players (any position) down to
    exactly `target` active bodies -- used to simulate "the user already
    trimmed to 53 (or below)" without going through auto_cut_team_to_
    limits()'s own blunt rating-only cut, which can itself create a
    position hole (R16 Sec 8, see prepare_ai_rosters()'s own docstring
    for the real LV/Center bug this exact behavior caused)."""
    with get_session() as s:
        roster = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
        roster.sort(key=lambda p: p.overall_rating)
        for p in roster[: max(0, len(roster) - target)]:
            p.team_abbr = None
            s.add(p)
        s.commit()


def _delete_free_agents(position: Position) -> None:
    with get_session() as s:
        for p in s.exec(select(Player).where(Player.team_abbr == None, Player.position == position)):  # noqa: E711
            s.delete(p)
        s.commit()


def test_pool_guarantee_generates_enough_undrafted_free_agents_and_is_idempotent():
    # Make the league short at K with no free-agent kicker anywhere.
    _release_all("KC", Position.K)
    _release_all("BUF", Position.K)
    _delete_free_agents(Position.K)

    generated = roster_prep.ensure_free_agent_pool_depth(2025, 25)
    assert generated.get(Position.K, 0) >= 3  # ceil(2 * 1.2) = 3
    with get_session() as s:
        fa_kickers = list(s.exec(select(Player).where(Player.team_abbr == None, Player.position == Position.K)))  # noqa: E711
    assert len(fa_kickers) >= 3
    assert all(pid in undrafted_pool.tracked_ids() for pid in (p.player_id for p in fa_kickers))

    assert roster_prep.ensure_free_agent_pool_depth(2025, 25) == {}


def test_prepare_ai_rosters_fixes_every_ai_team_but_never_touches_the_user_team():
    _release_all("KC", Position.QB)
    _release_all("BUF", Position.CB)
    roster_prep.prepare_ai_rosters(2025, 24, user_team_abbr="KC")
    assert Position.QB in roster_prep.team_holes("KC")  # user's own team is left for the gate
    for team in TEAMS:
        if team.abbr != "KC":
            assert roster_prep.team_holes(team.abbr) == {}, team.abbr


def test_auto_fill_user_roster_fills_user_first_then_the_league():
    _release_all("KC", Position.TE)
    names = roster_prep.auto_fill_user_roster(2025, 24, "KC")
    assert len(names) >= 2
    assert roster_prep.team_holes("KC") == {}
    with get_session() as s:
        tes = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.TE)))
    assert all(p.acquisition_type in ("Free Agent", "Undrafted FA") for p in tes)


def test_preseason_gate_redirects_to_gm_desk_then_auto_fill_unblocks_it():
    """R16 Sec 10/decision #18: the shortfall gate now lands on GM Desk
    (signing happens there), not /roster (which is for trimming an
    over-53 roster instead) -- see _preseason_roster_gate_redirect()."""
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    _release_all("KC", Position.EDGE)
    # A real import carries 54-72 players per team -- releasing 6 EDGEs
    # alone still leaves KC over 53, which would trip the OTHER gate
    # first (decision #18's own stated order). Trim to 50 (leaving room
    # for the 3 EDGE signings Auto-Fill is about to make) so this test
    # exercises the shortfall gate in isolation, without landing back on
    # the over-53 gate the moment the shortfall is fixed.
    _trim_active_to("KC", 50)

    resp = client.post("/season/simulate-week", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/gm-desk?roster_gate=1")
    assert season_state.get_season().preseason_rounds_played == 0

    resp = client.post("/season/simulate-preseason", follow_redirects=False)
    assert resp.headers["location"].startswith("/gm-desk?")

    page = client.get("/gm-desk?roster_gate=1").text
    assert "Roster Holes" in page and "3 EDGE" in page and "AUTO-FILL ROSTER" in page

    resp = client.post("/roster/auto-fill-holes", follow_redirects=False)
    assert resp.status_code == 303
    page = client.get(resp.headers["location"]).text
    assert "Roster Ready" in page

    resp = client.post("/season/simulate-week", data={"redirect_to": "/season"}, follow_redirects=False)
    assert resp.headers["location"] == "/season"
    assert season_state.get_season().preseason_rounds_played == 1
    assert season.season_number == season_state.get_season().season_number


def test_first_game_prepares_ai_rosters_even_without_the_gate():
    season_state.reset_season()
    _release_all("BUF", Position.S)
    season_state.simulate_next_preseason_round()
    assert roster_prep.team_holes("BUF") == {}


# --- Staff-stage offseason gate ----------------------------------------------

def _set_contract_years(team_abbr: str, role_value: str, years: int) -> None:
    from app.models.coach import Coach
    from app.services import coach_store
    with get_session() as s:
        for c in s.exec(select(Coach).where(Coach.team_abbr == team_abbr)):
            if c.role == role_value or getattr(c.role, "value", None) == role_value:
                c.contract_years = years
                s.add(c)
        s.commit()
    coach_store.clear_cache()


def test_staff_stage_blocks_an_expired_head_coach_until_extended():
    import pytest
    from app.services import coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported")
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    season.offseason_stage = "staff"  # the gate itself doesn't care how we got here
    _set_contract_years("KC", "HC", 0)

    with pytest.raises(season_state.StaffRequirementError):
        season_state.advance_offseason_stage()
    resp = client.post("/offseason/advance-to-resign", follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"].startswith("/staff")
    assert season_state.get_season().offseason_stage == "staff"

    page = client.get("/staff").text
    assert "Head Coach contract expired. Extend or hire a replacement to continue." in page
    assert "Continue to Expiring Contracts" in page

    _set_contract_years("KC", "HC", 3)
    resp = client.post("/offseason/advance-to-resign", follow_redirects=False)
    assert resp.headers["location"] == "/gm-desk"
    assert season_state.get_season().offseason_stage == "resign"


def test_ensure_core_staff_repairs_ai_vacancies_and_expired_contracts():
    import pytest
    from app.engine import coach_replacement
    from app.services import coach_ai, coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported")
    season = season_state.reset_season()
    coach_replacement.execute_fire(coach_store.head_coach("BUF").coach_id)
    _set_contract_years("MIA", "DC", 0)
    assert coach_ai.core_staff_blockers("BUF") and coach_ai.core_staff_blockers("MIA")

    coach_ai.ensure_core_staff(season, exclude_team_abbr="KC")
    assert coach_ai.core_staff_blockers("BUF") == []
    assert coach_ai.core_staff_blockers("MIA") == []


def test_header_label_names_expiring_contracts_at_the_resign_stage():
    from types import SimpleNamespace
    from app.main import _sim_week_label
    done = SimpleNamespace(is_complete=True)
    season = SimpleNamespace(preseason_pending=False, is_complete=True, playoffs=done, offseason_stage="resign")
    assert _sim_week_label(season) == "Expiring Contracts"
    season.offseason_stage = "staff"
    assert _sim_week_label(season) == "Staff Decisions"


# --- Roster page -------------------------------------------------------------

def test_roster_page_has_roster_and_depth_chart_tabs_with_a_starter_legend():
    season_state.reset_season()
    page = client.get("/roster?team_abbr=KC").text
    assert 'data-roster-tab="roster"' in page and 'data-roster-tab="depth"' in page
    assert 'id="roster-depth-card"' in page
    assert "starter-legend" in page and "starter-last" in page
    assert page.count('id="roster-depth-card"') == 1
    # The stale OL/DL wiring paragraph is gone.
    assert "FB/K/P orders are saved but not consumed" not in page


def test_depth_chart_move_redirect_reopens_the_depth_tab():
    season_state.reset_season()
    with get_session() as s:
        qbs = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.QB)))
    resp = client.post(f"/depth-chart/KC/QB/move", data={"player_id": qbs[-1].player_id, "direction": "up"},
                       follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"].endswith("#depth-chart")


# --- R16 Step 3: Injured Reserve ---------------------------------------

def _give_injury(player_id: str, team_abbr: str, weeks_out: int, season_number: int = 24, week_injured: int = 1) -> None:
    injury_store.save_injuries([Injury(
        injury_id=f"{player_id}_{season_number}_{week_injured}", player_id=player_id, team_abbr=team_abbr,
        season_number=season_number, week_injured=week_injured,
        injury_type=InjuryType.KNEE, severity=InjurySeverity.MAJOR if weeks_out >= 4 else InjurySeverity.MINOR,
        weeks_out=weeks_out, placed_on_ir=(weeks_out >= 4), is_active=True,
    )])


def test_place_on_ir_requires_a_qualifying_injury_then_moves_the_player():
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        qb = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.QB)))[0]

    resp = client.post(f"/roster/KC/{qb.player_id}/place-on-ir")
    assert resp.status_code == 409  # no injury at all yet

    _give_injury(qb.player_id, "KC", weeks_out=2)  # real, but not IR-eligible
    resp = client.post(f"/roster/KC/{qb.player_id}/place-on-ir")
    assert resp.status_code == 409

    _give_injury(qb.player_id, "KC", weeks_out=6)  # now IR-eligible
    resp = client.post(f"/roster/KC/{qb.player_id}/place-on-ir", follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        moved = s.get(Player, qb.player_id)
    assert moved.roster_status == RosterStatus.IR
    assert moved.ir_placed_week == season.current_week


def test_ir_reactivation_blocked_before_four_weeks_then_allowed_both_ways():
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        # The starter (highest-rated), so trimming the roster below can
        # never accidentally release the very player this test tracks.
        qb = max(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.QB)),
                  key=lambda p: p.overall_rating)
    # A real import carries 54-72 players -- trim well below 53 first so
    # the OTHER "active roster is already full" 409 (promote-to-53's own,
    # unrelated check) can't mask the IR-eligibility gate this test cares
    # about.
    _trim_active_to("KC", 40)
    _give_injury(qb.player_id, "KC", weeks_out=8)
    client.post(f"/roster/KC/{qb.player_id}/place-on-ir")

    # Not yet eligible: 0, 1, 3 weeks elapsed.
    for elapsed in (0, 1, 3):
        season.current_week = 1 + elapsed
        assert client.post(f"/roster/KC/{qb.player_id}/promote-to-53").status_code == 409
        assert client.post(f"/roster/KC/{qb.player_id}/send-to-ps").status_code == 409

    # Exactly 4 weeks: eligible for the active 53.
    season.current_week = 5
    resp = client.post(f"/roster/KC/{qb.player_id}/promote-to-53", follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        assert s.get(Player, qb.player_id).roster_status == RosterStatus.ACTIVE

    # Same 4-week floor applies to the PS path too (a fresh IR stint) --
    # resolve the first injury first so this player has only ONE active
    # injury at a time, same real invariant the game itself maintains.
    injury_store.resolve_all_active()
    _give_injury(qb.player_id, "KC", weeks_out=8, week_injured=5)
    client.post(f"/roster/KC/{qb.player_id}/place-on-ir")
    season.current_week = 5 + 3
    assert client.post(f"/roster/KC/{qb.player_id}/send-to-ps").status_code == 409
    season.current_week = 5 + 4
    resp = client.post(f"/roster/KC/{qb.player_id}/send-to-ps", follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        assert s.get(Player, qb.player_id).roster_status == RosterStatus.PRACTICE_SQUAD


def test_auto_place_ai_players_on_ir_skips_the_user_team():
    season_state.reset_season()
    with get_session() as s:
        kc_qb = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.QB)))[0]
        buf_qb = list(s.exec(select(Player).where(Player.team_abbr == "BUF", Player.position == Position.QB)))[0]

    ir_injury = Injury(injury_id="kc_ir_test", player_id=kc_qb.player_id, team_abbr="KC",
                        season_number=24, week_injured=3, injury_type=InjuryType.KNEE,
                        severity=InjurySeverity.MAJOR, weeks_out=8, placed_on_ir=True, is_active=True)
    user_ir_injury = Injury(injury_id="buf_ir_test", player_id=buf_qb.player_id, team_abbr="BUF",
                             season_number=24, week_injured=3, injury_type=InjuryType.KNEE,
                             severity=InjurySeverity.MAJOR, weeks_out=8, placed_on_ir=True, is_active=True)

    moved = roster_prep.auto_place_ai_players_on_ir([ir_injury, user_ir_injury], user_team_abbr="BUF", week_num=3)
    assert moved == [kc_qb.full_name]
    with get_session() as s:
        assert s.get(Player, kc_qb.player_id).roster_status == RosterStatus.IR
        assert s.get(Player, kc_qb.player_id).ir_placed_week == 3
        assert s.get(Player, buf_qb.player_id).roster_status == RosterStatus.ACTIVE  # the user's own team untouched
