"""
Tests for app/engine/clinch.py -- Standings clinch marks ("x" playoff
berth, "*" first-round bye) and the before/after-week comparison that
keeps "clinches" headlines from repeating week after week.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

from app.data.teams import TEAMS, TEAMS_BY_ABBR
from app.engine import clinch
from app.engine.game_state import GameResult
from app.services.season_state import Season, WeekGame, TeamRecord


def _blank(wins=0, remaining=17):
    return {t.abbr: wins for t in TEAMS}, {t.abbr: remaining for t in TEAMS}


def _conf_divisions(conf):
    out = {}
    for t in TEAMS:
        if t.conference == conf:
            out.setdefault(t.division, []).append(t.abbr)
    return out


def test_nobody_is_marked_before_any_games():
    wins, remaining = _blank()
    assert all(s.mark == "" for s in clinch.compute_clinches(wins, remaining).values())


def test_bye_requires_every_conference_rival_to_be_unable_to_catch_up():
    wins, remaining = _blank(wins=0, remaining=0)
    wins["KC"] = 13
    for t in TEAMS:
        if t.conference == "AFC" and t.abbr != "KC":
            wins[t.abbr] = 12  # max 12 < 13
    status = clinch.compute_clinches(wins, remaining)["KC"]
    assert status.bye and status.berth and status.division and status.mark == "*"

    # One rival who can still reach 13 (ties count against KC) -> no bye.
    remaining["BUF"] = 1
    status = clinch.compute_clinches(wins, remaining)["KC"]
    assert not status.bye


def test_wild_card_berth_counts_threats_spilling_out_of_each_division():
    divisions = _conf_divisions("AFC")
    wins, remaining = _blank(wins=0, remaining=0)
    east, north, south, west = divisions["East"], divisions["North"], divisions["South"], divisions["West"]
    team = east[0]
    wins[team] = 11
    # A division rival who can still pass: team can't clinch the division.
    wins[east[1]], remaining[east[1]] = 10, 2
    # North: 3 threats -> 2 spill into the wild-card pool. South: 1 threat (its own winner).
    for abbr in north[:3]:
        wins[abbr], remaining[abbr] = 11, 1
    wins[south[0]] = 12
    status = clinch.compute_clinches(wins, remaining)[team]
    assert not status.division
    assert status.berth and status.mark == "x"  # pool threats: 0 (East) + 2 (North) + 0 = 2 <= 2

    # West: 2 threats -> one more in the pool -> 3 teams could take all 3 wild cards.
    for abbr in west[:2]:
        wins[abbr] = 11
    assert not clinch.compute_clinches(wins, remaining)[team].berth


def _game(home, away, hs, as_):
    return WeekGame(home_abbr=home, away_abbr=away,
                    result=GameResult(home_score=hs, away_score=as_, winner="home" if hs >= as_ else "away", events=[], plays=[]))


def _season(schedule, wins):
    records = {t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS}
    for abbr, w in wins.items():
        records[abbr].wins = w
    for week in schedule:
        for g in week:
            if g.result is not None:
                loser = g.away_abbr if g.result.winner == "home" else g.home_abbr
                records[loser].losses += 1
    return Season(league_seed=1, schedule=schedule, records=records, current_week=len(schedule) + 1)


def test_clinch_is_new_only_in_the_week_it_happens():
    # KC plays weeks 1 and 2 and wins both; nobody else in the AFC plays
    # again -- so KC's bye becomes guaranteed exactly after Week 2.
    schedule = [
        [_game("KC", "LV", 24, 10)],
        [_game("DEN", "KC", 10, 24)],
        [WeekGame(home_abbr="NYG", away_abbr="DAL")],  # still unplayed, NFC only
    ]
    season = _season(schedule, {"KC": 2})
    before = clinch.clinches_before_week(season, 2)["KC"]
    after = clinch.season_clinches(season)["KC"]
    assert not before.bye and after.bye

    # One week later the status is unchanged -> not "new" again.
    before_wk3 = clinch.clinches_before_week(season, 3)["KC"]
    assert before_wk3.bye


def test_completed_season_uses_real_seeding():
    schedule = [[_game("KC", "LV", 24, 10)]]
    season = _season(schedule, {"KC": 1})
    # Every scheduled game is played -> exact marks from seed_conference.
    marks = clinch.clinch_marks(season)
    assert sum(1 for t in TEAMS if TEAMS_BY_ABBR[t.abbr].conference == "AFC" and marks[t.abbr]) == 7
    assert marks["KC"] == "*"


# --- Ties fix (2026-09-19): compute_clinches must weigh a rival's ties as --
#     real standings value, not silently discard them ------------------------

def test_compute_clinches_accounts_for_a_rivals_ties_as_a_threat():
    """Regression test for a real false-positive risk the ties fix could
    have introduced: a rival sitting on several ties has real standings
    value (a tie is worth half a win) that pure win-count comparisons
    would understate, potentially declaring a clinch that isn't actually
    guaranteed -- the one thing this module's own docstring says must
    never happen. A rival with 5 wins + 6 ties (11 of 17 games -> a
    16/17 win-pct ceiling if it wins out) must still be counted as a
    threat against a team whose own worst-case final total is only
    12 wins (12/17), even though the rival's raw win count (5) is far
    below 12."""
    wins, remaining = _blank(wins=0, remaining=0)
    tested_team = "KC"
    wins[tested_team] = 12  # already locked in; 0 games remaining -> floor == 12
    rival = "LV"  # same conference (AFC West)
    wins[rival] = 5
    remaining[rival] = 6
    ties = {t.abbr: 0 for t in TEAMS}
    ties[rival] = 6  # 5-0-6 through 11 games, 6 left -> ceiling of 5+6=11 wins + 6 ties if it also ties out,
    # but simply WINNING OUT (11 wins, 6 ties, 0 losses over 17) already beats 12-5's raw win_pct:
    # (11 + 0.5*6) / 17 = 14/17 = .8235 vs KC's worst-case 12/17 = .7059.

    status = clinch.compute_clinches(wins, remaining, ties)[tested_team]
    # LV's ties must be counted as a real threat (via the doubled-points
    # comparison: LV's ceiling is 2*5+6 + 2*6 = 28 "points" vs KC's floor
    # of 2*12 = 24 "points") -- so KC must NOT show a guaranteed mark here.
    assert not status.division and not status.bye


def test_compute_clinches_ignores_ties_when_none_given_same_as_before():
    """Backward compatibility: existing callers (and this test module's
    other tests) that pass no `ties` argument at all must behave exactly
    as they did before this fix -- ties default to 0 for every team."""
    wins, remaining = _blank(wins=0, remaining=0)
    wins["KC"] = 13
    for t in TEAMS:
        if t.conference == "AFC" and t.abbr != "KC":
            wins[t.abbr] = 12
    status = clinch.compute_clinches(wins, remaining)["KC"]
    assert status.bye and status.berth and status.division and status.mark == "*"


def test_clinches_before_week_does_not_credit_a_tied_game_as_a_phantom_home_win(monkeypatch):
    """Regression test for a real bug the ties fix could otherwise leave
    behind: clinches_before_week() used to rebuild win counts from
    GameResult.winner, which game_sim.py always forces to "home" on a
    tied score -- silently crediting a home win here that season.records
    (post-fix) correctly does NOT credit anywhere. Monkeypatches
    compute_clinches to capture exactly the (wins, remaining, ties)
    dicts clinches_before_week() builds and hands it, so this checks the
    real function's own rebuilt state, not a reimplementation of it."""
    schedule = [
        [_game("KC", "LV", 20, 20)],  # a real tie -- GameResult.winner is still forced to "home"
        [WeekGame(home_abbr="DEN", away_abbr="LAC")],  # unplayed
    ]
    season = _season(schedule, {})

    captured = {}
    real_compute = clinch.compute_clinches

    def _capture(wins, remaining, ties=None):
        captured["wins"] = dict(wins)
        captured["ties"] = dict(ties) if ties else {}
        return real_compute(wins, remaining, ties)

    monkeypatch.setattr(clinch, "compute_clinches", _capture)
    clinch.clinches_before_week(season, 2)

    assert captured["wins"]["KC"] == 0 and captured["wins"]["LV"] == 0  # no phantom home win from the tie
    assert captured["ties"]["KC"] == 1 and captured["ties"]["LV"] == 1
