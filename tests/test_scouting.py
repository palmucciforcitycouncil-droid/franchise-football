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
from app.services import save_service, history_store

# The end-to-end test below calls season_state.reset_season()/
# simulate_current_week() for real -- must never touch the live app's
# real save file, same convention as test_season.py, and this module
# can't rely on that module having already run first (e.g. `pytest
# tests/test_scouting.py` in isolation).
save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_season.json")
# season_state._build_season() now reads history_store (a fresh franchise's
# season_number bootstraps to AFTER whatever's archived) -- redirect + clear so this
# module never depends on the REAL data/saves/history.json's ambient content.
history_store.DEFAULT_PATH = Path("data/saves/_test_history_scouting.json")
history_store.DEFAULT_PATH.unlink(missing_ok=True)


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


def test_situational_defense_run_tactic_and_primary_call_splits():
    # Same 3-play fixture as above: 1 "Standard" call, 1 "Run Defense"
    # call (with a real Plug Gaps run tactic), 1 "Pass Defense" call
    # (the red-zone play, real Man coverage).
    plays = [
        _play(1, 10, 30, "pass", "BUF", defensive_call="Standard, Blitz (J. Smith), Man"),
        _play(1, 10, 30, "run", "BUF", defensive_call="Run Defense, Zone, Plug Gaps"),
        _play(2, 5, 85, "pass", "BUF", defensive_call="Pass Defense, Blitz (K. Jones), Man"),  # red zone
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)

    result = scouting.situational_defense(season, "KC")
    assert result["standard_pct"] == pytest.approx(33.3, abs=0.1)
    assert result["run_defense_pct"] == pytest.approx(33.3, abs=0.1)
    assert result["pass_defense_pct"] == pytest.approx(33.3, abs=0.1)
    # Only 1 of the 3 plays has a run tactic at all (Plug Gaps) -- the
    # tactic split is a percentage of THAT subset, not of all 3 plays.
    assert result["plug_gaps_pct"] == 100.0
    assert result["contain_edge_pct"] == 0.0
    assert result["redzone_man_pct"] == 100.0
    assert result["third_long_blitz_pct"] is None  # no down==3 & distance>=8 plays in this fixture


# --- red_zone_efficiency -----------------------------------------------------

def _drive_play(drive_number, down, distance, field_pos, offense_abbr, outcome="gain"):
    return PlayEvent(down=down, distance=distance, field_pos=field_pos, play_type="run" if down != 4 else "pass",
                      yards=4, desc="x", outcome=outcome, offense_abbr=offense_abbr, drive_number=drive_number)


def test_red_zone_efficiency_counts_real_drive_conversions_not_per_play():
    plays = [
        # Drive 1: reaches the red zone, ends in a real touchdown -- a converted trip.
        _drive_play(1, 1, 10, 60, "KC"),
        _drive_play(1, 2, 5, 85, "KC", outcome="touchdown"),
        # Drive 2: reaches the red zone, ends in a field goal -- a trip, not converted.
        _drive_play(2, 1, 10, 82, "KC", outcome="field_goal"),
        # Drive 3: never reaches the red zone at all -- not a trip.
        _drive_play(3, 1, 10, 50, "KC", outcome="first_down"),
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)

    result = scouting.red_zone_efficiency(season, "KC")
    assert result["trips"] == 2
    assert result["touchdowns"] == 1
    assert result["td_pct"] == 50.0


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
    assert result["attempts"] == 3
    assert result["conversions"] == 2
    assert result["success_rate"] == pytest.approx(66.7, abs=0.1)


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


def test_field_goal_accuracy_3bucket_regroups_the_same_real_data():
    plays = [
        _fg_play("KC", 25, True),
        _fg_play("KC", 35, True),
        _fg_play("KC", 35, False),
        _fg_play("KC", 52, True),
    ]
    schedule = [[_played_game("KC", "BUF", 10, 7, plays=plays)]]
    season = _season(schedule, current_week=2)
    result = scouting.field_goal_accuracy_3bucket(season, "KC")
    assert result["Under 40"] == {"made": 2, "attempted": 3, "pct": pytest.approx(66.7, abs=0.1)}
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


def test_team_summary_tie_credits_the_home_team_a_win_not_a_loss():
    """A tied score (game_sim.py has no overtime, so h == a is a real
    outcome) still resolves to a winner -- GDD Sec 3.1.2's `ties` field
    is "reserved even if engine forces a winner" (home wins the tie,
    game_sim.py's `winner = "home" if h >= a else "away"`). last3's
    won flag must agree with that forced winner instead of independently
    recomputing my_score > opp_score, which would show the tie as a loss
    for BOTH teams and contradict season.records' win/loss counts."""
    schedule = [[_played_game("KC", "BUF", 6, 6)]]  # tie -- home (KC) is the forced winner
    season = _season(schedule, current_week=2)
    kc_result = scouting.team_summary(season, "KC")
    buf_result = scouting.team_summary(season, "BUF")

    assert kc_result["last3"][0].won is True
    assert buf_result["last3"][0].won is False


def test_team_summary_turnover_differential_is_forced_minus_committed():
    schedule = [[_played_game(
        "KC", "BUF", 10, 7,
        home_totals=_totals(turnovers=1),   # KC committed 1
        away_totals=_totals(turnovers=3),   # BUF (forced by KC's defense) committed 3
    )]]
    season = _season(schedule, current_week=2)
    result = scouting.team_summary(season, "KC")
    assert result["turnover_diff"] == 2  # 3 forced - 1 committed


def test_team_summary_yards_allowed_and_total_ypg():
    schedule = [[_played_game(
        "KC", "BUF", 10, 7,
        home_totals=_totals(pass_yards=200, rush_yards=100),  # KC's own offense
        away_totals=_totals(pass_yards=150, rush_yards=80),   # BUF's offense -- what KC's defense allowed
    )]]
    season = _season(schedule, current_week=2)
    result = scouting.team_summary(season, "KC")
    assert result["total_ypg"] == 300.0
    assert result["pass_ypg_allowed"] == 150.0
    assert result["rush_ypg_allowed"] == 80.0
    assert result["total_ypg_allowed"] == 230.0


def test_team_summary_philosophy_label_from_real_pass_rate():
    def _plays(pass_count, run_count):
        return [_play(1, 10, 30, "pass", "KC") for _ in range(pass_count)] + \
               [_play(1, 10, 30, "run", "KC") for _ in range(run_count)]

    pass_heavy = _season([[_played_game("KC", "BUF", 10, 7, plays=_plays(7, 3))]], current_week=2)
    run_heavy = _season([[_played_game("KC", "BUF", 10, 7, plays=_plays(3, 7))]], current_week=2)
    balanced = _season([[_played_game("KC", "BUF", 10, 7, plays=_plays(5, 5))]], current_week=2)

    assert scouting.team_summary(pass_heavy, "KC")["philosophy"] == "Pass-Heavy"
    assert scouting.team_summary(run_heavy, "KC")["philosophy"] == "Run-Heavy"
    assert scouting.team_summary(balanced, "KC")["philosophy"] == "Balanced"


def test_team_summary_before_any_games_is_all_none_not_zero():
    schedule = [[_unplayed_game("KC", "BUF")]]
    season = _season(schedule, current_week=1)
    result = scouting.team_summary(season, "KC")
    assert result["games_played"] == 0
    assert result["ppg"] is None
    assert result["streak"] == "-"
    assert result["last3"] == []
    assert result["total_ypg"] is None
    assert result["pass_ypg_allowed"] is None
    assert result["philosophy"] is None


# --- league_ranks --------------------------------------------------------------

def test_league_ranks_ranks_a_team_among_the_whole_league():
    # A: 0 penalties, turnover_diff +3 (best in both).
    # B: 2 penalties, turnover_diff -3 (the team under test -- unambiguous
    #    middle rank on penalties, unambiguous last on turnover diff).
    # C vs D: 4 penalties for C / 0 for D, turnover_diff 0/0 (a tie between
    #    A(0.0)/D(0.0) on penalties is fine -- B's own rank stays
    #    deterministic either way since its value is strictly between them).
    penalty_plays_b = [_penalty_play("B", "False start, X: 5 yards"), _penalty_play("B", "False start, X: 5 yards")]
    penalty_plays_c = [_penalty_play("C", "False start, X: 5 yards") for _ in range(4)]
    schedule = [[
        _played_game("A", "B", 10, 7, plays=penalty_plays_b,
                      home_totals=_totals(turnovers=0), away_totals=_totals(turnovers=3)),
        _played_game("C", "D", 10, 7, plays=penalty_plays_c,
                      home_totals=_totals(turnovers=1), away_totals=_totals(turnovers=1)),
    ]]
    season = _season(schedule, current_week=2)

    b_ranks = scouting.league_ranks(season, "B")
    assert b_ranks["of_teams"] == 4
    assert b_ranks["penalty_rank"] == 3  # worse than A and D (0.0 each), better than C (4.0)
    assert b_ranks["turnover_rank"] == 4  # strictly worst turnover_diff (-3)

    a_ranks = scouting.league_ranks(season, "A")
    assert a_ranks["turnover_rank"] == 1  # strictly best turnover_diff (+3)


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


# --- Scouting Panel prose (ROADMAP.md Sec4e/R12) -----------------------------

def _fake_scouting(team_abbr="KC", games_played=5, philosophy="Balanced", ppg=24.0, papg=20.0,
                    first_down_pass_pct=50.0, third_long_pass_pct=70.0, sample_size=100,
                    blitz_pct=25.0, man_pct=50.0, def_sample_size=100,
                    fg_buckets=None, penalty_rank=15, turnover_diff=0):
    return {
        "team_abbr": team_abbr,
        "summary": {
            "games_played": games_played, "philosophy": philosophy, "ppg": ppg, "papg": papg,
            "turnover_diff": turnover_diff,
        },
        "offense": {
            "sample_size": sample_size, "first_down_pass_pct": first_down_pass_pct,
            "first_down_run_pct": scouting._complement(first_down_pass_pct), "third_long_pass_pct": third_long_pass_pct,
        },
        "defense": {"sample_size": def_sample_size, "blitz_pct": blitz_pct, "man_pct": man_pct},
        "field_goals": fg_buckets or {"Under 40": {"made": 3, "attempted": 3, "pct": 100.0}, "40-49": {"made": 1, "attempted": 2, "pct": 50.0}, "50+": {"made": 0, "attempted": 0, "pct": None}},
        "league_ranks": {"penalty_rank": penalty_rank, "turnover_rank": 10, "of_teams": 32},
    }


def test_overview_prose_no_games_yet():
    s = _fake_scouting(games_played=0)
    text = scouting.overview_prose(s, league_seed=1)
    assert "hasn't played" in text


def test_overview_prose_reflects_real_philosophy_bucket():
    pass_heavy = scouting.overview_prose(_fake_scouting(philosophy="Pass-Heavy", ppg=30.0, papg=18.0), league_seed=1)
    assert "30.0" in pass_heavy
    run_heavy = scouting.overview_prose(_fake_scouting(philosophy="Run-Heavy"), league_seed=1)
    assert run_heavy  # renders without error, a different template bucket


def test_offense_prose_no_sample():
    s = _fake_scouting(sample_size=0)
    assert "Not enough" in scouting.offense_prose(s, league_seed=1)


def test_offense_prose_pass_heavy_bucket_uses_real_values():
    s = _fake_scouting(first_down_pass_pct=70.0, third_long_pass_pct=85.0)
    text = scouting.offense_prose(s, league_seed=1)
    assert "70.0" in text and "85.0" in text


def test_defense_prose_blitz_heavy_bucket():
    s = _fake_scouting(blitz_pct=45.0)
    text = scouting.defense_prose(s, league_seed=1)
    assert "45.0" in text


def test_special_teams_prose_computes_real_combined_pct():
    s = _fake_scouting()
    text = scouting.special_teams_prose(s, league_seed=1)
    # 4 made of 5 attempted across the two non-empty buckets = 80.0%
    assert "80.0" in text


def test_special_teams_prose_no_attempts_yet():
    s = _fake_scouting(fg_buckets={"Under 40": {"made": 0, "attempted": 0, "pct": None}, "40-49": {"made": 0, "attempted": 0, "pct": None}, "50+": {"made": 0, "attempted": 0, "pct": None}})
    assert "hasn't attempted" in scouting.special_teams_prose(s, league_seed=1)


def test_discipline_prose_uses_real_rank_buckets():
    clean = scouting.discipline_prose(_fake_scouting(penalty_rank=3), league_seed=1)
    assert "disciplined" in clean
    sloppy = scouting.discipline_prose(_fake_scouting(penalty_rank=30), league_seed=1)
    assert "struggled" in sloppy


def test_discipline_prose_handles_no_games_played_rank_of_none():
    s = _fake_scouting(penalty_rank=None)
    text = scouting.discipline_prose(s, league_seed=1)
    assert text  # renders without a KeyError/TypeError on a None rank


def test_stats_prose_reflects_real_turnover_sign():
    positive = scouting.stats_prose(_fake_scouting(turnover_diff=5), league_seed=1)
    assert "plus-5" in positive
    negative = scouting.stats_prose(_fake_scouting(turnover_diff=-3), league_seed=1)
    assert "minus-3" in negative
    even = scouting.stats_prose(_fake_scouting(turnover_diff=0), league_seed=1)
    assert "even" in even


def test_prose_functions_are_deterministic_given_the_same_inputs():
    s = _fake_scouting()
    assert scouting.overview_prose(s, league_seed=7) == scouting.overview_prose(s, league_seed=7)
    assert scouting.offense_prose(s, league_seed=7) == scouting.offense_prose(s, league_seed=7)


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_build_scouting_report_includes_real_prose_via_the_dashboard_route():
    """The prose fields aren't computed inside build_scouting_report()
    itself (app/main.py's dashboard_view adds scouting['prose'] after
    calling it) -- this confirms the report's own shape has everything
    each prose function needs, end-to-end against a real simulated
    season, not just the synthetic fixtures above."""
    from app.services import season_state

    season_state.reset_season()
    for _ in range(3):
        season_state.simulate_current_week()
    season = season_state.get_season()
    next_opponent = scouting.find_next_opponent(season, "KC")
    opponent_abbr, _ = next_opponent
    report = scouting.build_scouting_report(season, opponent_abbr)

    assert scouting.overview_prose(report, season.league_seed)
    assert scouting.offense_prose(report, season.league_seed)
    assert scouting.defense_prose(report, season.league_seed)
    assert scouting.special_teams_prose(report, season.league_seed)
    assert scouting.discipline_prose(report, season.league_seed)
    assert scouting.stats_prose(report, season.league_seed)
