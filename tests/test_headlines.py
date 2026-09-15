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
    # Records are AFTER this game: KC was 2-9 going in, LV 9-2.
    records = {"KC": TeamRecord(abbr="KC", location="KC", wins=3, losses=9, power_rating=1400),
               "LV": TeamRecord(abbr="LV", location="LV", wins=9, losses=3, power_rating=1600)}
    season = _season(schedule, records=records, current_week=13)
    events = headlines._detect_game_events(season, schedule[0], None)
    upsets = [e for e in events if e.category == "upset"]
    assert len(upsets) == 1
    assert upsets[0].values["winner"] == _team_name("KC")
    # Brian: records next to the team names, "NE (1-14) upsets NYJ (14-1)".
    line = headlines.render_headline(upsets[0], 2025, 0, 12)
    assert "KC (3-9)" in line and "LV (9-3)" in line and "24-21" in line


def test_detect_game_events_does_not_flag_a_favorite_winning_as_an_upset():
    schedule = [[_game("KC", "LV", 24, 21)]]
    records = {"KC": TeamRecord(abbr="KC", location="KC", wins=9, losses=3, power_rating=1600),
               "LV": TeamRecord(abbr="LV", location="LV", wins=3, losses=9, power_rating=1400)}
    season = _season(schedule, records=records, current_week=13)
    events = headlines._detect_game_events(season, schedule[0], None)
    assert not [e for e in events if e.category == "upset"]


def test_equal_records_are_never_an_upset_even_with_a_rating_gap():
    schedule = [[_game("KC", "LV", 24, 21)]]
    records = {"KC": TeamRecord(abbr="KC", location="KC", wins=7, losses=6, power_rating=1450),
               "LV": TeamRecord(abbr="LV", location="LV", wins=7, losses=6, power_rating=1600)}
    season = _season(schedule, records=records, current_week=14)
    events = headlines._detect_game_events(season, schedule[0], "LV")
    assert not [e for e in events if e.category in ("upset", "team_upset")]


def test_early_season_upset_needs_a_wide_pregame_rating_gap():
    schedule = [[_game("KC", "LV", 24, 21)]]
    near = {"KC": TeamRecord(abbr="KC", location="KC", wins=1, losses=0, power_rating=1490),
            "LV": TeamRecord(abbr="LV", location="LV", wins=0, losses=1, power_rating=1510)}
    assert not [e for e in headlines._detect_game_events(_season(schedule, records=near, current_week=2), schedule[0], None)
                if e.category == "upset"]
    # Wide gap, but the printed records (KC 1-0, LV 0-1) don't show LV as the better team.
    wide_even = {"KC": TeamRecord(abbr="KC", location="KC", wins=1, losses=0, power_rating=1420),
                 "LV": TeamRecord(abbr="LV", location="LV", wins=0, losses=1, power_rating=1580)}
    assert not [e for e in headlines._detect_game_events(_season(schedule, records=wide_even, current_week=2), schedule[0], None)
                if e.category == "upset"]
    wide = {"KC": TeamRecord(abbr="KC", location="KC", wins=1, losses=2, power_rating=1420),
            "LV": TeamRecord(abbr="LV", location="LV", wins=3, losses=1, power_rating=1580)}
    assert [e for e in headlines._detect_game_events(_season(schedule, records=wide, current_week=4), schedule[0], None)
            if e.category == "upset"]


def test_pregame_rating_inversion_recovers_the_ratings_before_the_game():
    from app.engine.power_rating import update_ratings
    post_h, post_a = update_ratings(1450.0, 1580.0, 31, 17)
    pre_h, pre_a = headlines._pregame_ratings(post_h, post_a, 31, 17)
    assert abs(pre_h - 1450.0) < 1e-6 and abs(pre_a - 1580.0) < 1e-6


def test_a_tie_is_never_an_upset_a_win_or_a_loss():
    # Brian: "NE shocks NYJ 17-17" / "falls to ... in a tie" must never happen.
    schedule = [[_game("NE", "NYJ", 17, 17)]]
    records = {"NE": TeamRecord(abbr="NE", location="NE", wins=2, losses=10, power_rating=1350),
               "NYJ": TeamRecord(abbr="NYJ", location="NYJ", wins=10, losses=2, power_rating=1650)}
    season = _season(schedule, records=records, current_week=13)
    events = headlines._detect_game_events(season, schedule[0], "NYJ")
    cats = {e.category for e in events}
    assert "tie" in cats
    assert not cats & {"upset", "team_upset", "close_game", "blowout"}
    tie = next(e for e in events if e.category == "tie")
    for tmpl in headlines.TEMPLATES["tie"]:
        line = tmpl.format(**tie.values)
        assert "17-17" in line and "NE (2-10)" in line and "NYJ (10-2)" in line
        assert "falls" not in line and "upset" not in line.lower()


def test_player_headlines_keep_the_plain_team_tag():
    # "Name (POS, TEAM)" -- a team describing a player carries no record.
    for key in ("stat_milestone", "single_season_record", "playoff_standout", "notable_injury"):
        for tmpl in headlines.TEMPLATES[key]:
            assert "_label}" not in tmpl


def test_consecutive_weeks_do_not_reuse_the_same_phrasing():
    ev = headlines.HeadlineEvent(tier=1, category="blowout", magnitude=1, is_user_team=False, template_key="blowout",
                                 values={"winner_label": "KC (5-1)", "loser_label": "LV (1-5)", "w_score": 40, "l_score": 10},
                                 event_key="blowout|KC|LV")
    headlines_history.DEFAULT_PATH.unlink(missing_ok=True)
    # ev.is_user_team is False, so every render lands in league_lines (index 0).
    lines = [headlines._render_events([ev], 2025, 77, week)[0][0] for week in range(1, 7)]
    assert all(a != b for a, b in zip(lines, lines[1:]))


def test_same_week_events_of_one_type_get_different_phrasings():
    evs = [headlines.HeadlineEvent(tier=1, category="blowout", magnitude=1, is_user_team=False, template_key="blowout",
                                   values={"winner_label": w, "loser_label": "X (0-1)", "w_score": 40, "l_score": 10},
                                   event_key=f"blowout|{w}") for w in ("A (1-0)", "B (1-0)")]
    league_lines, user_lines = headlines._render_events(evs, 2025, 78, 3)
    a, b = league_lines
    assert a.replace("A (1-0)", "") != b.replace("B (1-0)", "")


def test_starter_injury_headline_only_for_starters_missing_time():
    from types import SimpleNamespace
    from app.core.db import get_session
    from app.models.player import Player
    from app.models.injury import InjuryType
    from sqlmodel import select

    with get_session() as s:
        player = s.exec(select(Player).where(Player.team_abbr != None)).first()  # noqa: E711
    if player is None:
        return
    inj = SimpleNamespace(player_id=player.player_id, team_abbr=player.team_abbr, weeks_out=3,
                          injury_type=InjuryType.KNEE, injury_id="t1")
    events = headlines._detect_injury_events([inj], None, starter_ids={player.player_id})
    assert len(events) == 1
    for tmpl in headlines.TEMPLATES["notable_injury"]:
        line = tmpl.format(**events[0].values)
        assert player.full_name in line and f"({player.position.value})" in line
        assert "3 weeks" in line and "a knee injury" in line

    assert headlines._detect_injury_events([inj], None, starter_ids=set()) == []  # not a starter
    inj.weeks_out = 0
    assert headlines._detect_injury_events([inj], None, starter_ids={player.player_id}) == []  # misses no time


def test_playoff_round_headlines_name_the_round_and_the_result():
    from app.engine.playoffs import PlayoffMatchup
    records = {"KC": TeamRecord(abbr="KC", location="KC", wins=13, losses=4),
               "BUF": TeamRecord(abbr="BUF", location="BUF", wins=11, losses=6)}
    season = _season([[_game("KC", "BUF", 1, 0)]], records=records)
    m = PlayoffMatchup(round_name="DIV", conference="AFC", home_abbr="KC", away_abbr="BUF", home_seed=1, away_seed=4,
                       result=GameResult(home_score=20, away_score=27, winner="away", events=[], plays=[]))
    headlines_history.DEFAULT_PATH.unlink(missing_ok=True)
    league_lines, user_lines = headlines.playoff_round_headlines(season, [m])
    lines = league_lines + user_lines  # no user_team_abbr set on this season -- everything's league-wide
    assert len(lines) == 1
    assert "BUF (11-6)" in lines[0] and "KC (13-4)" in lines[0] and "27-20" in lines[0]
    assert "Divisional" in lines[0]


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
        entry = headlines_history.get_week_headlines(season.season_number, 1)
        assert entry is not None
        lines = entry["league"] + entry["user_team"]
        assert 1 <= len(lines) <= headlines.TARGET_TOTAL + headlines.MAX_INJURY_HEADLINES
        assert all(isinstance(line, str) and line for line in lines)
    finally:
        save_service.DEFAULT_SAVE_PATH = real_save
