import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import season_state, save_service, gameplan_store, history_store, power_rank_history
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


def setup_function(_):
    # Each test gets a fresh season so they don't interact via shared module state.
    history_store.DEFAULT_PATH.unlink(missing_ok=True)
    season_state.reset_season()
    gameplan_store.DEFAULT_PATH.unlink(missing_ok=True)
    power_rank_history.DEFAULT_PATH.unlink(missing_ok=True)


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
    assert "Coaching Staff" in resp.text
    assert "Trait Effects" in resp.text
    assert "data-coach-card=" in resp.text

    head_coach = coach_store.head_coach("KC")
    assert head_coach is not None
    assert head_coach.full_name in resp.text
    # The generated-vs-real disclosure must be on the page, not just in
    # a docstring -- it's the whole reason the generated ratings are
    # acceptable to show at all.
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
            sorted(season.records.values(), key=lambda r: -r.power_rating), start=1
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


def test_dashboard_headlines_box_replaces_old_header_with_coming_soon():
    """ROADMAP.md Sec2c items 1-2: the old "Dashboard — Season N..." header
    is replaced by a Headlines box, which renders per the coming-soon
    convention until R9 (GDD Sec12) actually lands -- no fabricated
    headline content."""
    season_state.set_user_team("KC")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Headlines" in resp.text
    assert "Coming soon" in resp.text
    assert "<h2>Dashboard" not in resp.text
    # The old header's real week-status line/nav links are preserved.
    assert "Week 1 of" in resp.text
    assert 'href="/season"' in resp.text


def test_dashboard_gameplan_filler_subtext_removed():
    """ROADMAP.md Sec2c item 4: strip GDD-citation-style filler captions
    from dashboard widgets -- Weekly Gameplan's own field tooltips already
    explain each setting."""
    season_state.set_user_team("KC")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Weekly Gameplan" in resp.text
    assert "Sets your Head Coach's strategy" not in resp.text


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
    assert "class=\"boxscore-summary\"" in resp.text
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
