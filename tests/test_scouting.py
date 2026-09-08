"""
Tests for Scouting: Next Opponent (GDD Part 1 Sec 10.4.1,
app/engine/scouting.py). Most tests build a small synthetic Season by
hand (real dataclasses, fabricated PlayEvents/scores) so each
computation can be checked against an exact expected count -- these
don't need the roster DB. A couple of end-to-end tests run a real
simulated season and just check the report doesn't crash and returns
sane shapes.
"""
import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.services.season_state import Season, WeekGame, TeamRecord
from app.engine.game_state import GameResult, PlayEvent
from app.engine.game_sim import TeamTotals
from app.engine import scouting
from app.services import save_service

# The end-to-end test below calls season_state.reset_season()/
# simulate_current_week() for real -- must never touch the live app's
# real save file, same convention as test_season.py, and this module
# can't rely on that module having already run first (e.g. `pytest
# tests/test_scouting.py` in isolation).
save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_season.json")


def _totals(pass_yards=0, rush_yards=0, turnovers=0):
    return TeamTotals(pass_yards=pass_yards, rush_yards=rush_yards, turnovers=turnovers)


def _played_game(home_abbr, away_abbr, home_score, away_score, plays=None, home_totals=None, away_totals=None):
    result = GameResult(
        home_score=home_score, away_score=away_score,
        winner="home" if home_score >= away_score else "away",
        events=[], plays=plays or [],
    )
    result.home_totals = home_totals or _totals()
    result.away_totals = away_totals or _totals()
    return WeekGame(home_abbr=home_abbr, away_abbr=away_abbr, result=result)


def _unplayed_game(home_abbr, away_abbr):
    return WeekGame(home_abbr=home_abbr, away_abbr=away_abbr, result=None)


def _season(schedule, current_week=1):
    abbrs = {g.home_abbr for week in schedule for g in week} | {g.away_abbr for week in schedule for g in week}
    records = {a: TeamRecord(abbr=a, location=a) for a in abbrs}
    return Season(league_seed=1, schedule=schedule, records=records, current_week=current_week)


# --- find_next_opponent -----------------------------------------------------

def test_find_next_opponent_returns_the_immediate_next_game():
    schedule = [
        [_played_game("KC", "BUF", 20, 17)],
        [_unplayed_game("KC", "DEN")],
    ]
    season = _season(schedule, current_week=2)
    opponent, is_home = scouting.find_next_opponent(season, "KC")
    assert opponent == "DEN"
    assert is_home is True


def test_find_next_opponent_skips_a_bye_week():
    schedule = [
        [_played_game("KC", "BUF", 20, 17)],
        [_unplayed_game("DEN", "LAC")],           # KC has a bye this week
        [_unplayed_game("LV", "KC")],
    ]
    season = _season(schedule, current_week=2)
    opponent, is_home = scouting.find_next_opponent(season, "KC")
    assert opponent == "LV"
    assert is_home is False


def test_find_next_opponent_none_when_season_is_over():
    schedule = [[_played_game("KC", "BUF", 20, 17)]]
    season = _season(schedule, current_week=2)
    assert scouting.find_next_opponent(season, "KC") is None


# --- situational_offense / situational_defense ------------------------------

def _play(down, distance, field_pos, play_type, offense_abbr, defensive_call="Standard, Zone", outcome="gain"):
    return PlayEvent(down=down, distance=distance, field_pos=field_pos, play_type=play_type,
                      yards=4, desc="x", outcome=outcome, offense_abbr=offense_abbr, defensive_call=defensive_call)


def test_situational_offense_computes_real_pass_percentages():
    plays = [
        _play(1, 10, 30, "run", "KC"),
        _play(1, 10, 30, "pass", "KC"),
        _play(1, 10, 30, "pass", "KC"),
        _play(1, 10, 30, "pass", "KC"),  # 3 of 4 first-down plays are passes -> 75%
        _play(3, 2, 50, "run", "KC"),
        _play(3, 2, 50, "run", "KC"),    # 0% pass on 3rd & short
        _play(3, 9, 50, "pass", "KC"),   # 100% pass on 3rd & long
        _play(2, 5, 85, "pass", "KC"),   # red zone: 1 of 1 pass -> 100%
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)

    result = scouting.situational_offense(season, "KC")
    assert result["sample_size"] == 8
    assert result["first_down_pass_pct"] == 75.0
    assert result["third_short_pass_pct"] == 0.0
    assert result["third_long_pass_pct"] == 100.0
    assert result["redzone_pass_pct"] == 100.0
    assert result["third_medium_pass_pct"] is None  # no 3rd & 4-7 plays at all


def test_situational_offense_only_counts_that_teams_own_plays():
    plays = [_play(1, 10, 30, "pass", "BUF")]  # BUF's play, not KC's
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)
    result = scouting.situational_offense(season, "KC")
    assert result["sample_size"] == 0
    assert result["first_down_pass_pct"] is None


def test_situational_defense_computes_blitz_and_coverage_rates():
    # BUF is on offense; KC is on defense for these plays.
    plays = [
        _play(1, 10, 30, "pass", "BUF", defensive_call="Standard, Blitz (J. Smith), Man"),
        _play(1, 10, 30, "run", "BUF", defensive_call="Run Defense, Zone, Plug Gaps"),
        _play(2, 5, 85, "pass", "BUF", defensive_call="Pass Defense, Blitz (K. Jones), Man"),  # red zone
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)

    result = scouting.situational_defense(season, "KC")
    assert result["sample_size"] == 3
    assert result["blitz_pct"] == pytest.approx(66.7, abs=0.1)
    assert result["man_pct"] == pytest.approx(66.7, abs=0.1)
    assert result["redzone_blitz_pct"] == 100.0


# --- fourth_down_aggressiveness ---------------------------------------------

def test_fourth_down_aggressiveness_counts_attempts_and_conversions():
    plays = [
        _play(4, 1, 50, "run", "KC", outcome="first_down"),  # converted
        _play(4, 2, 50, "pass", "KC", outcome="incomplete"),  # failed
        _play(4, 8, 50, "pass", "KC", outcome="touchdown"),  # converted (TD)
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)
    result = scouting.fourth_down_aggressiveness(season, "KC")
    assert result == {"attempts": 3, "conversions": 2}


# --- field_goal_accuracy -----------------------------------------------------

def _fg_play(offense_abbr, yards, made):
    desc = f"{yards}-yard field goal is GOOD" if made else f"{yards}-yard field goal is NO GOOD"
    return PlayEvent(down=4, distance=1, field_pos=80, play_type="field_goal", yards=0, desc=desc,
                      outcome="field_goal" if made else "turnover", offense_abbr=offense_abbr)


def test_field_goal_accuracy_buckets_by_real_parsed_distance():
    plays = [
        _fg_play("KC", 25, True),
        _fg_play("KC", 35, True),
        _fg_play("KC", 35, False),
        _fg_play("KC", 52, True),
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)
    result = scouting.field_goal_accuracy(season, "KC")
    assert result["<30"] == {"made": 1, "attempted": 1, "pct": 100.0}
    assert result["30-39"] == {"made": 1, "attempted": 2, "pct": 50.0}
    assert result["40-49"] == {"made": 0, "attempted": 0, "pct": None}
    assert result["50+"] == {"made": 1, "attempted": 1, "pct": 100.0}


# --- penalty_discipline -------------------------------------------------------

def _penalty_play(offense_abbr, desc):
    return PlayEvent(down=1, distance=10, field_pos=50, play_type="penalty", yards=0, desc=desc, outcome="penalty", offense_abbr=offense_abbr)


def test_penalty_discipline_attributes_to_the_real_committing_team():
    plays = [
        _penalty_play("KC", "False start, T. Smith: 5 yards"),        # KC's own penalty (offense)
        _penalty_play("KC", "False start, T. Smith: 5 yards"),        # KC's own penalty (offense), same type again
        _penalty_play("BUF", "Offside, D. Jones: 5 yards"),           # BUF on offense -> KC (defense) committed this
        _penalty_play("BUF", "Defensive pass interference, D. Jones: 12 yards, automatic first down"),  # KC's defense
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)

    result = scouting.penalty_discipline(season, "KC")
    assert result["total"] == 4
    assert result["per_game"] == 4.0
    types = dict(result["top_types"])
    assert types.get("False start") == 2  # ranked first, most common
    assert types.get("Offside") == 1
    assert types.get("Defensive pass interference") == 1


def test_penalty_discipline_top_types_caps_at_three():
    """Matches the Figma design's own "top 3 penalties" convention --
    a 4th distinct type should be counted in `total` but not listed."""
    plays = [
        _penalty_play("KC", "False start, T: 5 yards"),
        _penalty_play("KC", "Holding, T: 10 yards, repeat 1st down"),
        _penalty_play("KC", "Delay of game, Q: 5 yards"),
        _penalty_play("KC", "Illegal formation, T: 5 yards"),
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)
    result = scouting.penalty_discipline(season, "KC")
    assert result["total"] == 4
    assert len(result["top_types"]) == 3


def test_penalty_discipline_ignores_the_opponents_own_penalties():
    plays = [
        _penalty_play("BUF", "False start, X: 5 yards"),  # BUF's own penalty -- not KC's
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)
    result = scouting.penalty_discipline(season, "KC")
    assert result["total"] == 0


# --- team_summary -------------------------------------------------------------

def test_team_summary_streak_and_last3_most_recent_first():
    schedule = [
        [_played_game("KC", "BUF", 10, 20)],   # L
        [_played_game("DEN", "KC", 14, 21)],   # W (KC away)
        [_played_game("KC", "LV", 30, 10)],    # W
        [_played_game("KC", "LAC", 24, 20)],   # W -- current streak W3
    ]
    season = _season(schedule, current_week=5)
    season.records["KC"].wins = 3
    season.records["KC"].losses = 1
    result = scouting.team_summary(season, "KC")

    assert result["streak"] == "W3"
    assert len(result["last3"]) == 3
    assert result["last3"][0].opponent == "LAC"  # most recent first
    assert result["last3"][0].won is True
    assert result["last3"][-1].opponent == "DEN"


def test_team_summary_turnover_differential_is_forced_minus_committed():
    schedule = [[_played_game(
        "KC", "BUF", 10, 7,
        home_totals=_totals(turnovers=1),   # KC committed 1
        away_totals=_totals(turnovers=3),   # BUF (forced by KC's defense) committed 3
    )]]
    season = _season(schedule, current_week=2)
    result = scouting.team_summary(season, "KC")
    assert result["turnover_diff"] == 2  # 3 forced - 1 committed


def test_team_summary_before_any_games_is_all_none_not_zero():
    schedule = [[_unplayed_game("KC", "BUF")]]
    season = _season(schedule, current_week=1)
    result = scouting.team_summary(season, "KC")
    assert result["games_played"] == 0
    assert result["ppg"] is None
    assert result["streak"] == "-"
    assert result["last3"] == []


# --- end-to-end smoke test against a real simulated season -------------------

from app.core.db import DB_PATH

DB_EXISTS = DB_PATH.exists()


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_build_scouting_report_against_a_real_simulated_season():
    from app.services import season_state

    season_state.reset_season()
    for _ in range(3):
        season_state.simulate_current_week()
    season = season_state.get_season()

    next_opponent = scouting.find_next_opponent(season, "KC")
    assert next_opponent is not None
    opponent_abbr, _ = next_opponent

    report = scouting.build_scouting_report(season, opponent_abbr)
    assert report["team_abbr"] == opponent_abbr
    assert report["summary"]["games_played"] >= 1
    assert isinstance(report["offense"]["sample_size"], int)
    assert isinstance(report["discipline"]["total"], int)
