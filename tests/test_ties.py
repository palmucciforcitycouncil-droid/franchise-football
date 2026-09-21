"""
Regression tests for the regular-season ties bug: a genuine tied score
(home_score == away_score) used to be recorded as a HOME TEAM WIN, with
no ties tracked anywhere. Root cause: game_sim.py's `winner = "home" if
h >= a else "away"` always forces a pick for GameResult.winner (left
alone -- that's a real, intentional field with no third state), and
season_state.py's week-sim loop only ever checked `result.winner`
instead of comparing the literal score.

The fix is scoped to REGULAR SEASON STANDINGS -- ties are a real,
possible regular-season outcome (even after real OT, one period can
still leave a game tied, same as the real NFL). Playoff games instead
get real sudden-death OT that repeats until the tie breaks and can only
end tied via a vanishingly rare safety-valve fallback (see game_sim.py's
`_simulate_overtime_period`/`simulate_game`'s `playoff` flag,
2026-09-20) -- not exercised by these tests, which only cover the
regular-season standings bookkeeping.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

from pathlib import Path

import pytest

from app.data.teams import TEAMS
from app.engine.game_state import GameResult
from app.engine.game_sim import TeamTotals
from app.engine import playoffs
from app.services.season_state import Season, WeekGame, TeamRecord
from app.services import season_state, save_service


def _tied_result(score=17) -> GameResult:
    """A GameResult shaped like a real one (home_totals/away_totals set
    dynamically, same as game_sim.simulate_game does -- scouting.py's
    team_summary() reads them unconditionally) but with a literal tied
    score, for monkeypatching _simulate_one_game in the tests below."""
    result = GameResult(home_score=score, away_score=score, winner="home", events=[], plays=[])
    result.home_totals = TeamTotals(points=score)  # type: ignore[attr-defined]
    result.away_totals = TeamTotals(points=score)  # type: ignore[attr-defined]
    return result


# --- (b) win_pct with ties matches the standard NFL half-win formula -------

def test_win_pct_counts_a_tie_as_half_a_win():
    rec = TeamRecord(abbr="KC", location="Kansas City", wins=8, losses=6, ties=2)
    assert rec.win_pct == pytest.approx((8 + 0.5 * 2) / 16)
    assert rec.games_played == 16


def test_win_pct_is_zero_with_no_games_played():
    rec = TeamRecord(abbr="KC", location="Kansas City")
    assert rec.win_pct == 0.0
    assert rec.games_played == 0


def test_win_pct_matches_pre_fix_behavior_when_there_are_no_ties():
    """Sanity check that the formula change is additive -- a record with
    zero ties behaves exactly as it always did."""
    rec = TeamRecord(abbr="KC", location="Kansas City", wins=11, losses=6)
    assert rec.win_pct == pytest.approx(11 / 17)


# --- (a) a forced-tie matchup increments both teams' ties, not wins/losses -

def test_simulated_tie_increments_ties_not_wins_or_losses(monkeypatch):
    """Forces every Week 1 game to end in a literal tie (by monkeypatching
    the RNG-driven per-game core, _simulate_one_game, which
    simulate_current_week()'s loop calls once per game) and confirms the
    week-sim loop's new tie branch fires: both teams' `ties` go up, and
    NEITHER team's wins/losses do -- the exact bug Brian reported (a tie
    silently counted as a home win) is what this guards against."""
    season_state.reset_season()

    def _forced_tie(season, home_abbr, away_abbr, week_for_parity, seed_parts, playoff=False):
        return _tied_result(17)

    monkeypatch.setattr(season_state, "_simulate_one_game", _forced_tie)
    season_state.simulate_current_week()

    season = season_state.get_season()
    week1_teams = {abbr for g in season.schedule[0] for abbr in (g.home_abbr, g.away_abbr)}
    assert week1_teams, "sanity: Week 1 has games"
    for abbr in week1_teams:
        rec = season.records[abbr]
        assert rec.ties == 1, f"{abbr} should have 1 tie"
        assert rec.wins == 0, f"{abbr} should NOT have a win credited for a tied score"
        assert rec.losses == 0, f"{abbr} should NOT have a loss credited for a tied score"
        assert rec.win_pct == pytest.approx(0.5)
        assert rec.games_played == 1

    # Bye-week team (if any this week) is untouched.
    for abbr, rec in season.records.items():
        if abbr not in week1_teams:
            assert rec.wins == rec.losses == rec.ties == 0


def test_simulated_mixed_week_only_ties_the_tied_games(monkeypatch):
    """A more realistic week: exactly one game is forced to a tie, the
    rest simulate normally. Only the two teams in that one game should
    show a tie; the rest keep ordinary win/loss behavior."""
    season_state.reset_season()
    season = season_state.get_season()
    tied_home, tied_away = season.schedule[0][0].home_abbr, season.schedule[0][0].away_abbr

    real_simulate = season_state._simulate_one_game

    def _maybe_tie(season, home_abbr, away_abbr, week_for_parity, seed_parts, playoff=False):
        if home_abbr == tied_home and away_abbr == tied_away:
            return _tied_result(20)
        return real_simulate(season, home_abbr, away_abbr, week_for_parity, seed_parts, playoff=playoff)

    monkeypatch.setattr(season_state, "_simulate_one_game", _maybe_tie)
    season_state.simulate_current_week()

    season = season_state.get_season()
    assert season.records[tied_home].ties == 1
    assert season.records[tied_away].ties == 1
    assert season.records[tied_home].wins == 0 and season.records[tied_home].losses == 0
    assert season.records[tied_away].wins == 0 and season.records[tied_away].losses == 0

    total_wins = sum(r.wins for r in season.records.values())
    total_losses = sum(r.losses for r in season.records.values())
    total_ties = sum(r.ties for r in season.records.values())
    games_this_week = len(season.schedule[0])
    # Every game contributes either one win + one loss, or two ties (one per
    # team) -- real games (not the forced one) can also land on a genuine
    # tied score by chance, so this checks the invariant rather than an
    # exact count: total_ties is always even, and wins/losses/ties account
    # for every game played this week with no double-counting.
    assert total_wins == total_losses
    assert total_ties % 2 == 0
    assert total_wins + total_ties // 2 == games_this_week
    assert total_ties >= 2  # at least the one game this test forced


# --- (c) playoffs.rank_teams() orders/breaks ties among teams with ---------
#     --- different tie counts correctly -------------------------------------

def _record(abbr, location, wins=0, losses=0, ties=0):
    return TeamRecord(abbr=abbr, location=location, wins=wins, losses=losses, ties=ties)


def _bare_season(records):
    return Season(league_seed=1, schedule=[], records=records, current_week=1)


def test_rank_teams_ranks_a_team_with_ties_between_a_better_and_worse_pure_record():
    """9-6-2 (win_pct = (9+1)/17 = .588) should rank between 10-7 (.588 --
    a genuine tie with the ties team) and 9-8 (.529). Uses three distinct
    AFC East teams so the tiebreak chain has real head-to-head data to
    fall back on if win_pct alone doesn't separate two of them."""
    records = {t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS}
    records["BUF"].wins, records["BUF"].losses, records["BUF"].ties = 10, 7, 0   # .5882
    records["MIA"].wins, records["MIA"].losses, records["MIA"].ties = 9, 6, 2    # .5882 (tied with BUF)
    records["NYJ"].wins, records["NYJ"].losses, records["NYJ"].ties = 9, 8, 0    # .5294
    season = _bare_season(records)

    ranked = playoffs.rank_teams(season, ["BUF", "MIA", "NYJ"], playoffs._wildcard_steps)
    assert ranked[2] == "NYJ"  # clearly worst win_pct, ranked last regardless of tiebreak order
    assert set(ranked[:2]) == {"BUF", "MIA"}  # the two .5882 teams are genuinely tied and go through the tiebreak chain


def test_rank_teams_groups_teams_by_wins_losses_and_ties_together():
    """Two teams with the SAME wins/losses but DIFFERENT ties must not be
    silently grouped as if tied (the pre-fix bug: the grouping key was
    (wins, losses) only) -- 10-5-1 (.6818) clearly outranks 10-6-0 (.625)."""
    records = {t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS}
    records["BUF"].wins, records["BUF"].losses, records["BUF"].ties = 10, 5, 1
    records["MIA"].wins, records["MIA"].losses, records["MIA"].ties = 10, 6, 0
    season = _bare_season(records)

    ranked = playoffs.rank_teams(season, ["BUF", "MIA"], playoffs._wildcard_steps)
    assert ranked == ["BUF", "MIA"]


def test_rank_teams_exact_tie_including_ties_count_still_uses_tiebreak_chain():
    """Two teams genuinely level on wins, losses, AND ties fall through to
    the real tiebreak chain (head-to-head here), same as the pre-fix
    (wins, losses)-only behavior for teams with zero ties."""
    schedule = [
        [WeekGame(home_abbr="BUF", away_abbr="MIA",
                  result=GameResult(home_score=24, away_score=17, winner="home", events=[], plays=[]))],
    ]
    records = {t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS}
    records["BUF"].wins, records["BUF"].losses, records["BUF"].ties = 10, 6, 1
    records["MIA"].wins, records["MIA"].losses, records["MIA"].ties = 10, 6, 1
    season = Season(league_seed=1, schedule=schedule, records=records, current_week=2)

    ranked = playoffs.rank_teams(season, ["BUF", "MIA"], playoffs._division_steps)
    assert ranked == ["BUF", "MIA"]  # BUF won their head-to-head game


# --- (d) an old-format saved season JSON (no "ties" key) still loads -------
#     --- correctly (defaults to 0) ------------------------------------------

def test_teamrecord_defaults_ties_to_zero_when_constructed_without_it():
    """Directly exercises the exact construction save_service.py's
    season_from_dict() uses (TeamRecord(**rec)) against a dict shaped
    like an old save's "records" entry, written before `ties` existed."""
    old_style_rec = {"abbr": "KC", "location": "Kansas City", "wins": 11, "losses": 6,
                      "points_for": 410, "points_against": 350, "power_rating": 1550.0}
    rec = TeamRecord(**old_style_rec)
    assert rec.ties == 0
    assert rec.wins == 11 and rec.losses == 6
    assert rec.win_pct == pytest.approx(11 / 17)


def test_old_format_save_file_loads_via_save_service_with_ties_defaulted(tmp_path, monkeypatch):
    """End-to-end: hand-write a save JSON in the OLD shape (every
    "records" entry missing "ties" entirely, as a real save written
    before this fix would be) and confirm save_service.load_season()
    reconstructs a Season where every team's ties defaults to 0 --
    exactly the "no migration needed" guarantee TeamRecord's dataclass
    default is supposed to provide."""
    import json

    season_state.reset_season()
    season = season_state.get_season()
    raw = save_service.season_to_dict(season)
    for rec in raw["records"].values():
        assert "ties" in rec  # sanity: a fresh save DOES write ties
        del rec["ties"]  # simulate an old, pre-fix save file

    path = tmp_path / "old_save.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    reloaded = save_service.load_season(path)
    assert all(r.ties == 0 for r in reloaded.records.values())
    # Everything else still round-trips normally.
    assert reloaded.league_seed == season.league_seed
    assert reloaded.current_week == season.current_week


# --- headlines.py / power_rating.py already anticipated the field ---------

def test_headlines_record_map_reflects_real_ties():
    from app.engine import headlines

    season_state.reset_season()
    season = season_state.get_season()
    season.records["KC"].ties = 2
    season.records["KC"].wins = 3
    season.records["KC"].losses = 1

    record_map = headlines.season_record_map(season)
    assert record_map["KC"] == (3, 1, 2)


def test_power_rating_record_anchor_treats_a_tie_as_a_half_win():
    """Three teams, all 10 games into their season: 9-1-0 (a real loss),
    9-0-1 (a real tie), and 10-0-0 (a real win) for that 10th game. The
    record-anchor bonus (win_pct-based) should rank them in exactly that
    order -- a tie is worth more than a loss and less than a win, never
    equal to either."""
    from app.engine import power_rating

    nine_one_loss = power_rating.power_score(1500.0, wins=9, losses=1, ties=0)
    nine_oh_tie = power_rating.power_score(1500.0, wins=9, losses=0, ties=1)
    ten_and_oh = power_rating.power_score(1500.0, wins=10, losses=0, ties=0)
    assert nine_one_loss < nine_oh_tie < ten_and_oh
