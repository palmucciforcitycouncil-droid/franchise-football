"""
Tests for scripts/import_nfl_history.py -- the real-NFL-data import
pipeline for League History/HOF (nflverse via nflreadpy).

All tests here use small, hand-built polars DataFrames matching
nflreadpy's real column shapes (confirmed against a real fetched row
while writing this script -- see the module's own docstring) rather
than hitting the network, so this file runs fast and deterministically
offline. A separate, explicitly-marked end-to-end test does a real
network fetch to prove the whole pipeline against real data -- skipped
by default (network-dependent, not run as part of the regular suite).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

polars = pytest.importorskip("polars")

from scripts.import_nfl_history import (
    _map_abbr, _real_standings, _real_champion, _real_season_stat_lines, _real_rookie_keys, MY_ABBRS,
)


def test_map_abbr_normalizes_historically_relocated_franchises():
    assert _map_abbr("LA") == "LAR"
    assert _map_abbr("OAK") == "LV"
    assert _map_abbr("SD") == "LAC"
    assert _map_abbr("STL") == "LAR"
    assert _map_abbr("KC") == "KC"  # never-relocated franchise passes through unchanged


def _schedule_row(home, away, home_score, away_score, game_type="REG"):
    return {"game_type": game_type, "home_team": home, "away_team": away, "home_score": home_score, "away_score": away_score}


def test_real_standings_aggregates_wins_losses_and_points_from_real_scores():
    schedules = polars.DataFrame([
        _schedule_row("KC", "BUF", 30, 20),
        _schedule_row("MIA", "KC", 10, 24),
        _schedule_row("KC", "DEN", 17, 17),  # a tie -- neither a win nor a loss
    ])
    standings = _real_standings(schedules)
    kc = standings["KC"]
    assert kc.wins == 2
    assert kc.losses == 0
    assert kc.points_for == 30 + 24 + 17
    assert kc.points_against == 20 + 10 + 17
    # every one of this engine's 32 real teams gets a row, even with zero real games
    assert len(standings) == len(MY_ABBRS)


def test_real_standings_maps_historical_abbrs_onto_current_ones():
    schedules = polars.DataFrame([_schedule_row("OAK", "KC", 14, 21)])
    standings = _real_standings(schedules)
    assert "OAK" not in standings
    assert standings["LV"].losses == 1


def test_real_champion_picks_the_real_super_bowl_winner():
    schedules = polars.DataFrame([
        _schedule_row("KC", "BUF", 30, 20),  # a REG game -- must be ignored
        _schedule_row("KC", "SF", 25, 22, game_type="SB"),
    ])
    assert _real_champion(schedules) == "KC"


def test_real_champion_none_when_no_sb_row_exists():
    schedules = polars.DataFrame([_schedule_row("KC", "BUF", 30, 20)])
    assert _real_champion(schedules) is None


def _stat_row(**overrides):
    row = {
        "recent_team": "KC", "player_display_name": "Test Player",
        "attempts": 0, "completions": 0, "passing_yards": 0, "passing_tds": 0, "passing_interceptions": 0,
        "carries": 0, "rushing_yards": 0, "rushing_tds": 0,
        "receptions": 0, "targets": 0, "receiving_yards": 0, "receiving_tds": 0,
        "def_tackles_solo": 0, "def_tackles_for_loss": 0, "def_sacks": 0.0, "def_interceptions": 0,
        "def_pass_defended": 0, "def_fumbles_forced": 0, "fumble_recovery_own": 0, "fumble_recovery_opp": 0,
    }
    row.update(overrides)
    return row


def test_real_season_stat_lines_builds_a_passing_line_from_real_attempts():
    stats = polars.DataFrame([_stat_row(player_display_name="Real QB", attempts=500, completions=350, passing_yards=4000, passing_tds=30, passing_interceptions=10)])
    passing, rushing, receiving, defense = _real_season_stat_lines(stats)
    line = passing[("KC", "Real QB")]
    assert line.attempts == 500 and line.yards == 4000 and line.touchdowns == 30


def test_real_season_stat_lines_triggers_receiving_on_receptions_not_just_targets():
    """Regression guard: real nflverse data before ~2009 has real
    receptions/receiving_yards but targets == 0 (not tracked league-wide
    that far back) -- gating on targets alone silently drops almost
    every real pre-2009 receiver. Confirmed empirically against real
    2005 data while building this script."""
    stats = polars.DataFrame([_stat_row(player_display_name="Old Era WR", receptions=60, targets=0, receiving_yards=800, receiving_tds=5)])
    _, _, receiving, _ = _real_season_stat_lines(stats)
    line = receiving[("KC", "Old Era WR")]
    assert line.receptions == 60 and line.yards == 800


def test_real_season_stat_lines_builds_a_defensive_line_from_real_defensive_stats():
    stats = polars.DataFrame([_stat_row(player_display_name="Real LB", def_tackles_solo=120, def_sacks=8.0, def_interceptions=3, def_tackles_for_loss=10, def_pass_defended=5, def_fumbles_forced=2)])
    _, _, _, defense = _real_season_stat_lines(stats)
    line = defense[("KC", "Real LB")]
    assert line.solo_tackles == 120 and line.sacks == 8 and line.interceptions == 3 and line.forced_fumbles == 2


def test_real_season_stat_lines_maps_historical_team_abbrs():
    stats = polars.DataFrame([_stat_row(recent_team="OAK", player_display_name="Old Raider", attempts=400, passing_yards=3000)])
    passing, _, _, _ = _real_season_stat_lines(stats)
    assert ("LV", "Old Raider") in passing
    assert ("OAK", "Old Raider") not in passing


def test_real_season_stat_lines_skips_teams_outside_the_current_32():
    """A real player_stats row whose team doesn't map onto this engine's
    32 real teams (e.g. a Pro Bowl squad, or any residual code this
    engine's TEAM_ABBR_MAP doesn't cover) is silently skipped, not
    crashed on."""
    stats = polars.DataFrame([_stat_row(recent_team="AFC", player_display_name="Pro Bowler", attempts=10, passing_yards=50)])
    passing, _, _, _ = _real_season_stat_lines(stats)
    assert passing == {}


def test_real_rookie_keys_filters_to_years_exp_zero_and_maps_abbrs():
    rosters = polars.DataFrame([
        {"team": "KC", "full_name": "Real Rookie", "years_exp": 0},
        {"team": "KC", "full_name": "Real Veteran", "years_exp": 5},
        {"team": "OAK", "full_name": "Old Era Rookie", "years_exp": 0},
    ])
    keys = _real_rookie_keys(rosters)
    assert ("KC", "Real Rookie") in keys
    assert ("KC", "Real Veteran") not in keys
    assert ("LV", "Old Era Rookie") in keys  # historical abbr mapped


# --- Real end-to-end network test (explicitly opt-in, not part of the regular suite) ---

@pytest.mark.skip(reason="hits the real network (nflreadpy/nflverse) -- this repo's test suite runs offline; comment out this skip to run it manually")
def test_real_network_import_2023_matches_known_real_facts():
    """Not run automatically (network-dependent, and this repo's test
    suite is meant to run offline) -- a manual sanity check proving the
    whole real pipeline against real 2023 NFL data, confirmed by hand
    while building this script: KC won Super Bowl LVIII (25-22 over SF)
    finishing 11-6 in the regular season."""
    from scripts.import_nfl_history import import_season
    record = import_season(2023)
    assert record.champion_abbr == "KC"
    kc = next(t for t in record.team_results if t.abbr == "KC")
    assert (kc.wins, kc.losses) == (11, 6)
