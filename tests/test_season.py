import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

from fastapi.testclient import TestClient

from app.main import app
from app.services import season_state, save_service
from app.engine.schedule import generate_season_schedule, N_WEEKS
from app.data.teams import TEAMS

client = TestClient(app)

# Tests must never touch the live app's real save file (data/saves/current_season.json)
# -- that would clobber whatever a real browser session has in progress. Redirect to a
# throwaway path for the duration of this test module.
save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_season.json")


def setup_function(_):
    # Each test gets a fresh season so they don't interact via shared module state.
    season_state.reset_season()


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
