import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import (
    season_state, save_service, gameplan_store, history_store, power_rank_history,
    award_race_history, headlines_history, draft_class_store, draft_board_store, draft_progress_store,
    roster_prep,
)
from app.engine.schedule import generate_season_schedule, N_WEEKS
from app.data.teams import TEAMS

client = TestClient(app)

# Tests must never touch the live app's real save file (data/saves/current_season.json)
# -- that would clobber whatever a real browser session has in progress. Redirect to a
# throwaway path for the duration of this test module.
save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_season.json")
gameplan_store.DEFAULT_PATH = Path("data/saves/_test_gameplans.json")
# Also redirect history_store: season_state._build_season() now reads it (a fresh
# franchise's season_number bootstraps to AFTER whatever's archived, see
# season_state._bootstrap_season_number()) -- without this, tests here would read the
# REAL data/saves/history.json and get a non-zero, environment-dependent season_number,
# breaking the season_number=0 assumption several of these tests make.
history_store.DEFAULT_PATH = Path("data/saves/_test_season_history.json")
# ROADMAP.md Sec2d-B item 10: simulate_current_week() now writes a weekly
# Power Ranking snapshot too -- same isolation reasoning as the paths above.
power_rank_history.DEFAULT_PATH = Path("data/saves/_test_season_power_ranks.json")
# Same reasoning: simulate_current_week() also writes a real weekly Awards-
# Race snapshot and real Weekly Headlines every call -- this module runs
# full/partial seasons dozens of times, and without this redirect every
# one of those writes would land in the live app's real award_race_history.json/
# headlines_history.json (both keyed by season_number, so a test season's
# always-season-0 writes could clobber the real franchise's own archived
# season 0 if it has one -- found via a real, if inert, instance of exactly
# this during this feature's own test run).
award_race_history.DEFAULT_PATH = Path("data/saves/_test_season_award_race.json")
headlines_history.DEFAULT_PATH = Path("data/saves/_test_season_headlines.json")
# Brian's ask, 2026-09-13: _build_season() now ALSO generates + persists
# next season's real draft class (draft_class_store) every single time
# it runs -- same isolation reasoning as every store above, or every
# reset_season() call in this file would write into the live app's real
# data/saves/draft_classes.json, keyed by a season_number that could
# collide with a real franchise's own pending class.
draft_class_store.DEFAULT_PATH = Path("data/saves/_test_season_draft_classes.json")
draft_board_store.DEFAULT_PATH = Path("data/saves/_test_season_draft_board.json")
draft_progress_store.DEFAULT_PATH = Path("data/saves/_test_season_draft_progress.json")


def setup_function(_):
    # Each test gets a fresh season so they don't interact via shared module state.
    history_store.DEFAULT_PATH.unlink(missing_ok=True)
    season_state.reset_season()
    gameplan_store.DEFAULT_PATH.unlink(missing_ok=True)
    power_rank_history.DEFAULT_PATH.unlink(missing_ok=True)
    award_race_history.DEFAULT_PATH.unlink(missing_ok=True)
    headlines_history.DEFAULT_PATH.unlink(missing_ok=True)
    draft_class_store.DEFAULT_PATH.unlink(missing_ok=True)
    draft_board_store.DEFAULT_PATH.unlink(missing_ok=True)
    draft_progress_store.DEFAULT_PATH.unlink(missing_ok=True)


def test_schedule_shape():
    """Verifies the real GDD opponent formula (Part 1 Sec 5.1): 18 weeks,
    17 games per team against 14 distinct opponents (6 divisional games
    are the doubled leg against 3 division mates), exactly one bye per
    team, no team double-booked in a week. Bye-week *timing* is not
    constrained to weeks 5-14 -- see app/engine/schedule.py's docstring
    for why that's a deliberate simplification, not a bug."""
    from collections import defaultdict

    schedule = generate_season_schedule(2025, season_number=0)
    assert len(schedule) == N_WEEKS == 18

    opponents = defaultdict(set)
    games_played = defaultdict(int)
    weeks_played = defaultdict(set)
    total_games = 0
    for week_num, week in enumerate(schedule, start=1):
        teams_this_week = [t for pair in week for t in pair]
        assert len(teams_this_week) == len(set(teams_this_week)), "team double-booked in one week"
        for home, away in week:
            total_games += 1
            games_played[home] += 1
            games_played[away] += 1
            opponents[home].add(away)
            opponents[away].add(home)
            weeks_played[home].add(week_num)
            weeks_played[away].add(week_num)

    assert total_games == len(TEAMS) * 17 // 2 == 272
    for t in TEAMS:
        assert games_played[t.abbr] == 17, f"{t.abbr} played {games_played[t.abbr]} games, expected 17"
        assert len(opponents[t.abbr]) == 14, f"{t.abbr} faced {len(opponents[t.abbr])} distinct opponents, expected 14"
        bye_weeks = set(range(1, N_WEEKS + 1)) - weeks_played[t.abbr]
        assert len(bye_weeks) == 1, f"{t.abbr} has {len(bye_weeks)} bye weeks, expected exactly 1"


def test_schedule_opponent_formula_breakdown():
    """Every team's 17 games break down as 6 divisional + 4 intra-conference
    rotation + 4 inter-conference rotation + 2 standings-based + 1
    seventeenth game, per the GDD formula -- checked against the raw game
    list before week-placement, since that's what encodes each game's
    source."""
    from app.engine.schedule import _generate_games, _bootstrap_prior_standings
    from collections import defaultdict

    prior = _bootstrap_prior_standings()
    games = _generate_games(0, prior)
    by_team_source = defaultdict(lambda: defaultdict(int))
    for g in games:
        by_team_source[g.home][g.source] += 1
        by_team_source[g.away][g.source] += 1

    for t in TEAMS:
        counts = by_team_source[t.abbr]
        assert counts["DIV"] == 6
        assert counts["INTRA_ROT"] == 4
        assert counts["INTER_ROT"] == 4
        assert counts["INTRA_PLACE"] == 2
        assert counts["INTER_PLACE_17"] == 1
        assert sum(counts.values()) == 17


def test_schedule_generation_is_deterministic():
    a = generate_season_schedule(2025, season_number=0)
    b = generate_season_schedule(2025, season_number=0)
    assert a == b


def test_schedule_generation_reliable_across_many_seeds():
    """The week-placement search (app/engine/schedule.py's
    _try_place_attempt) has internal randomness and isn't guaranteed to
    succeed on a given attempt -- it retries with different seeds until
    one works. This checks that it actually does converge, and stays
    fast, across a spread of league seeds and season numbers, not just
    the one or two used in the other tests above."""
    import time

    t0 = time.time()
    for seed in [1, 2, 3, 100, 2025, 999999]:
        for season_number in [0, 1, 2, 3]:
            schedule = generate_season_schedule(seed, season_number=season_number)
            assert len(schedule) == N_WEEKS
            total = sum(len(week) for week in schedule)
            assert total == 272
    elapsed = time.time() - t0
    assert elapsed < 30, f"schedule generation took {elapsed:.1f}s for 24 combinations -- too slow"


def test_season_page_loads():
    resp = client.get("/season")
    assert resp.status_code == 200
    assert "Week 1" in resp.text


def test_simulate_week_advances_and_updates_standings():
    season_state.simulate_preseason()  # clear the preseason first -- Sim Week plays that before Week 1
    resp = client.post("/season/simulate-week", follow_redirects=True)
    assert resp.status_code == 200
    assert "Week 2" in resp.text
    season = season_state.get_season()
    total_wins = sum(r.wins for r in season.records.values())
    total_losses = sum(r.losses for r in season.records.values())
    assert total_wins == 16  # one winner per game, 16 games in week 1
    assert total_wins == total_losses


def test_full_season_completes():
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    season = season_state.get_season()
    assert season.is_complete
    # 17 games per team (not N_WEEKS=18) -- each team has exactly one bye week.
    total_games = sum(r.wins + r.losses for r in season.records.values())
    assert total_games == len(TEAMS) * 17


def test_reset_clears_results():
    season_state.simulate_current_week()
    season_state.reset_season()
    season = season_state.get_season()
    assert season.current_week == 1
    assert all(r.wins == 0 and r.losses == 0 for r in season.records.values())


def test_save_load_round_trip_preserves_results_and_events():
    season_state.simulate_current_week()
    season_state.simulate_current_week()
    original = season_state.get_season()

    save_service.save_season(original)
    reloaded = save_service.load_season()

    assert reloaded.league_seed == original.league_seed
    assert reloaded.current_week == original.current_week
    for abbr in original.records:
        assert reloaded.records[abbr] == original.records[abbr]

    orig_game = original.schedule[0][0]
    reloaded_game = reloaded.schedule[0][0]
    assert reloaded_game.home_abbr == orig_game.home_abbr
    assert reloaded_game.result.home_score == orig_game.result.home_score
    assert reloaded_game.result.away_score == orig_game.result.away_score
    assert len(reloaded_game.result.events) == len(orig_game.result.events)
    assert reloaded_game.result.events[0].desc == orig_game.result.events[0].desc

    assert reloaded.sfs == original.sfs


def test_simulating_weeks_moves_power_ratings_off_the_baseline():
    """Score Fidelity System (GDD Sec 7.2): Team Power Ratings start at
    the league baseline (1500) and should diverge as real results come
    in -- a season where every team is stuck at exactly 1500 after
    several weeks would mean the Elo update never actually ran."""
    from app.engine import power_rating

    for _ in range(4):
        season_state.simulate_current_week()
    season = season_state.get_season()
    ratings = [r.power_rating for r in season.records.values()]
    assert any(r != power_rating.INITIAL_RATING for r in ratings)


def test_weekly_feedback_telemetry_accumulates_one_entry_per_simulated_week():
    for week in range(1, 4):
        season_state.simulate_current_week()
        season = season_state.get_season()
        assert len(season.sfs.telemetry) == week
        assert season.sfs.telemetry[-1]["week"] == week


def test_season_survives_a_simulated_restart():
    """Simulates a server restart: clear the in-memory season, then confirm
    get_season() loads the persisted one instead of silently generating a
    brand new (different) season."""
    season_state.simulate_current_week()
    before = season_state.get_season()
    before_week = before.current_week
    before_standings = [(r.abbr, r.wins, r.losses) for r in before.standings()]

    season_state._season = None  # simulate process restart losing in-memory state

    after = season_state.get_season()
    assert after.current_week == before_week
    after_standings = [(r.abbr, r.wins, r.losses) for r in after.standings()]
    assert after_standings == before_standings


def test_concurrent_simulate_week_calls_dont_corrupt_state():
    """Regression test for a real bug found via live manual testing: a team
    ended up 20-0 with current_week at 21 in an 18-week season.
    /season/simulate-week is a plain `def` route, thread-pooled by FastAPI,
    so concurrent requests (a double-click, a slow request retried, a page
    reload resubmitting the form) could genuinely race: two threads both
    read the same current_week before either incremented it, both simulated
    the same week (inflating that week's teams' win/loss counts), and
    current_week could end up past N_WEEKS entirely. season_state._STATE_LOCK
    fixes this by fully serializing every mutating call -- fire way more
    concurrent calls than there are weeks and confirm the season still ends
    up in an exactly-correct state, not merely a plausible-looking one."""
    import threading

    n_threads = 25  # more than N_WEEKS=18, so some calls MUST safely no-op post-completion
    barrier = threading.Barrier(n_threads)

    def hammer():
        barrier.wait()  # start all threads at (as close to) the same instant as possible
        season_state.simulate_current_week()

    threads = [threading.Thread(target=hammer) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    season = season_state.get_season()
    assert season.is_complete
    assert season.current_week == N_WEEKS + 1  # never past this, no matter how many extra calls raced in
    for r in season.records.values():
        assert r.wins + r.losses == 17, f"{r.abbr} played {r.wins + r.losses} games, not the scheduled 17"
    total_games = sum(r.wins + r.losses for r in season.records.values())
    assert total_games == len(TEAMS) * 17


def test_user_team_starts_unset():
    """GDD Sec 10.1: a fresh franchise has no user team until one is
    explicitly chosen -- this is what drives the /dashboard redirect to
    /team-select."""
    assert season_state.get_season().user_team_abbr is None


def test_set_user_team_persists_and_round_trips():
    season_state.set_user_team("KC")
    assert season_state.get_season().user_team_abbr == "KC"

    save_service.save_season(season_state.get_season())
    reloaded = save_service.load_season()
    assert reloaded.user_team_abbr == "KC"


def test_set_user_team_rejects_unknown_team():
    import pytest
    with pytest.raises(ValueError):
        season_state.set_user_team("ZZZ")
    assert season_state.get_season().user_team_abbr is None


def test_reset_season_clears_user_team():
    """GDD Sec 10.1: there's no mid-season re-pick -- starting a new
    franchise (reset) is what clears the choice, not a settings toggle."""
    season_state.set_user_team("KC")
    season_state.reset_season()
    assert season_state.get_season().user_team_abbr is None


def test_dashboard_redirects_to_team_select_when_no_team_chosen():
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/team-select"


def test_dashboard_shows_user_team_once_chosen():
    season_state.set_user_team("KC")
    resp = client.get("/dashboard", follow_redirects=True)
    assert resp.status_code == 200
    assert "Kansas City" in resp.text
    assert "AFC West" in resp.text


def test_persistent_header_shows_team_badge_and_sim_week_on_every_page_once_chosen():
    """GDD Sec 10.3: a persistent header (team badge, record/division/
    power-rank, a Sim Week control) visible on EVERY screen, not just
    Dashboard -- app.main._header_context(), registered as a Jinja2
    global so base.html can call it directly without every route
    threading the same values through its own context dict."""
    season_state.set_user_team("KC")
    for path in ("/roster", "/stats", "/staff", "/history"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "Kansas City (KC)" in resp.text
        assert "Sim Week" in resp.text


def test_persistent_header_falls_back_to_plain_title_before_a_team_is_chosen():
    resp = client.get("/team-select")
    assert resp.status_code == 200
    assert "Sim Week" not in resp.text
    assert "Franchise" in resp.text and "Football" in resp.text


def test_safe_internal_redirect_rejects_external_and_protocol_relative_urls():
    """_safe_internal_redirect guards the persistent header's Sim Week
    form (redirect_to is a hidden field echoing request.url.path) against
    being turned into an open redirect by a crafted form submission --
    only a genuine internal path is ever honored."""
    from app.main import _safe_internal_redirect

    assert _safe_internal_redirect("/roster", "/season") == "/roster"
    assert _safe_internal_redirect(None, "/season") == "/season"
    assert _safe_internal_redirect("", "/season") == "/season"
    assert _safe_internal_redirect("https://evil.example.com", "/season") == "/season"
    assert _safe_internal_redirect("//evil.example.com", "/season") == "/season"
    assert _safe_internal_redirect("not-a-path", "/season") == "/season"


def test_sim_week_button_returns_to_the_page_it_was_clicked_from():
    """The whole point of a persistent Sim Week control is that using it
    doesn't lose your place -- confirms the redirect actually goes back
    to redirect_to, not always to /season."""
    season_state.set_user_team("KC")
    # R16 Sec 8: a real import carries 54-72 players per team -- KC needs
    # the same one-time, position-need-aware trim to 53 a fresh-load AI
    # team gets automatically, or the over-53 gate fires here instead of
    # the flow this test checks.
    roster_prep.auto_cut_team_to_limits("KC")
    resp = client.post("/season/simulate-week", data={"redirect_to": "/roster"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/roster"


def test_dashboard_power_rank_ordinal_suffix_handles_11_13_exception():
    """Regression test for a real bug found via live manual testing: a
    fresh 0-0 team's power rank rendered as "22th" instead of "22nd" --
    the template's ordinal logic only special-cased exact ranks 1/2/3,
    not the mod-10 pattern (nor the 11th-13th exception to it). Checks
    app.main._ordinal directly since which literal rank a team lands at
    depends on standings tie-break order, not something to hardcode
    against the live season."""
    from app.main import _ordinal
    assert _ordinal(1) == "1st"
    assert _ordinal(2) == "2nd"
    assert _ordinal(3) == "3rd"
    assert _ordinal(4) == "4th"
    assert _ordinal(11) == "11th"
    assert _ordinal(12) == "12th"
    assert _ordinal(13) == "13th"
    assert _ordinal(21) == "21st"
    assert _ordinal(22) == "22nd"
    assert _ordinal(23) == "23rd"
    assert _ordinal(32) == "32nd"


def test_team_select_post_sets_team_and_redirects_to_dashboard():
    resp = client.post("/team-select", data={"team_abbr": "BUF"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"
    assert season_state.get_season().user_team_abbr == "BUF"


def test_team_select_post_rejects_unknown_team():
    resp = client.post("/team-select", data={"team_abbr": "ZZZ"})
    assert resp.status_code == 404


def test_roster_and_depth_chart_default_to_user_team():
    season_state.set_user_team("KC")
    roster_resp = client.get("/roster", follow_redirects=True)
    assert roster_resp.status_code == 200
    assert "Kansas City" in roster_resp.text

    depth_resp = client.get("/depth-chart", follow_redirects=True)
    assert depth_resp.status_code == 200
    assert "Kansas City" in depth_resp.text


def test_find_player_results_are_sortable_by_column():
    """R11 (GDD Sec 11, "Roster - Find Player & Free Agents"): Find
    Player's results reuse ROSTER_SORT_KEYS, the same GET-param sort
    convention the main Roster table already uses -- confirms a real
    re-order actually happens (not just an accepted-but-ignored param)."""
    import re

    season_state.set_user_team("KC")
    # find_min_ovr=0 is a real, always-true filter (every OVR is >= 0) --
    # activates find_active and matches the whole league without needing
    # a specific name to search for.
    default_resp = client.get("/roster?find_min_ovr=0")
    assert default_resp.status_code == 200
    find_section = default_resp.text[default_resp.text.index('id="find-player-box"'):]
    default_ovrs = [int(x) for x in re.findall(r"OVR (\d+)", find_section)]
    assert len(default_ovrs) > 1
    assert default_ovrs == sorted(default_ovrs, reverse=True)  # unset find_sort still defaults to OVR desc

    asc_resp = client.get("/roster?find_min_ovr=0&find_sort=age&find_dir=asc")
    assert asc_resp.status_code == 200
    asc_section = asc_resp.text[asc_resp.text.index('id="find-player-box"'):]
    asc_ages = [int(x) for x in re.findall(r"Age (\d+)", asc_section)]
    assert len(asc_ages) > 1
    assert asc_ages == sorted(asc_ages)
    assert asc_ages != default_ovrs  # sanity: a real, different ordering was exercised

    # "dep" needs each result's OWN team's depth chart (_depth_slot_across_teams),
    # not just the currently-browsed team's -- confirm it doesn't error across
    # a result set spanning many different teams.
    dep_resp = client.get("/roster?find_min_ovr=0&find_sort=dep&find_dir=asc")
    assert dep_resp.status_code == 200


def test_find_player_and_free_agents_rows_have_inline_detail_widget():
    """R11: both boxes grow a shared tabbed detail view (Overview/Ratings/
    Stats/Contract, reusing the Player Card's own tab markup) instead of
    only the full modal; Free Agents rows additionally get a 5th
    "Contract Sought" tab (a Global MVP "Coming Soon" shell, GDD Sec
    9.2.8) that Find Player rows correctly do NOT get."""
    season_state.set_user_team("KC")
    resp = client.get("/roster?find_min_ovr=0")
    assert resp.status_code == 200
    fa_section = resp.text[resp.text.index('id="free-agents-box"'):resp.text.index('id="find-player-box"')]
    find_section = resp.text[resp.text.index('id="find-player-box"'):]

    assert 'data-row-toggle' in fa_section
    assert 'class="row-detail-panel" data-show-contract-sought="1"' in fa_section

    assert 'data-row-toggle' in find_section
    assert 'data-show-contract-sought' not in find_section


def test_dashboard_renders_weekly_gameplan_form_with_defaults():
    from app.engine.gameplan import Gameplan

    season_state.set_user_team("KC")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Weekly Gameplan" in resp.text
    # Default Gameplan() values should be pre-selected.
    default = Gameplan()
    assert f'value="{default.offensive_aggressiveness}" selected' in resp.text
    assert f'value="{default.coverage}" selected' in resp.text


def test_gameplan_post_saves_and_reflects_on_dashboard():
    season_state.set_user_team("KC")
    resp = client.post("/gameplan", data={
        "offensive_aggressiveness": "Very Aggressive",
        "defensive_aggressiveness": "Very Aggressive",
        "coverage": "Man-Heavy",
        "blitz": "Blitz Heavy",
        "rz_offense": "Spread/Shot",
        "rz_defense": "Pressure QB",
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"

    from app.engine.gameplan import Gameplan
    saved = gameplan_store.get_gameplan("KC")
    assert saved == Gameplan(
        offensive_aggressiveness="Very Aggressive",
        defensive_aggressiveness="Very Aggressive",
        coverage="Man-Heavy",
        blitz="Blitz Heavy",
        rz_offense="Spread/Shot",
        rz_defense="Pressure QB",
    )

    dashboard = client.get("/dashboard")
    assert 'value="Very Aggressive" selected' in dashboard.text
    assert 'value="Man-Heavy" selected' in dashboard.text


def test_gameplan_post_rejects_invalid_value():
    season_state.set_user_team("KC")
    resp = client.post("/gameplan", data={
        "offensive_aggressiveness": "Not A Real Option",
        "defensive_aggressiveness": "Balanced",
        "coverage": "Hybrid",
        "blitz": "Standard",
        "rz_offense": "Balanced",
        "rz_defense": "Balanced",
    })
    assert resp.status_code == 422


def test_gameplan_post_requires_a_chosen_team():
    resp = client.post("/gameplan", data={
        "offensive_aggressiveness": "Balanced",
        "defensive_aggressiveness": "Balanced",
        "coverage": "Hybrid",
        "blitz": "Standard",
        "rz_offense": "Balanced",
        "rz_defense": "Balanced",
    })
    assert resp.status_code == 404


def test_draft_renders_coming_soon():
    """GDD Sec 10.3's MVP navigation behavior: this nav item exists and
    renders a real Coming Soon message, not a 404.

    /staff and /gm-desk used to be in this list and no longer are -- both
    became real pages (ROADMAP.md R3/Sec 4c for Staff, R4a/Sec 8.3 for
    GM Desk's Cap Summary + Re-sign flow), so asserting either still says
    "Coming soon" would now be asserting a regression. Their own real
    coverage is test_staff_page_is_real_not_a_stub and
    test_gm_desk_is_real_not_a_stub below (plus the whole of
    tests/test_coaching.py and tests/test_contracts.py). Draft is still a
    genuine stub (it needs R5)."""
    resp = client.get("/draft")
    assert resp.status_code == 200
    assert "Draft" in resp.text
    assert "Coming soon" in resp.text


def test_gm_desk_is_real_not_a_stub():
    """ROADMAP.md R4a: /gm-desk renders a real Cap Summary (a real dollar
    figure for cap space, not a placeholder) once a team is chosen."""
    season_state.set_user_team("KC")
    resp = client.get("/gm-desk")
    assert resp.status_code == 200
    assert "Coming soon" not in resp.text
    assert "Cap Space" in resp.text


def test_gm_desk_trade_panel_shows_real_tradeable_picks():
    """Draft-Pick Trading (GDD Sec 8.5): the Propose Trade panel lists
    real, currently-owned picks for both sides, not just players."""
    season_state.reset_season()
    season_state.set_user_team("KC")
    resp = client.get("/gm-desk?team_b=BUF")
    assert resp.status_code == 200
    assert "1st Round Pick" in resp.text  # the user's own next-draft 1st, at minimum


def test_gm_desk_cap_uses_the_reanchored_season_cap():
    """Brian: "Salary cap is still showing as $700M." Every cap figure on
    GM Desk comes from contracts.salary_cap_for_season() -- $450M in 2026."""
    from app.config import season_year
    from app.engine import contracts

    season_state.reset_season()
    season_state.set_user_team("KC")
    season = season_state.get_season()
    original_number = season.season_number
    # A new save's first season is 2026 (season_number 24); the test
    # fixture's reset_season() builds an earlier number, so pin it here.
    season.season_number = 24
    try:
        assert season_year(season.season_number) == 2026
        assert contracts.salary_cap_for_season(season.season_number) == 450_000_000
        resp = client.get("/gm-desk")
        assert resp.status_code == 200
        assert '<div style="font-size: 1.4rem;" id="gm-cap">$450,000,000</div>' in resp.text
        assert "Payroll" in resp.text and "of $450,000,000 cap" in resp.text
        assert "$700,000,000" not in resp.text
    finally:
        season.season_number = original_number


def test_gm_desk_trade_box_always_shows_the_user_roster_before_a_partner_is_picked():
    from app.core.db import get_session
    from app.models.player import Player
    from sqlmodel import select

    season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        kc_player = s.exec(select(Player).where(Player.team_abbr == "KC")).first()
    resp = client.get("/gm-desk")
    assert resp.status_code == 200
    assert 'id="trade-user-side"' in resp.text
    assert f'data-asset-id="{kc_player.player_id}"' in resp.text
    assert "Choose a team above" in resp.text
    # Trade Block filter pills + Expiring Contracts' POT column.
    assert 'data-tb-filter="OFF"' in resp.text and 'data-tb-filter="DEF"' in resp.text
    assert 'data-sort="pot"' in resp.text


def test_gm_desk_trade_side_fragment_includes_roster_picks_and_wants():
    season_state.reset_season()
    season_state.set_user_team("KC")
    resp = client.get("/gm-desk/trade/side?team=BUF")
    assert resp.status_code == 200
    data = resp.json()
    assert 'data-side="get"' in data["html"]
    assert "Round Pick" in data["html"]
    assert data["wants"]["mode_line"]
    assert isinstance(data["wants"]["needs"], list)


def test_gm_desk_trade_ajax_submit_returns_a_verdict_and_records_acquisition():
    """The rebuilt Propose Trade box submits via fetch (ajax=1) and renders
    the verdict in place; an accepted trade stamps every moved player's
    acquisition record."""
    from app.config import season_year
    from app.core.db import get_session
    from app.engine import trades
    from app.models.player import Player
    from sqlmodel import select

    season_state.reset_season()
    season_state.set_user_team("KC")
    season = season_state.get_season()
    with get_session() as s:
        kc = sorted(s.exec(select(Player).where(Player.team_abbr == "KC")).all(), key=lambda p: -p.overall_rating)
        buf = sorted(s.exec(select(Player).where(Player.team_abbr == "BUF")).all(), key=lambda p: p.overall_rating)
    # A lopsided deal in the AI's favor (KC's best for BUF's worst) should be accepted.
    give, get = kc[0], buf[0]

    preview = client.get("/gm-desk/trade/preview", params={"team_b": "BUF", "give": [give.player_id], "get": [get.player_id]})
    assert preview.status_code == 200
    pdata = preview.json()
    assert 0 <= pdata["likelihood"] <= 100
    assert pdata["reason"]

    resp = client.post("/gm-desk/trade", data={"team_b": "BUF", "give": [give.player_id], "get": [get.player_id], "ajax": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == pdata["accepted"]
    assert data["reason"]
    if data["accepted"]:
        assert data["headline"] == "Accepted!"
        assert data["likelihood"] >= trades.ACCEPT_LIKELY
        with get_session() as s:
            moved = s.get(Player, give.player_id)
            came = s.get(Player, get.player_id)
        assert moved.team_abbr == "BUF" and came.team_abbr == "KC"
        assert moved.acquisition_type == "Trade" and moved.acquisition_team == "KC"
        assert came.acquisition_team == "BUF"
        assert moved.acquisition_season == season_year(season.season_number)
    else:
        assert data["headline"] in trades.REJECTION_PHRASES


def test_gm_desk_trade_counter_offer_route():
    from app.core.db import get_session
    from app.models.player import Player
    from sqlmodel import select

    season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        buf_best = max(s.exec(select(Player).where(Player.team_abbr == "BUF")).all(), key=lambda p: p.overall_rating)
    resp = client.get("/gm-desk/trade/counter", params={"team_b": "BUF", "get": [buf_best.player_id]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"]
    if data["possible"] and not data["already_acceptable"]:
        assert data["add_give"] or data["add_give_picks"]
        follow = client.get("/gm-desk/trade/preview", params={
            "team_b": "BUF", "get": [buf_best.player_id], "give": data["add_give"], "give_picks": data["add_give_picks"],
        })
        assert follow.json()["accepted"] is True
    elif not data["possible"]:
        assert data["message"] == "A deal is not possible with those terms."


def test_gm_desk_trade_route_accepts_a_pick_for_pick_swap():
    """A pick-for-pick trade (no players either side) really transfers
    ownership via app/services/draft_pick_store.py once accepted."""
    from app.services import draft_pick_store

    season_state.reset_season()
    season_state.set_user_team("KC")
    season = season_state.get_season()

    kc_pick = draft_pick_store.picks_owned_by("KC")[0]
    buf_pick = draft_pick_store.picks_owned_by("BUF")[0]

    resp = client.post("/gm-desk/trade", data={
        "team_b": "BUF", "give_picks": [kc_pick.pick_id], "get_picks": [buf_pick.pick_id],
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert "trade_result=" in resp.headers["location"]
    # Whether accepted or not, the route must not have crashed -- and if
    # accepted, ownership really moved.
    if "trade_result=ACCEPT" in resp.headers["location"]:
        assert draft_pick_store.owner_of(kc_pick.season_number, kc_pick.round, kc_pick.original_team_abbr) == "BUF"
        assert draft_pick_store.owner_of(buf_pick.season_number, buf_pick.round, buf_pick.original_team_abbr) == "KC"


def test_trade_side_excludes_practice_squad_players():
    """R16 Sec 4.1/decision #15: PS players aren't tradeable -- only
    active-53 and IR are, same as before this feature."""
    from app.core.db import get_session
    from app.models.player import Player, RosterStatus
    from sqlmodel import select

    season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        kc_roster = list(s.exec(select(Player).where(Player.team_abbr == "KC")))
    ps_player = kc_roster[0]
    ir_player = kc_roster[1]
    with get_session() as s:
        p = s.get(Player, ps_player.player_id)
        p.roster_status = RosterStatus.PRACTICE_SQUAD
        s.add(p)
        p2 = s.get(Player, ir_player.player_id)
        p2.roster_status = RosterStatus.IR
        s.add(p2)
        s.commit()

    side_html = client.get("/gm-desk/trade/side", params={"team": "KC"}).json()["html"]
    assert ps_player.player_id not in side_html  # PS is excluded from the tradeable list
    assert ir_player.player_id in side_html      # IR stays tradeable, same as before R16


def test_gm_desk_trade_route_rejects_offering_a_practice_squad_player():
    from app.core.db import get_session
    from app.models.player import Player, RosterStatus
    from sqlmodel import select

    season_state.reset_season()
    season_state.set_user_team("KC")
    with get_session() as s:
        kc = list(s.exec(select(Player).where(Player.team_abbr == "KC")))
        buf_best = max(s.exec(select(Player).where(Player.team_abbr == "BUF")), key=lambda p: p.overall_rating)
    ps_player = kc[0]
    with get_session() as s:
        p = s.get(Player, ps_player.player_id)
        p.roster_status = RosterStatus.PRACTICE_SQUAD
        s.add(p)
        s.commit()

    resp = client.post("/gm-desk/trade", data={
        "team_b": "BUF", "give": [ps_player.player_id], "get": [buf_best.player_id],
    })
    assert resp.status_code == 422


def test_gm_desk_trade_route_rejects_a_pick_not_owned_by_the_offering_team():
    from app.services import draft_pick_store

    season_state.reset_season()
    season_state.set_user_team("KC")

    someone_elses_pick = draft_pick_store.picks_owned_by("BUF")[0]  # KC does NOT own this
    sf_pick = draft_pick_store.picks_owned_by("SF")[0]
    resp = client.post("/gm-desk/trade", data={
        "team_b": "SF", "give_picks": [someone_elses_pick.pick_id], "get_picks": [sf_pick.pick_id],
    })
    assert resp.status_code == 404


def test_staff_page_is_real_not_a_stub():
    """ROADMAP.md R3: /staff renders the real coaching staff -- the head
    coach by name, the Trait Effects panel showing the actual sim biases
    that staff produces, and a clickable Coach Card blob. Skips cleanly
    on a database with no coaches imported, which is the one case the
    page legitimately still shows a coming-soon message for."""
    from app.services import coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported into this database")

    season_state.set_user_team("KC")
    resp = client.get("/staff")
    assert resp.status_code == 200
    assert "Coming soon" not in resp.text
    assert "Trait Effects" in resp.text
    assert "data-coach-card=" in resp.text

    head_coach = coach_store.head_coach("KC")
    assert head_coach is not None
    assert head_coach.full_name in resp.text
    # The generated-vs-real disclosure must be on the page, not just in a
    # docstring -- it's the whole reason the generated ratings are
    # acceptable to show at all. It moved from a page-level summary
    # paragraph (removed 2026-09-13, Brian's "too busy" report -- the top
    # card is now just a team picker) into each real coach's own
    # data-coach-card blob (_coach_card_json()'s own "generated_note"
    # field), which is arguably the more relevant place for it anyway.
    assert "deterministically generated" in resp.text


def test_scouting_panel_shows_a_real_head_coach_not_the_placeholder():
    """ROADMAP.md Sec2d item 3 shipped a literal "Coach Name" placeholder
    because no Coach entity existed. R3 replaced it with the real one --
    this asserts the placeholder string is genuinely gone."""
    from app.services import coach_store
    if not coach_store.has_coaches():
        pytest.skip("no coaches imported into this database")

    season_state.set_user_team("KC")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Coach Name" not in resp.text
    assert "Head Coach" in resp.text


def test_simulate_current_week_records_a_power_rank_snapshot():
    """ROADMAP.md Sec2d-B item 10: the Dashboard's Power Rankings CHG
    column needs a real persisted snapshot to diff against -- confirms
    simulate_current_week() actually writes one, with the same
    power_rating-descending order the Dashboard itself sorts by."""
    season_state.simulate_current_week()
    season = season_state.get_season()

    expected_ranks = {
        r.abbr: i for i, r in enumerate(
            # 2026-09-14: ranked by rating + record anchor (power_rating.power_score_for).
            sorted(season.records.values(), key=lambda r: -__import__("app.engine.power_rating", fromlist=["x"]).power_score_for(r)), start=1
        )
    }
    stored = power_rank_history.get_ranks(season.season_number, 1)
    assert stored == expected_ranks


def test_power_rank_snapshot_has_no_delta_available_on_the_first_tracked_week():
    """Week 1 has no "week 0" snapshot to diff against -- the Dashboard
    route must treat this as "no delta yet," not fabricate one."""
    season_state.simulate_current_week()
    season = season_state.get_season()
    assert power_rank_history.get_ranks(season.season_number, 0) is None


def test_dashboard_power_rankings_show_a_real_delta_after_two_simulated_weeks():
    """First simulated week has nothing to diff against (delta is None,
    not a fabricated arrow); the second week's Dashboard render should
    show a real delta for at least one team, since Elo-style power
    ratings essentially never produce a perfect rank tie across 32 teams
    two weeks running."""
    season_state.set_user_team("KC")
    season_state.simulate_current_week()
    season_state.simulate_current_week()
    season = season_state.get_season()

    week1_ranks = power_rank_history.get_ranks(season.season_number, 1)
    week2_ranks = power_rank_history.get_ranks(season.season_number, 2)
    assert week1_ranks is not None and week2_ranks is not None
    assert any(week1_ranks[abbr] != week2_ranks[abbr] for abbr in week1_ranks)

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Power Rankings" in resp.text


def test_dashboard_standings_box_has_afc_nfc_tabs_and_all_divisions_stacked():
    """ROADMAP.md Sec2d-B item 9 originally had AFC/NFC top-level tabs with
    a SECOND East/North/South/West tab row underneath; the Sec2c follow-up
    round (2026-09-10) removed that second tab layer as mostly dead space
    (only one division's table visible at a time in a card already sized
    for the whole conference) in favor of all four divisions stacked under
    their own sub-header inside each conference panel -- confirms all 8
    real groups still render (not just the user's own division), just via
    `.standings-division-header`s now instead of a second tab row. Updated
    2026-09-11: the original assertion (`data-tab="{division}"`) checked
    for the removed tab row and had gone stale against that redesign,
    flagged but left unfixed by two other concurrent sessions' own work
    this same day -- fixed here while finalizing everything together."""
    season_state.set_user_team("KC")  # AFC West
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Standings" in resp.text
    for conf in ("AFC", "NFC"):
        assert f'data-tab="{conf}"' in resp.text
    for division in ("East", "North", "South", "West"):
        assert f'class="standings-division-header">{division}<' in resp.text
    # Kansas City (AFC West) should appear in the standings data somewhere.
    assert "Kansas City (KC)" in resp.text


def test_dashboard_top_performers_has_category_dropdown_and_conference_tabs():
    """ROADMAP.md Sec2d-B item 11: a real stat-category dropdown (reusing
    the same per-player season aggregates the Stats page already
    computes) plus an AFC/NFC/All toggle styled like the Standings tabs,
    not Figma's own small inline dropdown."""
    season_state.set_user_team("KC")
    season_state.simulate_current_week()
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Top Performers" in resp.text
    assert 'class="tp-category-select"' in resp.text
    assert "QB Rating" in resp.text and "Passing Yards" in resp.text
    for conf in ("ALL", "AFC", "NFC"):
        assert f'data-conf="{conf}"' in resp.text


def test_dashboard_headlines_box_replaces_old_header_and_shows_real_content_once_a_week_is_played():
    """ROADMAP.md Sec2c items 1-2 originally replaced the old "Dashboard —
    Season N..." header with a Headlines box that rendered a "Coming
    soon" placeholder (R9/GDD Sec12 wasn't built yet). R9 landed
    2026-09-13 as a real, deterministic (no LLM) feature -- see
    app/engine/headlines.py's own module docstring -- so the box now
    shows either a real "no headlines yet" empty state (before Week 1
    finishes) or real rendered storylines after. Updated here instead of
    left asserting stale placeholder text, same discipline as every
    other stale-test fix tonight."""
    season_state.set_user_team("KC")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Headlines" in resp.text
    assert "No headlines yet" in resp.text  # before Week 1 has been simulated
    assert "<h2>Dashboard" not in resp.text

    season_state.simulate_current_week()
    resp = client.get("/dashboard")
    assert "headlines-list" in resp.text  # real rendered storylines now, not the empty state


def test_dashboard_gameplan_filler_subtext_removed():
    """ROADMAP.md Sec2c item 4: strip GDD-citation-style filler captions
    from dashboard widgets -- Weekly Gameplan's own field tooltips already
    explain each setting."""
    season_state.set_user_team("KC")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Weekly Gameplan" in resp.text
    assert "Sets your Head Coach's strategy" not in resp.text


# --- R10: Preseason ----------------------------------------------------------

def test_generate_preseason_schedule_shape():
    """4 real rounds, every team appearing exactly once per round (no
    double-booking) and playing exactly 4 distinct real opponents total."""
    from app.engine.schedule import generate_preseason_schedule
    from collections import defaultdict

    schedule = generate_preseason_schedule(2025, season_number=0)
    assert len(schedule) == 4

    opponents = defaultdict(set)
    games_played = defaultdict(int)
    for round_games in schedule:
        teams_this_round = [t for pair in round_games for t in pair]
        assert len(teams_this_round) == len(set(teams_this_round)), "team double-booked in one round"
        assert len(round_games) == len(TEAMS) // 2
        for home, away in round_games:
            games_played[home] += 1
            games_played[away] += 1
            opponents[home].add(away)
            opponents[away].add(home)

    for t in TEAMS:
        assert games_played[t.abbr] == 4
        assert len(opponents[t.abbr]) == 4


def test_generate_preseason_schedule_is_deterministic():
    from app.engine.schedule import generate_preseason_schedule
    a = generate_preseason_schedule(2025, season_number=0)
    b = generate_preseason_schedule(2025, season_number=0)
    assert a == b


def test_a_fresh_season_has_an_unplayed_preseason_schedule():
    season = season_state.get_season()
    assert len(season.preseason_schedule) == 4
    assert season.preseason_rounds_played == 0
    assert not season.preseason_complete
    assert all(g.result is None for round_games in season.preseason_schedule for g in round_games)


def test_simulate_preseason_plays_every_game_and_never_touches_records():
    season = season_state.get_season()
    simulated = season_state.simulate_preseason()

    assert simulated == sum(len(w) for w in season.preseason_schedule)
    assert season.preseason_complete
    assert all(g.result is not None for round_games in season.preseason_schedule for g in round_games)

    # R10's own scope: doesn't count toward standings/Power Rankings anywhere.
    from app.engine import power_rating
    assert all(r.wins == 0 and r.losses == 0 for r in season.records.values())
    assert all(r.points_for == 0 and r.points_against == 0 for r in season.records.values())
    assert all(r.power_rating == power_rating.INITIAL_RATING for r in season.records.values())
    assert season.current_week == 1  # preseason doesn't advance the regular-season clock


def test_simulate_preseason_is_idempotent_once_complete():
    season_state.simulate_preseason()
    second_call_count = season_state.simulate_preseason()
    assert second_call_count == 0


def test_simulate_preseason_route_redirects_to_season():
    resp = client.post("/season/simulate-preseason", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/season"

    season = season_state.get_season()
    assert season.preseason_complete


def test_reset_season_regenerates_a_fresh_unplayed_preseason():
    season_state.simulate_preseason()
    season_state.reset_season()
    season = season_state.get_season()
    assert len(season.preseason_schedule) == 4
    assert not season.preseason_complete


def test_preseason_game_view_renders_after_being_played():
    season_state.simulate_preseason()
    season = season_state.get_season()
    g = season.preseason_schedule[0][0]
    resp = client.get(f"/season/preseason/game/{g.home_abbr}/{g.away_abbr}")
    assert resp.status_code == 200
    assert g.away_abbr in resp.text and g.home_abbr in resp.text


def test_preseason_game_view_404s_before_its_played():
    season = season_state.get_season()
    g = season.preseason_schedule[0][0]
    resp = client.get(f"/season/preseason/game/{g.home_abbr}/{g.away_abbr}")
    assert resp.status_code == 404


def test_preseason_save_load_round_trip():
    season_state.simulate_preseason()
    original = season_state.get_season()
    save_service.save_season(original)
    reloaded = save_service.load_season()

    assert len(reloaded.preseason_schedule) == 4
    orig_game = original.preseason_schedule[0][0]
    reloaded_game = reloaded.preseason_schedule[0][0]
    assert reloaded_game.home_abbr == orig_game.home_abbr
    assert reloaded_game.result.home_score == orig_game.result.home_score
    assert reloaded_game.result.away_score == orig_game.result.away_score


# --- Sim Week driving preseason round-by-round (Brian's ask, 2026-09-13) ----------------

def test_simulate_next_preseason_round_plays_exactly_one_round_at_a_time():
    season = season_state.get_season()
    assert season.preseason_rounds_played == 0

    round_num = season_state.simulate_next_preseason_round()
    assert round_num == 1
    assert season.preseason_rounds_played == 1
    assert all(g.result is not None for g in season.preseason_schedule[0])
    assert all(g.result is None for g in season.preseason_schedule[1])
    # Same "never touches records" rule as simulate_preseason().
    assert all(r.wins == 0 and r.losses == 0 for r in season.records.values())

    for expected_round in (2, 3, 4):
        assert season_state.simulate_next_preseason_round() == expected_round
    assert season.preseason_complete

    # Idempotent once complete, same convention as the other simulate_* functions.
    assert season_state.simulate_next_preseason_round() == 0


def test_simulate_week_route_plays_preseason_rounds_before_the_regular_season():
    season_state.set_user_team("KC")
    # R16 Sec 8: see test_sim_week_button_returns_to_the_page_it_was_clicked_from's
    # own comment -- KC's real 62-man import needs the same one-time trim.
    roster_prep.auto_cut_team_to_limits("KC")
    for expected_round in (1, 2, 3, 4):
        resp = client.post("/season/simulate-week", data={"redirect_to": "/season"}, follow_redirects=False)
        assert resp.status_code == 303
        season = season_state.get_season()
        assert season.preseason_rounds_played == expected_round
        assert season.current_week == 1  # regular season hasn't started yet

    resp = client.post("/season/simulate-week", data={"redirect_to": "/season"}, follow_redirects=False)
    assert resp.status_code == 303
    season = season_state.get_season()
    assert season.preseason_complete
    assert season.current_week == 2  # first regular-season week just got simulated


def test_simulate_week_route_never_retroactively_forces_preseason_once_week_1_is_past():
    """Regression test for a real bug found via manual testing against a
    live save (season 25, week 19) that had never played its preseason:
    Sim Week must NOT suddenly demand 4 rounds of preseason once the
    regular season (or playoffs) already moved past Week 1 without it --
    preseason only gates progress as the literal first weeks of a BRAND
    NEW season (season_state.Season.preseason_pending)."""
    season_state.set_user_team("KC")
    # Bypass preseason entirely, same as a save/reload from before Sim Week
    # drove it, or a franchise that just never played it -- current_week
    # advances past 1 with preseason_schedule still fully unplayed.
    season_state.simulate_current_week()
    season_state.simulate_current_week()
    season = season_state.get_season()
    assert season.current_week == 3
    assert not season.preseason_complete
    assert not season.preseason_pending  # too late for preseason to gate anything now

    resp = client.post("/season/simulate-week", data={"redirect_to": "/season"}, follow_redirects=False)
    assert resp.status_code == 303
    season = season_state.get_season()
    assert season.current_week == 4  # advanced the regular season, not preseason
    assert not season.preseason_complete  # preseason itself is untouched -- just no longer gating


def test_simulate_week_route_reaches_the_offseason_pause_after_the_super_bowl():
    """Regression test for the reported bug: Sim Week used to silently
    no-op forever once the Super Bowl was decided. It should now always
    make forward progress, landing on /staff for Staff Decisions first."""
    for _ in range(4):
        season_state.simulate_next_preseason_round()
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    for _ in range(4):
        season_state.simulate_playoff_round()
    season = season_state.get_season()
    assert season.playoffs.is_complete

    resp = client.post("/season/simulate-week", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/staff"
    assert season_state.get_season().offseason_stage == "staff"

    # Clicking it again doesn't error or regress -- still parked on /staff.
    resp = client.post("/season/simulate-week", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/staff"
    assert season_state.get_season().season_number == 0


def test_season_page_shows_preseason_button_before_played():
    resp = client.get("/season")
    assert resp.status_code == 200
    assert "Preseason (0/4 simulated)" in resp.text


def test_season_page_shows_preseason_complete_after_played():
    season_state.simulate_preseason()
    resp = client.get("/season")
    assert resp.status_code == 200
    assert "Preseason (4/4 complete)" in resp.text
    assert "Preseason (0/4 simulated)" not in resp.text


def test_preseason_backfills_week1_scouting_and_reverts_after_week1_is_played():
    """R10: while Week 1 hasn't been played yet, the Scouting Panel reads
    real preseason box scores instead of an empty sample; the moment
    Week 1 IS simulated, it reverts to regular-season-only."""
    from app.engine import scouting

    season_state.set_user_team("KC")
    season = season_state.get_season()
    season_state.simulate_preseason()

    games_before = scouting._played_games(season, "KC")
    assert len(games_before) == 4  # backfilled from the 4 preseason games

    season_state.simulate_current_week()
    games_after = scouting._played_games(season, "KC")
    assert len(games_after) == 1  # real Week 1 only, preseason no longer queried


def test_preseason_nudges_progression_usage():
    """PRESEASON_NUDGE_WEIGHT (0.25): a preseason snap counts as ~25% of
    a real regular-season snap toward progression's usage input -- "as
    if the player had ~25% of a regular-season game's usage" per this
    feature's own locked-in spec, checked directly against a real,
    simulated preseason box score's own attempt count."""
    season = season_state.get_season()
    season_state.simulate_preseason()

    passing, _, _ = season_state.season_stats.aggregate_season_stats(
        season_state.SimpleNamespace(schedule=season.preseason_schedule)
    )
    assert passing, "expected at least one QB to have real preseason pass attempts"
    _, line = max(passing.items(), key=lambda kv: kv[1].attempts)
    nudged_touches = round(line.attempts * season_state.PRESEASON_NUDGE_WEIGHT)
    assert 0 < nudged_touches < line.attempts
    assert season_state.PRESEASON_NUDGE_WEIGHT == 0.25


def test_apply_progression_to_roster_runs_cleanly_with_only_preseason_played():
    """Regression test for the preseason-touches wiring in
    apply_progression_to_roster(): a real end-to-end rollover pass
    against a roster whose ONLY played games are preseason (no
    regular-season game exists yet) must not raise, and must still
    update the DB -- confirms the new preseason aggregation branch is
    exercised without crashing (test_season_rollover.py's own
    test_apply_progression_to_roster_actually_mutates_the_db covers the
    regular-season path's mutation claim in detail already)."""
    from app.models.player import Player
    from app.core.db import get_session
    from sqlmodel import select

    season = season_state.get_season()
    season_state.simulate_preseason()

    with get_session() as s:
        before_ages = {p.player_id: p.age for p in s.exec(select(Player).where(Player.team_abbr != None)).all()}  # noqa: E711

    season_state.apply_progression_to_roster(season)

    with get_session() as s:
        after = {p.player_id: p.age for p in s.exec(select(Player).where(Player.team_abbr != None)).all()}  # noqa: E711
    still_rostered = before_ages.keys() & after.keys()
    assert still_rostered
    assert all(after[pid] == before_ages[pid] + 1 for pid in still_rostered)


def test_dashboard_play_by_play_box_removed():
    """ROADMAP.md Sec2c item 2: Play-by-Play is no longer its own
    dashboard box -- only reachable via the Box Score box's link to the
    full page."""
    season_state.set_user_team("KC")
    season_state.simulate_current_week()
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "<h3>Play-by-Play" not in resp.text


def test_dashboard_box_score_moved_to_row_1_with_scoreboard_and_game_leaders():
    """ROADMAP.md Sec2c items 2-3: Box Score moves to Row 1 (spanning 2 of
    the 3 columns, alongside Standings) and gains a condensed scoreboard
    summary + a real per-game "Game Leaders" mini-leaderboard above the
    existing full box score tables. Real regression test for a bug found
    live during verification: the away team's Game Leaders column was
    showing the HOME team's abbreviation twice instead of the away team's."""
    season_state.set_user_team("KC")
    season_state.simulate_current_week()
    resp = client.get("/dashboard")
    assert resp.status_code == 200

    from app.services import season_state as ss
    season = ss.get_season()
    game = next(g for g in season.schedule[0] if "KC" in (g.home_abbr, g.away_abbr))
    assert "class=\"boxscore-summary " in resp.text  # win/loss/tie band class appended, Brian's request 2026-09-13
    assert "Game Leaders" in resp.text
    assert f'class="boxscore-leaders-team">{game.home_abbr}<' in resp.text
    assert f'class="boxscore-leaders-team">{game.away_abbr}<' in resp.text
    assert game.home_abbr != game.away_abbr  # sanity: the two teams really are distinct

    # Box Score's own DOM position: appears before Team Schedule/Scouting/
    # Weekly Gameplan (Row 2) and Power Rankings/Top Performers/Awards
    # Race (Row 3), matching the new row-by-row layout.
    assert resp.text.index("Box Score") < resp.text.index("Team Schedule")
    assert resp.text.index("Box Score") < resp.text.index("Power Rankings")


def test_dashboard_awards_race_box_renders_real_categories():
    """ROADMAP.md Sec2c item 2's Row 3: a real Awards Race box reusing
    awards.py's season_awards() (same data the Stats page's own Awards
    Race section already shows), tabbed MVP/OPOY/DPOY/ROY rather than
    the Stats page's four-tables-in-a-row layout. Gated on Week 4
    completion (a follow-up ask, same session): too small a sample
    before that to rank candidates meaningfully."""
    season_state.set_user_team("KC")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Awards Race" in resp.text
    assert "Check back after Week 4" in resp.text  # only 0 weeks simulated so far in THIS test

    for _ in range(4):
        season_state.simulate_current_week()
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    for tab in ("MVP", "OPOY", "DPOY", "ROY"):
        assert f'data-tab="{tab.lower()}">{tab}' in resp.text


# --- 2026-09-14 fixes: preseason box score/headlines, clinch legend, no page jumps ---

def test_dashboard_box_score_shows_latest_preseason_game_before_week_1():
    season_state.set_user_team("KC")
    season_state.simulate_next_preseason_round()
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "No games played yet" not in resp.text
    assert 'class="preseason-tag">Preseason</span> Round 1' in resp.text
    assert "/season/preseason/game/" in resp.text  # full box score link + schedule score links
    assert "Preseason Round 1" in resp.text  # headlines label for the preseason round


def test_preseason_rounds_record_their_own_headlines():
    from app.services import headlines_history
    season_state.simulate_preseason()
    season = season_state.get_season()
    for r in range(1, season.preseason_total_rounds + 1):
        entry = headlines_history.get_week_headlines(season.season_number, f"P{r}")
        lines = entry["league"] + entry["user_team"]
        assert lines and all(isinstance(line, str) and line for line in lines)


def test_standings_boxes_show_the_clinch_legend():
    season_state.set_user_team("KC")
    for page in ("/dashboard", "/season"):
        resp = client.get(page)
        assert resp.status_code == 200
        assert "x = Clinched playoff spot" in resp.text and "* = Clinched first-round bye" in resp.text


def test_gameplan_save_via_fetch_answers_json_instead_of_reloading():
    season_state.set_user_team("KC")
    resp = client.post("/gameplan", data={
        "offensive_aggressiveness": "Balanced", "defensive_aggressiveness": "Balanced",
        "coverage": "Hybrid", "blitz": "Standard", "rz_offense": "Balanced", "rz_defense": "Balanced",
    }, headers={"X-Requested-With": "fetch"}, follow_redirects=False)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    dashboard = client.get("/dashboard")
    assert 'id="gameplan-form"' in dashboard.text and "X-Requested-With" in dashboard.text


def test_stats_apply_form_keeps_scroll_position():
    season_state.set_user_team("KC")
    season_state.simulate_current_week()
    resp = client.get("/stats?tab=player")
    assert resp.status_code == 200
    assert 'class="stats-filter-form" data-keep-scroll' in resp.text
    assert "ffg-keep-scroll" in resp.text  # base.html's restore wiring
