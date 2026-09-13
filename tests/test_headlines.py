"""
Tests for Weekly Headlines (GDD Sec 12, ROADMAP.md Sec4e/R9,
app/engine/headlines.py) -- the deterministic-template version, not an
LLM call. Builds small synthetic Seasons by hand (real dataclasses,
fabricated results) so each detector can be checked against an exact
expected event, plus a couple of end-to-end tests through a real
simulated week to confirm the whole pipeline doesn't crash and produces
real, stable output.
"""
import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

from app.services.season_state import Season, WeekGame, TeamRecord
from app.engine.game_state import GameResult
from app.engine import headlines
from app.engine.headlines import _team_name
from app.engine.flavor_text import pick_and_render
from app.services import save_service, history_store, headlines_history

save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_season_headlines.json")
history_store.DEFAULT_PATH = Path("data/saves/_test_history_headlines.json")
history_store.DEFAULT_PATH.unlink(missing_ok=True)
headlines_history.DEFAULT_PATH = Path("data/saves/_test_headlines_history.json")
headlines_history.DEFAULT_PATH.unlink(missing_ok=True)


def _game(home, away, home_score, away_score):
    result = GameResult(
        home_score=home_score, away_score=away_score,
        winner="home" if home_score >= away_score else "away",
        events=[], plays=[],
    )
    return WeekGame(home_abbr=home, away_abbr=away, result=result)


def _season(schedule, records=None, current_week=None, user_team_abbr=None):
    abbrs = {g.home_abbr for week in schedule for g in week} | {g.away_abbr for week in schedule for g in week}
    recs = {a: TeamRecord(abbr=a, location=a) for a in abbrs}
    if records:
        recs.update(records)
    return Season(
        league_seed=2025, schedule=schedule, records=recs,
        current_week=current_week or len(schedule) + 1, user_team_abbr=user_team_abbr,
    )


# --- flavor_text.pick_and_render --------------------------------------------

def test_pick_and_render_is_deterministic():
    templates = {"greeting": ["Hello {name}.", "Hi there, {name}!", "Yo {name}."]}
    a = pick_and_render(templates, "greeting", (2025, 1, "x"), name="KC")
    b = pick_and_render(templates, "greeting", (2025, 1, "x"), name="KC")
    assert a == b


def test_pick_and_render_varies_with_seed_key():
    templates = {"greeting": [f"Variant {i}" for i in range(20)]}
    results = {pick_and_render(templates, "greeting", (2025, i)) for i in range(20)}
    assert len(results) > 1  # not every seed collapses to the same variant


# --- blowouts / upsets -------------------------------------------------------

def test_detect_game_events_flags_a_real_blowout():
    schedule = [[_game("KC", "LV", 45, 10)]]
    season = _season(schedule, current_week=2)
    events = headlines._detect_game_events(season, schedule[0], None)
    blowouts = [e for e in events if e.category == "blowout"]
    assert len(blowouts) == 1
    assert blowouts[0].values["winner"] == _team_name("KC") and blowouts[0].values["w_score"] == 45


def test_detect_game_events_flags_a_real_upset_when_the_worse_team_wins():
    schedule = [[_game("KC", "LV", 24, 21)]]
    records = {"KC": TeamRecord(abbr="KC", location="KC", power_rating=1400),
               "LV": TeamRecord(abbr="LV", location="LV", power_rating=1600)}
    season = _season(schedule, records=records, current_week=2)
    events = headlines._detect_game_events(season, schedule[0], None)
    upsets = [e for e in events if e.category == "upset"]
    # KC (lower/worse rating 1400) beat LV (higher/better rating 1600) -- a real upset.
    assert len(upsets) == 1
    assert upsets[0].values["winner"] == _team_name("KC")


def test_detect_game_events_does_not_flag_a_favorite_winning_as_an_upset():
    schedule = [[_game("KC", "LV", 24, 21)]]
    records = {"KC": TeamRecord(abbr="KC", location="KC", power_rating=1600),
               "LV": TeamRecord(abbr="LV", location="LV", power_rating=1400)}
    season = _season(schedule, records=records, current_week=2)
    events = headlines._detect_game_events(season, schedule[0], None)
    assert not [e for e in events if e.category == "upset"]


def test_detect_game_events_flags_a_close_game():
    schedule = [[_game("KC", "LV", 20, 17)]]
    season = _season(schedule, current_week=2)
    events = headlines._detect_game_events(season, schedule[0], None)
    assert any(e.category == "close_game" for e in events)


# --- streaks ------------------------------------------------------------------

def test_detect_streak_events_flags_a_real_five_game_win_streak():
    schedule = [
        [_game("KC", "LV", 30, 10)],
        [_game("DEN", "KC", 10, 30)],
        [_game("KC", "LAC", 30, 10)],
        [_game("BUF", "KC", 10, 30)],
        [_game("KC", "MIA", 30, 10)],
    ]
    season = _season(schedule, current_week=6)
    events = headlines._detect_streak_events(season, 5, None)
    streaks = [e for e in events if e.category == "streak" and e.values["team"] == _team_name("KC")]
    assert len(streaks) == 1
    assert streaks[0].template_key == "win_streak"
    assert streaks[0].values["length"] == 5


def test_detect_streak_events_does_not_fire_on_a_four_game_streak():
    schedule = [
        [_game("KC", "LV", 30, 10)],
        [_game("DEN", "KC", 10, 30)],
        [_game("KC", "LAC", 30, 10)],
        [_game("BUF", "KC", 10, 30)],
    ]
    season = _season(schedule, current_week=5)
    events = headlines._detect_streak_events(season, 4, None)
    assert not [e for e in events if e.category == "streak" and e.values["team"] == _team_name("KC")]


# --- selection waterfall -------------------------------------------------------

def test_select_events_tier1_capped_at_three_then_fills_from_lower_tiers():
    events = (
        [headlines.HeadlineEvent(tier=1, category="a", magnitude=1, is_user_team=False, template_key="x", event_key=f"t1-{i}") for i in range(5)]
        + [headlines.HeadlineEvent(tier=2, category="b", magnitude=1, is_user_team=False, template_key="x", event_key=f"t2-{i}") for i in range(3)]
    )
    selected = headlines.select_events(events, league_seed=1, season_number=0, week_num=1)
    assert sum(1 for e in selected if e.tier == 1) == 3
    assert len(selected) == headlines.TARGET_TOTAL


def test_select_events_is_deterministic_across_calls():
    events = [
        headlines.HeadlineEvent(tier=2, category="a", magnitude=float(i), is_user_team=False, template_key="x", event_key=f"e{i}")
        for i in range(6)
    ]
    a = [e.event_key for e in headlines.select_events(events, 1, 0, 1)]
    b = [e.event_key for e in headlines.select_events(events, 1, 0, 1)]
    assert a == b


def test_select_events_returns_empty_when_nothing_detected():
    # weekly_headlines() itself is exercised end-to-end below; this just
    # confirms select_events on an empty list returns nothing to render,
    # which weekly_headlines() turns into the real "in the books" fallback.
    assert headlines.select_events([], 1, 0, 1) == []


# --- end-to-end through a real simulated week ---------------------------------

def test_weekly_headlines_end_to_end_through_a_real_simulated_week():
    from app.services import season_state

    real_save = save_service.DEFAULT_SAVE_PATH
    try:
        season_state.reset_season()
        season = season_state.get_season()
        season_state.simulate_current_week()
        season = season_state.get_season()
        lines = headlines_history.get_week_headlines(season.season_number, 1)
        assert lines is not None
        assert 1 <= len(lines) <= headlines.TARGET_TOTAL
        assert all(isinstance(line, str) and line for line in lines)
    finally:
        save_service.DEFAULT_SAVE_PATH = real_save
