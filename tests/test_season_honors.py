"""
Season honors (2026-09-14): frozen final awards + Pro Bowl at the end of
the regular season, Super Bowl result/MVP, dated player/coach award
history, player retirement, offseason-start headlines, and the pages
that show them (Awards, Playoffs, Season Summary, Player/Coach Cards).
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

import json
from pathlib import Path

import pytest

from app.engine import awards
from app.engine.offseason_headlines import season_end_headlines
from app.engine.retirement import retirement_probability
from app.models.player import Position
from app.services import honors_store

DB_EXISTS = Path("data/franchise_football.db").exists()


# --- pure pieces -------------------------------------------------------------

def test_super_bowl_numeral_matches_real_numbering():
    assert awards.super_bowl_numeral(2025) == "LX"
    assert awards.super_bowl_numeral(2026) == "LXI"
    assert awards.super_bowl_numeral(2003) == "XXXVIII"


def test_honors_store_awards_are_idempotent_and_grouped(tmp_path):
    path = tmp_path / "honors.json"
    added = honors_store.add_player_awards([("p1", 24, "Pro Bowl"), ("p1", 25, "Pro Bowl"), ("p1", 25, "MVP")], path)
    assert len(added) == 3
    # Replaying the same credits changes nothing.
    assert honors_store.add_player_awards([("p1", 25, "MVP"), ("", 25, "MVP")], path) == []
    rows = honors_store.player_awards("p1", path)
    assert len(rows) == 3
    grouped = honors_store.group_awards(rows)
    assert grouped[0] == {"award": "MVP", "count": 1, "years": [2027]}
    assert grouped[1] == {"award": "Pro Bowl", "count": 2, "years": [2027, 2026]}


def test_honors_store_season_fields_round_trip(tmp_path):
    path = tmp_path / "honors.json"
    assert honors_store.get_final_awards(3, path) is None
    honors_store.save_final_awards(3, {"mvp": []}, path)
    honors_store.save_super_bowl(3, {"winner_abbr": "KC"}, path)
    assert honors_store.get_final_awards(3, path) == {"mvp": []}
    assert honors_store.get_super_bowl(3, path) == {"winner_abbr": "KC"}
    assert honors_store.has_any_season_data(3, path)
    assert not honors_store.has_any_season_data(4, path)


def test_retirement_probability_shape():
    assert retirement_probability(Position.WR, 25, 80, False) == 0.0
    young_fa = retirement_probability(Position.WR, 28, 60, True)
    assert young_fa > 0.3  # an unsigned 28-year-old is likely done
    assert retirement_probability(Position.QB, 31, 90, False) == 0.0  # QBs play longer
    star = retirement_probability(Position.LB, 34, 88, False)
    fading = retirement_probability(Position.LB, 34, 65, False)
    assert 0 < star < fading
    assert retirement_probability(Position.S, 50, 40, True) == pytest.approx(0.95)


def test_season_end_headlines_lead_with_super_bowl_and_awards():
    sb = {"winner_abbr": "KC", "loser_abbr": "SF", "winner_score": 31, "loser_score": 25, "numeral": "LXI",
          "mvp": {"name": "Pat Q", "position": "QB", "stat_line": "306 Passing Yards | 1 TD | 0 INT"}}
    final = {"mvp": [{"name": "Jo B", "team_abbr": "BUF", "position": "QB", "player_position": "QB", "stat_line": "4,000 pass yds"}],
             "coty": [{"name": "Coach C", "team_abbr": "DET", "record": "14-3"}]}
    lines = season_end_headlines(2026, sb, final)
    assert lines[0] == "Kansas City win Super Bowl LXI, beating San Francisco 31-25"
    assert lines[1].startswith("Pat Q (QB) named Super Bowl MVP: 306 Passing Yards")
    assert any("league MVP" in l and "Jo B" in l for l in lines)
    assert any("Coach of the Year" in l for l in lines)
    assert season_end_headlines(2026, None, None) == ["The 2026 season is in the books."]


def test_acquisition_label_formats():
    from types import SimpleNamespace
    from app.main import _acquisition_label

    def p(**kw):
        base = dict(acquisition_type=None, acquisition_season=None, acquisition_round=None,
                    acquisition_pick=None, acquisition_team=None)
        base.update(kw)
        return SimpleNamespace(**base)

    assert _acquisition_label(p()) is None
    assert _acquisition_label(p(acquisition_type="Draft", acquisition_season=2027, acquisition_round=2,
                                 acquisition_pick=45, acquisition_team="NE")) == "Drafted 2027 · Round 2, Pick 45 (NE)"
    assert _acquisition_label(p(acquisition_type="Free Agent", acquisition_season=2026)) == "FA Signing 2026"
    assert _acquisition_label(p(acquisition_type="Undrafted FA", acquisition_season=2027)) == "Undrafted FA 2027"
    assert _acquisition_label(p(acquisition_type="Trade", acquisition_season=2026, acquisition_team="NYJ")) == "Trade 2026 (from NYJ)"


# --- the full season lifecycle -----------------------------------------------

@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_full_season_honors_lifecycle(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app, _player_card_json, _coach_card_json
    from app.services import season_state, history_store, gameplan_store, coach_store, season_honors
    from app.engine.schedule import N_WEEKS
    from app.core.db import get_session
    from app.models.player import Player
    from sqlmodel import select

    monkeypatch.setattr(history_store, "DEFAULT_PATH", tmp_path / "history.json")
    monkeypatch.setattr(gameplan_store, "DEFAULT_PATH", tmp_path / "gameplans.json")
    history_store.clear_career_stats_cache()
    client = TestClient(app)

    season_state.reset_season()
    season_state.set_user_team("KC")
    for _ in range(N_WEEKS - 1):
        season_state.simulate_current_week()
    sn = season_state.get_season().season_number

    # In-season: a live race (top 10), no Pro Bowl rosters yet, and none of
    # the removed explanatory copy.
    resp = client.get("/awards")
    assert "Awards Race" in resp.text and "Season Awards &mdash; Final" not in resp.text
    assert "Real-time leaderboards" not in resp.text and "General Manager of the Year" not in resp.text
    assert honors_store.get_final_awards(sn) is None
    resp = client.get("/awards?tab=pro-bowl")
    assert "announced after the final regular-season game" in resp.text
    assert "Disclosed simplification" not in resp.text

    season_state.simulate_current_week()  # the last regular-season week
    final = honors_store.get_final_awards(sn)
    assert final is not None
    for key in ("mvp", "opoy", "dpoy", "oroy", "droy", "coty"):
        assert len(final[key]) <= awards.AWARDS_RACE_TOP_N
    assert len(final["mvp"]) == awards.AWARDS_RACE_TOP_N
    mvp_id = final["mvp"][0]["player_id"]
    assert mvp_id and any(r["award"] == "MVP" for r in honors_store.player_awards(mvp_id))

    pro_bowl = honors_store.get_pro_bowl(sn)
    for conf in ("AFC", "NFC"):
        assert len(pro_bowl[conf]["offense"]) == sum(awards.PRO_BOWL_OFFENSE_STARTER_COUNTS.values())
        assert len(pro_bowl[conf]["defense"]) == sum(awards.PRO_BOWL_DEFENSE_STARTER_COUNTS.values())
        assert pro_bowl[conf]["reserves"]
    pb_qb = pro_bowl["AFC"]["offense"][0]
    assert pb_qb["position"] == "QB" and pb_qb["stat_line"]  # a real season stat line, not OVR-only
    assert any(r["award"] == "Pro Bowl" for r in honors_store.player_awards(pb_qb["player_id"]))

    resp = client.get("/awards")
    assert "Season Awards &mdash; Final" in resp.text
    resp = client.get("/awards?tab=pro-bowl")
    assert "Pro Bowl Roster" in resp.text and "Reserves" in resp.text

    # Finalization is idempotent -- no double Pro Bowl credit.
    assert season_honors.finalize_regular_season(season_state.get_season()) is False
    assert sum(1 for r in honors_store.player_awards(pb_qb["player_id"]) if r["award"] == "Pro Bowl") == 1

    for _ in range(4):
        season_state.simulate_playoff_round()
    season = season_state.get_season()
    sb = honors_store.get_super_bowl(sn)
    assert sb["winner_abbr"] == season.playoffs.champion_abbr
    assert {sb["winner_score"], sb["loser_score"]} <= {sb["home_score"], sb["away_score"]}
    assert sb["mvp"] and sb["mvp"]["team_abbr"] == sb["winner_abbr"] and sb["mvp"]["stat_line"]
    assert sb["afc_champion_abbr"] and sb["nfc_champion_abbr"]
    if sb["mvp"]["player_id"]:
        assert any(r["award"] == "Super Bowl MVP" for r in honors_store.player_awards(sb["mvp"]["player_id"]))

    resp = client.get("/playoffs?view=full")
    assert f"SUPER BOWL {sb['numeral']}" in resp.text and sb["mvp"]["name"] in resp.text
    resp = client.get("/playoffs?view=superbowl")
    assert f"SUPER BOWL {sb['numeral']}" in resp.text

    # Coach card: the winning head coach's title, with its year.
    coach_store.clear_cache()
    winning_hc = next((c for c in coach_store.all_coaches()
                       if c.team_abbr == sb["winner_abbr"] and c.role.value == "HC" and not c.retired), None)
    if winning_hc is not None:
        card = json.loads(_coach_card_json(winning_hc))
        assert any(h.startswith("Super Bowl Champion") and str(sb["year"]) in h for h in card["honors"])

    # Player card: award history shows up with years.
    with get_session() as s:
        mvp_player = s.get(Player, mvp_id)
    card = json.loads(_player_card_json(mvp_player))
    assert any(h.startswith("MVP") and str(sb["year"]) in h for h in card["honors"])


    season_state.begin_offseason()
    headlines = season_honors.offseason_headlines(sn)
    # Offseason recap lines have no per-event user-team split (they're not
    # produced by the HeadlineEvent pipeline) -- record_offseason_headlines
    # stores them all under "league".
    assert headlines and "Super Bowl" in headlines["league"][0]
    resp = client.get("/dashboard")
    assert headlines["league"][0].split(",")[0] in resp.text

    # Archived League History uses the frozen awards.
    archived = [r for r in history_store.get_history() if r.season_number == sn][0]
    assert archived.awards.mvp[0].name == final["mvp"][0]["name"]

    # Mid-offseason: the season summary already renders (no movement recap yet).
    resp = client.get("/offseason/recap")
    assert resp.status_code == 200
    assert "Super Bowl Champion" in resp.text and "Conference Champions" in resp.text
    assert "is saved once the draft finishes" in resp.text
    user_pro_bowlers = [p for conf in pro_bowl.values() for side in conf.values() for p in side if p["team_abbr"] == "KC"]
    if user_pro_bowlers:
        assert '<tr class="honors-user-row">' in resp.text

    with get_session() as s:
        before_ids = {p.player_id for p in s.exec(select(Player))}
    season_state.advance_offseason_stage()
    season_state.finish_offseason()

    retired = honors_store.get_retired_players(sn)
    assert retired is not None and len(retired) > 0
    with get_session() as s:
        live = list(s.exec(select(Player)))
    after_ids = {p.player_id for p in live}
    assert all(r["player_id"] in before_ids and r["player_id"] not in after_ids for r in retired)
    # Retirement never leaves a team unable to field its minimum roster.
    from collections import Counter
    from app.data.teams import TEAMS
    from app.engine.free_agency import MIN_ROSTER_COUNTS
    counts = Counter((p.team_abbr, p.position) for p in live if p.team_abbr)
    short = [(t.abbr, pos) for t in TEAMS for pos, n in MIN_ROSTER_COUNTS.items() if counts[(t.abbr, pos)] < n]
    assert short == []

    resp = client.get("/offseason/recap")
    from markupsafe import escape
    assert "Retired Players" in resp.text and str(escape(retired[0]["name"])) in resp.text


def test_retirement_never_strands_a_team_below_its_minimum_roster(monkeypatch):
    from types import SimpleNamespace
    from app.services import season_honors
    from app.services.season_honors import _protect_minimum_rosters
    from app.engine import free_agency

    # A one-team league needing just 1 P and 2 WR, so the test is only about KC.
    monkeypatch.setattr(season_honors, "TEAMS_BY_ABBR", {"KC": None})
    monkeypatch.setattr(free_agency, "MIN_ROSTER_COUNTS", {Position.P: 1, Position.WR: 2})

    def pl(pid, team, pos, ovr=70):
        return SimpleNamespace(player_id=pid, team_abbr=team, position=pos, overall_rating=ovr)

    kc_punter = pl("kc_p", "KC", Position.P)
    kc_backup_wr = pl("kc_wr3", "KC", Position.WR)
    on_team = [kc_punter, pl("kc_wr1", "KC", Position.WR), pl("kc_wr2", "KC", Position.WR), kc_backup_wr]
    fa_punter = pl("fa_p", None, Position.P)

    # KC's only punter rolls retirement and the only free-agent punter
    # rolls it too: the free agent stays (he's the replacement), KC's
    # punter can go, and the third WR can go (two remain).
    leaving = _protect_minimum_rosters(on_team, [fa_punter], [kc_punter, kc_backup_wr], [fa_punter])
    ids = {p.player_id for p in leaving}
    assert "kc_wr3" in ids and "kc_p" in ids and "fa_p" not in ids

    # With no free-agent punter at all, KC's punter plays another year.
    leaving = _protect_minimum_rosters(on_team, [], [kc_punter], [])
    assert leaving == []