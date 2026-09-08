import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

from fastapi.testclient import TestClient

from app.main import app
from app.services import season_state, save_service, gameplan_store, history_store
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


def setup_function(_):
    # Each test gets a fresh season so they don't interact via shared module state.
    history_store.DEFAULT_PATH.unlink(missing_ok=True)
    season_state.reset_season()
    gameplan_store.DEFAULT_PATH.unlink(missing_ok=True)


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


def test_staff_gm_desk_and_draft_render_coming_soon():
    """GDD Sec 10.3's MVP navigation behavior: these three nav items
    exist and render a real Coming Soon message, not a 404 -- they
    didn't exist as routes at all before this."""
    for path, title in [("/staff", "Staff"), ("/gm-desk", "GM Desk"), ("/draft", "Draft")]:
        resp = client.get(path)
        assert resp.status_code == 200
        assert title in resp.text
        assert "Coming soon" in resp.text
