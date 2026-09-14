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
