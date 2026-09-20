"""
R16 Step 5: Game-Day Elevation (docs/R16_PRACTICE_SQUAD_ROSTER_IR_SPECIFICATION.md
Sec 6). DB/store isolation comes from tests/conftest.py (per-test golden
DB copy + session-scoped throwaway JSON stores), same as every other
R16 test module.
"""
from __future__ import annotations

import os

os.environ.setdefault("LEAGUE_SEED", "2025")

from fastapi.testclient import TestClient
from sqlmodel import select

from app.core.db import get_session
from app.main import app
from app.models.player import Player, Position, RosterStatus
from app.services import depth_chart, roster_prep, season_state

client = TestClient(app)


def _send_to_ps(player_id: str) -> None:
    with get_session() as s:
        p = s.get(Player, player_id)
        p.roster_status = RosterStatus.PRACTICE_SQUAD
        s.add(p)
        s.commit()


def test_elevate_route_requires_a_practice_squad_player():
    season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        active_qb = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.QB)))[0]

    resp = client.post(f"/roster/KC/{active_qb.player_id}/elevate")
    assert resp.status_code == 409  # still ACTIVE, not PS

    _send_to_ps(active_qb.player_id)
    resp = client.post(f"/roster/KC/{active_qb.player_id}/elevate", follow_redirects=False)
    assert resp.status_code == 303
    with get_session() as s:
        assert s.get(Player, active_qb.player_id).roster_status == RosterStatus.ELEVATED


def test_elevated_player_is_depth_chart_eligible_like_active():
    season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        qbs = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.position == Position.QB)))
    best = max(qbs, key=lambda p: p.overall_rating)
    _send_to_ps(best.player_id)
    depth_chart.clear_starters_cache()
    # On the practice squad, he must never be the starter regardless of rating.
    assert depth_chart.get_offensive_starters("KC").qb.player_id != best.player_id

    client.post(f"/roster/KC/{best.player_id}/elevate")
    depth_chart.clear_starters_cache()
    assert depth_chart.get_offensive_starters("KC").qb.player_id == best.player_id


def test_elevation_auto_reverts_after_the_week_simulates():
    season_state.reset_season()
    season_state.set_user_team("KC")
    roster_prep.auto_cut_team_to_limits("KC")
    with get_session() as s:
        ps_player = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.roster_status == RosterStatus.PRACTICE_SQUAD)))[0]
    client.post(f"/roster/KC/{ps_player.player_id}/elevate")
    with get_session() as s:
        assert s.get(Player, ps_player.player_id).roster_status == RosterStatus.ELEVATED

    season_state.simulate_preseason()  # clears the preseason gate, doesn't touch ELEVATED (Sec 6 ties the revert to simulate_current_week specifically)
    season = season_state.get_season()
    season.pending_poach = None  # sidestep any incidental poaching gate for this narrowly-scoped test
    season.poaching_evaluated_through_week = season.current_week
    season_state.simulate_current_week()

    with get_session() as s:
        reverted = s.get(Player, ps_player.player_id)
    assert reverted.roster_status == RosterStatus.PRACTICE_SQUAD


def test_elevate_does_not_count_toward_the_53_cap():
    season_state.reset_season()
    season_state.set_user_team("KC")
    roster_prep.auto_cut_team_to_limits("KC")
    before = roster_prep.active_roster_count("KC")
    with get_session() as s:
        ps_player = list(s.exec(select(Player).where(Player.team_abbr == "KC", Player.roster_status == RosterStatus.PRACTICE_SQUAD)))[0]
    client.post(f"/roster/KC/{ps_player.player_id}/elevate")
    assert roster_prep.active_roster_count("KC") == before  # ELEVATED, not ACTIVE
