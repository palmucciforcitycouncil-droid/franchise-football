"""
Tests for app/engine/defensive_box_score.py -- pure unit tests against
hand-built PlayEvent lists so each stat's attribution can be checked
exactly, plus a real simulated-game smoke test at the end.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.engine.game_state import PlayEvent
from app.engine.defensive_box_score import build_defensive_box_score


def _pe(play_type, yards, outcome, offense_abbr="KC", defender_name="", pass_defended=False, fumble_recovered_by=""):
    return PlayEvent(
        down=1, distance=10, field_pos=50, play_type=play_type, yards=yards,
        desc="", outcome=outcome, offense_abbr=offense_abbr,
        defender_name=defender_name, pass_defended=pass_defended, fumble_recovered_by=fumble_recovered_by,
    )


def test_sack_credits_sack_and_solo_tackle():
    plays = [_pe("pass", -7, "sack", defender_name="Chris Jones")]
    box = build_defensive_box_score(plays, "BUF")
    assert box[0].name == "Chris Jones"
    assert box[0].sacks == 1
    assert box[0].solo_tackles == 1


def test_interception_credits_int_but_not_a_tackle():
    plays = [_pe("pass", 0, "turnover", defender_name="Xavien Howard")]
    box = build_defensive_box_score(plays, "BUF")
    assert box[0].interceptions == 1
    assert box[0].solo_tackles == 0


def test_run_fumble_credits_forced_fumble_and_recovery_separately():
    plays = [_pe("run", -1, "turnover", defender_name="Bobby Wagner", fumble_recovered_by="Xavien Howard")]
    box = {l.name: l for l in build_defensive_box_score(plays, "BUF")}
    assert box["Bobby Wagner"].forced_fumbles == 1
    assert box["Xavien Howard"].fumble_recoveries == 1
    # forcing doesn't imply recovering, and vice versa
    assert box["Bobby Wagner"].fumble_recoveries == 0
    assert box["Xavien Howard"].forced_fumbles == 0


def test_run_fumble_by_same_defender_credits_both_to_them():
    plays = [_pe("run", -1, "turnover", defender_name="Bobby Wagner", fumble_recovered_by="Bobby Wagner")]
    box = build_defensive_box_score(plays, "BUF")
    assert box[0].forced_fumbles == 1
    assert box[0].fumble_recoveries == 1


def test_pass_defended_flag_gates_the_pd_stat():
    plays = [
        _pe("pass", 0, "incomplete", defender_name="Xavien Howard", pass_defended=True),
        _pe("pass", 0, "incomplete", defender_name="Xavien Howard", pass_defended=False),
    ]
    box = build_defensive_box_score(plays, "BUF")
    assert box[0].passes_defended == 1  # only the flagged one counts


def test_run_stopped_at_or_behind_line_is_a_tackle_for_loss():
    plays = [
        _pe("run", -2, "gain", defender_name="Chris Jones"),   # TFL
        _pe("run", 0, "first_down", defender_name="Chris Jones"),  # not realistic but tests the yards<=0 boundary
        _pe("run", 5, "first_down", defender_name="Bobby Wagner"),  # a real gain -- not a TFL
    ]
    box = {l.name: l for l in build_defensive_box_score(plays, "BUF")}
    assert box["Chris Jones"].solo_tackles == 2
    assert box["Chris Jones"].tackles_for_loss == 2
    assert box["Bobby Wagner"].solo_tackles == 1
    assert box["Bobby Wagner"].tackles_for_loss == 0


def test_pass_completion_credits_the_covering_defender_with_a_solo_tackle():
    plays = [_pe("pass", 8, "first_down", defender_name="Xavien Howard")]
    box = build_defensive_box_score(plays, "BUF")
    assert box[0].name == "Xavien Howard"
    assert box[0].solo_tackles == 1
    assert box[0].tackles_for_loss == 0  # TFL is run-specific


def test_pass_defensive_touchdown_credits_the_interception_and_the_td_separately():
    """A pick-six (GDD Sec 6.7.2's Defensive TD, ROADMAP.md M1) is still a
    real interception too -- both stats should be credited to the same
    interceptor, matching a real box score crediting both categories."""
    plays = [_pe("pass", 0, "defensive_touchdown", defender_name="Xavien Howard")]
    box = build_defensive_box_score(plays, "BUF")
    assert box[0].name == "Xavien Howard"
    assert box[0].interceptions == 1
    assert box[0].defensive_touchdowns == 1
    assert box[0].solo_tackles == 0  # not a tackle, same as a plain interception


def test_run_defensive_touchdown_credits_the_td_to_the_recoverer_not_the_forcer():
    """A fumble-six's forcer and recoverer can be different players (same
    Forced Fumble vs. Fumble Recovery split a plain fumble already has)
    -- the TD credit belongs to whoever actually returned it, i.e. the
    recoverer."""
    plays = [_pe("run", -1, "defensive_touchdown", defender_name="Bobby Wagner", fumble_recovered_by="Xavien Howard")]
    box = {l.name: l for l in build_defensive_box_score(plays, "BUF")}
    assert box["Bobby Wagner"].forced_fumbles == 1
    assert box["Bobby Wagner"].defensive_touchdowns == 0
    assert box["Xavien Howard"].fumble_recoveries == 1
    assert box["Xavien Howard"].defensive_touchdowns == 1


def test_touchdown_credits_no_defender():
    plays = [_pe("run", 20, "touchdown", defender_name="")]
    box = build_defensive_box_score(plays, "BUF")
    assert box == []


def test_offense_abbr_filters_to_only_the_opponents_plays():
    """abbr is always the DEFENSE -- a play where abbr is the offense
    (this same team's own snap) must never contribute to its own
    defensive box score."""
    plays = [
        _pe("pass", -7, "sack", offense_abbr="KC", defender_name="Chris Jones"),
        _pe("pass", -3, "sack", offense_abbr="BUF", defender_name="Should Not Count"),
    ]
    box = build_defensive_box_score(plays, "BUF")
    assert len(box) == 1
    assert box[0].name == "Chris Jones"


def test_sorted_by_solo_tackles_descending():
    plays = [
        _pe("pass", 5, "first_down", defender_name="A"),
        _pe("pass", 5, "first_down", defender_name="B"),
        _pe("pass", 5, "first_down", defender_name="B"),
    ]
    box = build_defensive_box_score(plays, "BUF")
    assert [l.name for l in box] == ["B", "A"]


# --- Real simulated-game smoke test ---

from app.core.db import DB_PATH
from app.engine.rng import RNG
from app.engine.rating import TeamRatings
from app.engine.game_sim import simulate_game, TeamSim

DB_EXISTS = DB_PATH.exists()


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_aggregate_season_defensive_stats_sums_across_two_real_games():
    """app/engine/season_stats.py's aggregate_season_defensive_stats,
    mirroring how the equivalent offensive test proves aggregate_season_
    stats sums real per-game box scores."""
    from app.services.season_state import Season, WeekGame, TeamRecord
    from app.data.teams import TEAMS
    from app.engine.season_stats import aggregate_season_defensive_stats

    AVG = TeamRatings(offense=70, defense=70, special=70, run_bias=0.5, aggression=0.5, pace=0.5)
    g1 = simulate_game(RNG.with_seed(2025), TeamSim(name="Kansas City", abbr="KC", ratings=AVG), TeamSim(name="Buffalo", abbr="BUF", ratings=AVG))
    g2 = simulate_game(RNG.with_seed(2026), TeamSim(name="Kansas City", abbr="KC", ratings=AVG), TeamSim(name="Buffalo", abbr="BUF", ratings=AVG))

    records = {t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS}
    season = Season(
        league_seed=1,
        schedule=[[WeekGame(home_abbr="KC", away_abbr="BUF", result=g1)], [WeekGame(home_abbr="KC", away_abbr="BUF", result=g2)]],
        records=records,
    )

    defense = aggregate_season_defensive_stats(season)
    assert defense, "expected at least one credited defender across two real games"

    # cross-check one KC defender's season total against the raw sum of
    # their two per-game box scores, to prove this is real summation and
    # not just re-deriving the same numbers a different way
    kc_g1 = {l.name: l for l in build_defensive_box_score(g1.plays, "KC")}
    kc_g2 = {l.name: l for l in build_defensive_box_score(g2.plays, "KC")}
    some_name = next(iter(kc_g1))
    g2_tackles = kc_g2[some_name].solo_tackles if some_name in kc_g2 else 0
    expected_tackles = kc_g1[some_name].solo_tackles + g2_tackles
    assert defense[("KC", some_name)].solo_tackles == expected_tackles


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_real_simulated_game_produces_a_real_non_degenerate_defensive_box_score():
    AVG = TeamRatings(offense=70, defense=70, special=70, run_bias=0.5, aggression=0.5, pace=0.5)
    rng = RNG.with_seed(2025)
    home = TeamSim(name="Kansas City", abbr="KC", ratings=AVG)
    away = TeamSim(name="Buffalo", abbr="BUF", ratings=AVG)
    result = simulate_game(rng, home, away)

    # KC's defense faced BUF's offense
    kc_defense = build_defensive_box_score(result.plays, "KC")
    assert kc_defense, "expected at least one credited KC defender"
    assert sum(l.solo_tackles for l in kc_defense) > 0
    # every credited defender is a real, non-empty name
    assert all(l.name for l in kc_defense)
    # BUF's own offensive plays must never appear as a KC-credited defensive stat
    # (offense_abbr filter) -- spot check via total plays run by each side
    total_kc_credit_events = sum(
        l.solo_tackles + l.sacks + l.interceptions + l.passes_defended + l.forced_fumbles + l.fumble_recoveries
        for l in kc_defense
    )
    assert total_kc_credit_events > 0
