"""
R16 Step 4: Poaching (docs/R16_PRACTICE_SQUAD_ROSTER_IR_SPECIFICATION.md
Sec 5). DB/store isolation comes from tests/conftest.py (per-test golden
DB copy + session-scoped throwaway JSON stores), same as every other
R16 test module.
"""
from __future__ import annotations

import os

os.environ.setdefault("LEAGUE_SEED", "2025")

from fastapi.testclient import TestClient
from sqlmodel import select

from app.core.db import get_session
from app.data.teams import TEAMS
from app.engine import free_agency
from app.main import app
from app.models.player import Player, Position, RosterStatus
from app.services import roster_prep, season_state

client = TestClient(app)


def _release_all(team_abbr: str, position: Position) -> None:
    with get_session() as s:
        for p in s.exec(select(Player).where(Player.team_abbr == team_abbr, Player.position == position)):
            p.team_abbr = None
            s.add(p)
        s.commit()


def _trim_active_to(team_abbr: str, target: int) -> None:
    with get_session() as s:
        roster = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
        roster.sort(key=lambda p: p.overall_rating)
        for p in roster[: max(0, len(roster) - target)]:
            p.team_abbr = None
            s.add(p)
        s.commit()


def _send_to_ps(player_id: str, team_abbr: str, protected: bool = False, overall: int | None = None) -> Player:
    with get_session() as s:
        p = s.get(Player, player_id)
        p.roster_status = RosterStatus.PRACTICE_SQUAD
        p.ps_protected = protected
        if overall is not None:
            p.overall_rating = overall
        s.add(p)
        s.commit()
        s.refresh(p)
        return p


def test_weakest_active_need_ignores_ps_and_ir_depth():
    from app.engine import roster_strength

    season_state.reset_season()
    with get_session() as s:
        kc_cbs = sorted(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.CB)),
                          key=lambda p: -p.overall_rating)
    with get_session() as s:
        active_before = [p for p in s.exec(select(Player).where(Player.team_abbr == "KC"))]
    cb_rating_before = roster_strength.compute_group_ratings("KC", active_before)["CB"]

    # Send every CB but the WORST to the practice squad -- KC's ACTIVE CB
    # group rating should now reflect only his own (real, below-average)
    # depth, regardless of how many good CBs are sitting on the PS (a
    # full PS at a position must never mask a real active-roster
    # weakness, same principle Sec 9 already applies to
    # roster_shortfall()/the depth chart). Keeping the worst one active
    # (not an arbitrary one) guarantees the "after" rating is really
    # lower -- the snap-share-weighted blend of several real starters
    # CAN be lower than one single elite player's own raw rating, so an
    # arbitrary pick isn't a safe assumption here.
    for p in kc_cbs[:-1]:
        _send_to_ps(p.player_id, "KC")
    with get_session() as s:
        active_after = [p for p in s.exec(select(Player).where(Player.team_abbr == "KC", Player.roster_status == RosterStatus.ACTIVE))]
    cb_rating_after = roster_strength.compute_group_ratings("KC", active_after)["CB"]
    assert cb_rating_after < cb_rating_before  # PS depth no longer counts

    group, rating = roster_prep.weakest_active_need("KC")
    assert rating == min(roster_strength.compute_group_ratings("KC", active_after).values())


def test_find_poach_candidate_respects_protection_and_upgrade_margin():
    season_state.reset_season()
    # KC's only active CB is a 60 -- a real, clear need.
    with get_session() as s:
        kc_cbs = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.CB)))
    for p in kc_cbs[1:]:
        _send_to_ps(p.player_id, "KC")
    with get_session() as s:
        weak = s.get(Player, kc_cbs[0].player_id)
        weak.overall_rating = 60
        s.add(weak)
        s.commit()

    with get_session() as s:
        buf_cb = list(s.exec(select(Player).where(Player.team_abbr == "BUF", Player.position == Position.CB)))[0]
    marginal = _send_to_ps(buf_cb.player_id, "BUF", protected=False, overall=64)  # +4, below the margin
    pool = roster_prep._unprotected_ps_by_team()
    assert roster_prep.find_poach_candidate("KC", pool) is None  # not a CLEAR upgrade yet

    clear = _send_to_ps(buf_cb.player_id, "BUF", protected=False, overall=90)  # +30, clearly a real upgrade
    pool = roster_prep._unprotected_ps_by_team()
    found = roster_prep.find_poach_candidate("KC", pool)
    assert found is not None and found.player_id == clear.player_id

    # Protecting him takes him off the board entirely.
    _send_to_ps(clear.player_id, "BUF", protected=True, overall=90)
    pool = roster_prep._unprotected_ps_by_team()
    assert roster_prep.find_poach_candidate("KC", pool) is None


def test_execute_poach_signs_straight_to_the_53_with_a_three_week_lock():
    season_state.reset_season()
    with get_session() as s:
        buf_cb = list(s.exec(select(Player).where(Player.team_abbr == "BUF", Player.position == Position.CB)))[0]
    _send_to_ps(buf_cb.player_id, "BUF", protected=False, overall=90)

    roster_prep.execute_poach(buf_cb.player_id, "KC", week_num=3)
    with get_session() as s:
        poached = s.get(Player, buf_cb.player_id)
    assert poached.team_abbr == "KC"
    assert poached.roster_status == RosterStatus.ACTIVE  # never his own PS, decision #6
    assert poached.poached_from_team_abbr == "BUF"
    assert poached.roster_lock_until_week == 6
    assert poached.ps_protected is False


def test_block_poach_promotes_in_place_with_the_same_lock_but_no_poached_from():
    season_state.reset_season()
    with get_session() as s:
        kc_cb = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.CB)))[0]
    _send_to_ps(kc_cb.player_id, "KC")

    roster_prep.block_poach(kc_cb.player_id, week_num=5)
    with get_session() as s:
        blocked = s.get(Player, kc_cb.player_id)
    assert blocked.team_abbr == "KC" and blocked.roster_status == RosterStatus.ACTIVE
    assert blocked.roster_lock_until_week == 8
    assert blocked.poached_from_team_abbr is None


def test_clear_expired_poach_locks():
    season_state.reset_season()
    with get_session() as s:
        buf_cb = list(s.exec(select(Player).where(Player.team_abbr == "BUF", Player.position == Position.CB)))[0]
    _send_to_ps(buf_cb.player_id, "BUF", overall=90)
    roster_prep.execute_poach(buf_cb.player_id, "KC", week_num=1)

    roster_prep.clear_expired_poach_locks(week_num=4)  # still locked through week 4
    with get_session() as s:
        assert s.get(Player, buf_cb.player_id).roster_lock_until_week == 4

    roster_prep.clear_expired_poach_locks(week_num=5)  # now past it
    with get_session() as s:
        cleared = s.get(Player, buf_cb.player_id)
    assert cleared.roster_lock_until_week is None
    assert cleared.poached_from_team_abbr is None


def test_auto_protect_ai_ps_protects_exactly_the_top_four():
    season_state.reset_season()
    with get_session() as s:
        kc_roster = list(s.exec(select(Player).where(Player.team_abbr == "KC")))
    sample = sorted(kc_roster, key=lambda p: -p.overall_rating)[:6]
    for i, p in enumerate(sample):
        _send_to_ps(p.player_id, "KC", protected=(i % 2 == 0), overall=90 - i)  # scrambled starting state

    roster_prep.auto_protect_ai_ps(["KC"])
    with get_session() as s:
        ps = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.roster_status == RosterStatus.PRACTICE_SQUAD)))
    protected_ids = {p.player_id for p in ps if p.ps_protected}
    expected_ids = {p.player_id for p in sample[:4]}
    assert protected_ids == expected_ids
    assert sum(1 for p in ps if p.ps_protected) == 4


def test_run_weekly_poaching_is_idempotent_per_week_and_resolves_ai_vs_ai():
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    # NE needs an open 53 slot to poach at all (Sec 5.3) -- a real 62-man
    # import starts well over that, so trim it down first or NE never
    # even gets considered as a poacher (correctly skipped, per "if an
    # AI team has no room, it just doesn't poach that week").
    roster_prep.auto_cut_team_to_limits("NE")
    with get_session() as s:
        buf_cb = list(s.exec(select(Player).where(Player.team_abbr == "BUF", Player.position == Position.CB)))[0]
        buf_fillers = [p for p in s.exec(select(Player).where(Player.team_abbr == "BUF")) if p.player_id != buf_cb.player_id][:4]
        ne_cbs = list(s.exec(select(Player).where(
            Player.team_abbr == "NE", Player.position == Position.CB, Player.roster_status == RosterStatus.ACTIVE)))
    for p in ne_cbs[1:]:
        _send_to_ps(p.player_id, "NE")
    with get_session() as s:
        weak = s.get(Player, ne_cbs[0].player_id)
        weak.overall_rating = 1  # overwhelms any baseline group noise -- guaranteed the league-wide weakest
        s.add(weak)
        s.commit()
    # run_weekly_poaching() auto-protects BUF's own top 4 PS players
    # BEFORE any poacher gets to look (Sec 8) -- 4 higher-rated fillers
    # soak up those slots so the real bait (a genuine, but not BUF's
    # very best, upgrade for NE) is left genuinely unprotected. Without
    # this, a lone high-rated bait player would always rank in BUF's own
    # top 4 and get auto-protected before NE ever saw him -- a real
    # behavior this test would otherwise be flagging as a false bug.
    for filler in buf_fillers:
        _send_to_ps(filler.player_id, "BUF", overall=99)
    _send_to_ps(buf_cb.player_id, "BUF", overall=70)  # a real, clear upgrade for NE -- just not BUF's own best
    assert roster_prep.weakest_active_need("NE")[0] == "CB"  # sanity: the fixture actually set up what this test needs

    pending = roster_prep.run_weekly_poaching(season)
    assert pending is None  # AI (NE) vs AI (BUF) -- no user involvement
    with get_session() as s:
        moved = s.get(Player, buf_cb.player_id)
    assert moved.team_abbr == "NE" and moved.roster_status == RosterStatus.ACTIVE

    # Re-running the same week must NOT re-evaluate (idempotency guard).
    with get_session() as s:
        another_buf_cb = list(s.exec(select(Player).where(Player.team_abbr == "BUF", Player.position == Position.CB)))[0]
    _send_to_ps(another_buf_cb.player_id, "BUF", overall=70)
    result_again = roster_prep.run_weekly_poaching(season)
    assert result_again is None
    with get_session() as s:
        untouched = s.get(Player, another_buf_cb.player_id)
    assert untouched.team_abbr == "BUF" and untouched.roster_status == RosterStatus.PRACTICE_SQUAD


def test_run_weekly_poaching_gates_on_a_user_targeting_poach():
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        kc_cbs = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.CB)))
        ne_cbs = list(s.exec(select(Player).where(Player.team_abbr == "NE", Player.position == Position.CB)))
    for p in ne_cbs[1:]:
        _send_to_ps(p.player_id, "NE")
    with get_session() as s:
        weak = s.get(Player, ne_cbs[0].player_id)
        weak.overall_rating = 1
        s.add(weak)
        s.commit()
    target = _send_to_ps(kc_cbs[0].player_id, "KC", overall=95)  # the USER's own clear upgrade for NE
    assert roster_prep.weakest_active_need("NE")[0] == "CB"

    pending = roster_prep.run_weekly_poaching(season)
    assert pending is not None
    assert pending["player_id"] == target.player_id
    assert pending["from_team"] == "KC" and pending["to_team"] == "NE"
    with get_session() as s:
        untouched = s.get(Player, target.player_id)
    assert untouched.team_abbr == "KC" and untouched.roster_status == RosterStatus.PRACTICE_SQUAD  # not executed yet


def test_release_during_lock_reverts_to_original_team_ps_not_free_agency():
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        buf_cb = list(s.exec(select(Player).where(Player.team_abbr == "BUF", Player.position == Position.CB)))[0]
    _send_to_ps(buf_cb.player_id, "BUF", overall=90)
    roster_prep.execute_poach(buf_cb.player_id, "KC", week_num=1)  # now on KC's 53, locked through week 4
    season.current_week = 3

    resp = client.post(f"/roster/KC/{buf_cb.player_id}/release", follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        reverted = s.get(Player, buf_cb.player_id)
    assert reverted.team_abbr == "BUF"
    assert reverted.roster_status == RosterStatus.PRACTICE_SQUAD
    assert reverted.roster_lock_until_week is None
    assert reverted.poached_from_team_abbr is None


def test_send_to_ps_blocked_while_locked_then_allowed_after():
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    _trim_active_to("KC", 40)
    with get_session() as s:
        buf_cb = list(s.exec(select(Player).where(Player.team_abbr == "BUF", Player.position == Position.CB)))[0]
    _send_to_ps(buf_cb.player_id, "BUF", overall=90)
    roster_prep.execute_poach(buf_cb.player_id, "KC", week_num=1)  # locked through week 4

    season.current_week = 4
    assert client.post(f"/roster/KC/{buf_cb.player_id}/send-to-ps").status_code == 409
    season.current_week = 5
    resp = client.post(f"/roster/KC/{buf_cb.player_id}/send-to-ps", follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        assert s.get(Player, buf_cb.player_id).roster_status == RosterStatus.PRACTICE_SQUAD


def test_protect_ps_route_caps_at_four_and_persists():
    season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        kc_roster = list(s.exec(select(Player).where(Player.team_abbr == "KC")))
    sample = kc_roster[:5]
    for p in sample:
        _send_to_ps(p.player_id, "KC")

    resp = client.post("/roster/KC/protect-ps", data={"protected": [p.player_id for p in sample]})
    assert resp.status_code == 422  # 5 > the real 4-slot cap (decision #1)

    keep = sample[:4]
    resp = client.post("/roster/KC/protect-ps", data={"protected": [p.player_id for p in keep]}, follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        ps = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.roster_status == RosterStatus.PRACTICE_SQUAD)))
    protected_ids = {p.player_id for p in ps if p.ps_protected}
    assert protected_ids == {p.player_id for p in keep}


def test_practice_squad_market_excludes_own_team_and_protected_then_poaches():
    season_state.reset_season()
    season_state.set_user_team("KC")
    _trim_active_to("KC", 40)
    with get_session() as s:
        kc_cb = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.CB)))[0]
        buf_cb = list(s.exec(select(Player).where(Player.team_abbr == "BUF", Player.position == Position.CB)))[0]
        ne_cb = list(s.exec(select(Player).where(Player.team_abbr == "NE", Player.position == Position.CB)))[0]
    _send_to_ps(kc_cb.player_id, "KC")  # user's own PS -- must never appear
    _send_to_ps(buf_cb.player_id, "BUF", protected=True)  # protected -- must never appear
    _send_to_ps(ne_cb.player_id, "NE", protected=False)  # the one real target

    # Check real market rows (each one's own poach form action), not raw
    # name substrings -- a player's name can legitimately appear
    # elsewhere on the page too (e.g. a Team Card's own top-players list
    # embedded in the header's team switcher).
    page = client.get("/practice-squad-market").text
    assert f"/practice-squad-market/KC/{kc_cb.player_id}/poach" not in page
    assert f"/practice-squad-market/BUF/{buf_cb.player_id}/poach" not in page
    assert f"/practice-squad-market/NE/{ne_cb.player_id}/poach" in page

    resp = client.post(f"/practice-squad-market/NE/{ne_cb.player_id}/poach", follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        poached = s.get(Player, ne_cb.player_id)
    assert poached.team_abbr == "KC" and poached.roster_status == RosterStatus.ACTIVE
    assert poached.poached_from_team_abbr == "NE"


def test_poaching_alert_route_allow_and_block():
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        kc_cb = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.CB)))[0]
    target = _send_to_ps(kc_cb.player_id, "KC", overall=90)
    season.pending_poach = {
        "player_id": target.player_id, "player_name": target.full_name, "position": "CB",
        "from_team": "KC", "to_team": "NE", "week": season.current_week,
    }

    page = client.get("/poaching-alert").text
    assert "New England" in page and target.full_name in page

    resp = client.post("/poaching-alert/resolve", data={"action": "block"}, follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        blocked = s.get(Player, target.player_id)
    assert blocked.team_abbr == "KC" and blocked.roster_status == RosterStatus.ACTIVE
    assert blocked.poached_from_team_abbr is None
    assert season_state.get_season().pending_poach is None

    # A second target, this time letting it happen.
    _send_to_ps(kc_cb.player_id, "KC", overall=90)
    season = season_state.get_season()
    season.pending_poach = {
        "player_id": kc_cb.player_id, "player_name": kc_cb.full_name, "position": "CB",
        "from_team": "KC", "to_team": "NE", "week": season.current_week,
    }
    resp = client.post("/poaching-alert/resolve", data={"action": "allow"}, follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        allowed = s.get(Player, kc_cb.player_id)
    assert allowed.team_abbr == "NE" and allowed.poached_from_team_abbr == "KC"


def test_simulate_week_route_gates_on_a_pending_poach():
    season = season_state.reset_season()
    season_state.set_user_team("KC")
    # Poaching is scoped to the regular-season weekly pipeline (Sec 5.2),
    # not preseason -- and simulating preseason itself runs
    # prepare_ai_rosters() for every AI team (the "first game" trigger),
    # which would overwrite this test's own PS setup below if done
    # first. Clear preseason out of the way before setting anything up.
    season_state.simulate_preseason()
    # Only KC (the user) needs trimming to 53 -- a real 62-man import
    # would otherwise trip the OVER-53 gate first (checked ahead of the
    # poaching gate in the route), masking what this test actually
    # checks. NE being over 53 doesn't matter here: that gate only
    # applies to the user's own team.
    roster_prep.auto_cut_team_to_limits("KC")
    with get_session() as s:
        kc_cbs = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.CB)))
        ne_cbs = list(s.exec(select(Player).where(Player.team_abbr == "NE", Player.position == Position.CB)))
    for p in ne_cbs[1:]:
        _send_to_ps(p.player_id, "NE")
    with get_session() as s:
        weak = s.get(Player, ne_cbs[0].player_id)
        weak.overall_rating = 1
        s.add(weak)
        s.commit()
    target = _send_to_ps(kc_cbs[0].player_id, "KC", overall=99)
    assert roster_prep.weakest_active_need("NE")[0] == "CB"

    resp = client.post("/season/simulate-week", data={"redirect_to": "/season"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/poaching-alert")
    assert season_state.get_season().current_week == 1  # the week's games have NOT simulated yet
    assert season_state.get_season().pending_poach["player_id"] == target.player_id
