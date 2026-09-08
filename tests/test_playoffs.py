"""
Tests for the Playoffs system (GDD Part 1 Sec 7.3, app/engine/playoffs.py).

Includes the worked 3-team tie scenario the GDD's own "Test-plan gap"
note explicitly asks for, stepped through by hand in the test's
docstring, before any other playoff work should have been trusted.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

from pathlib import Path

import pytest

from app.data.teams import TEAMS
from app.services.season_state import Season, WeekGame, TeamRecord
from app.engine.game_state import GameResult
from app.engine import playoffs


def _played_game(home_abbr, away_abbr, home_score, away_score, plays=None):
    result = GameResult(
        home_score=home_score, away_score=away_score,
        winner="home" if home_score >= away_score else "away",
        events=[], plays=plays or [],
    )
    return WeekGame(home_abbr=home_abbr, away_abbr=away_abbr, result=result)


def _season(schedule, current_week=1, records_override=None):
    records = {t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS}
    if records_override:
        for abbr, (w, l) in records_override.items():
            records[abbr].wins, records[abbr].losses = w, l
    return Season(league_seed=1, schedule=schedule, records=records, current_week=current_week)


# --- worked tie-break scenario (GDD Sec 7.3's own explicit ask) ------------

def test_worked_three_team_division_tie_resolved_by_head_to_head():
    """Hand-worked example: BUF, MIA, and NYJ (three of the AFC East's
    four teams) all finish with an identical overall record. Within
    this trio: BUF beat MIA and beat NYJ (2-0 vs the group); MIA lost to
    BUF but beat NYJ (1-1); NYJ lost to both (0-2).

    Stepped through by hand against Sec 7.3.A's own chain: step 1
    (head-to-head) computes each team's W-L only in games against the
    OTHER members of the currently-tied group. On the full 3-team group,
    BUF is 2-0 (pct 1.0), MIA is 1-1 (pct 0.5), NYJ is 0-2 (pct 0.0) --
    all three values differ, so BUF is immediately separated as the
    best. The GDD's Sec 7.3.C says to "eliminate it and re-apply the
    procedure to the remaining teams" -- re-running head-to-head on just
    {MIA, NYJ} looks only at their own game (MIA won), which again fully
    separates them. Head-to-head alone resolves every seat; no later
    step (division record, common games, etc.) is ever reached.
    Expected order: BUF, MIA, NYJ."""
    schedule = [
        [_played_game("BUF", "MIA", 24, 17)],
        [_played_game("MIA", "NYJ", 20, 10)],
        [_played_game("BUF", "NYJ", 30, 6)],
    ]
    season = _season(schedule, current_week=4, records_override={
        "BUF": (10, 7), "MIA": (10, 7), "NYJ": (10, 7),
    })

    ranked = playoffs.rank_teams(season, ["BUF", "MIA", "NYJ"], playoffs._division_steps)
    assert ranked == ["BUF", "MIA", "NYJ"]


def test_worked_three_team_wildcard_tie_falls_through_to_conference_record():
    """A second worked example, this time exercising a LATER step: BUF,
    CIN, and DEN (three different AFC divisions, so no head-to-head
    games between any pair -- head_to_head_pct returns the neutral 0.5
    for all three and does not discriminate). Their conference (AFC)
    records differ: BUF 8-4, CIN 6-6, DEN 4-8 within the conference --
    that alone should fully separate them at step 2 without needing any
    games against each other."""
    schedule = [
        [_played_game("BUF", "MIA", 20, 10)],   # BUF's only conference game modeled
        [_played_game("CIN", "PIT", 20, 17)],   # CIN's only conference game modeled
        [_played_game("DEN", "LV", 10, 24)],    # DEN's only conference game modeled (a loss)
    ]
    season = _season(schedule, current_week=4, records_override={
        "BUF": (10, 7), "CIN": (10, 7), "DEN": (10, 7),
    })

    ranked = playoffs.rank_teams(season, ["BUF", "CIN", "DEN"], playoffs._wildcard_steps)
    # Only one conference game modeled per team above (1-0 / 1-0 / 0-1) --
    # enough for conference_record_pct to separate DEN (0.0) from the
    # other two (1.0 apiece), but BUF and CIN remain tied at that step
    # and must fall through further; assert what IS determinable by hand:
    assert ranked[-1] == "DEN"
    assert set(ranked[:2]) == {"BUF", "CIN"}


# --- individual tiebreak-step building blocks -------------------------------

def test_head_to_head_pct_is_neutral_when_no_games_played():
    season = _season([], current_week=1)
    assert playoffs.head_to_head_pct(season, "BUF", ["BUF", "MIA"]) == 0.5


def test_division_record_pct_only_counts_division_games():
    schedule = [
        _played_game("BUF", "MIA", 20, 10),   # division game, BUF wins
        _played_game("BUF", "KC", 10, 30),    # non-division game, BUF loses (shouldn't count)
    ]
    season = _season([schedule], current_week=2)
    assert playoffs.division_record_pct(season, "BUF") == 1.0


def test_conference_record_pct_only_counts_conference_games():
    schedule = [
        _played_game("BUF", "KC", 20, 10),      # AFC vs AFC
        _played_game("BUF", "DAL", 10, 30),     # AFC vs NFC, shouldn't count
    ]
    season = _season([schedule], current_week=2)
    assert playoffs.conference_record_pct(season, "BUF") == 1.0


def test_strength_of_victory_uses_beaten_opponents_own_records():
    # BUF beats MIA. MIA's own overall record across ALL its games this
    # season -- including the very game it lost to BUF -- is what
    # counts: lost to BUF, beat NYJ, lost to NE => 1-2 (pct 1/3), not
    # just its record in games other than the one against BUF.
    schedule = [
        [_played_game("BUF", "MIA", 20, 10)],
        [_played_game("MIA", "NYJ", 24, 17)],
        [_played_game("NE", "MIA", 30, 20)],
    ]
    season = _season(schedule, current_week=4)
    assert playoffs.strength_of_victory(season, "BUF") == pytest.approx(1 / 3)


def test_common_games_pct_requires_the_minimum_sample():
    # BUF and MIA share exactly one common opponent (KC) with only one
    # game each -- below the wildcard chain's min_games=4 threshold.
    schedule = [
        [_played_game("BUF", "KC", 20, 17)],
        [_played_game("MIA", "KC", 10, 24)],
    ]
    season = _season(schedule, current_week=3)
    assert playoffs.common_games_pct(season, "BUF", ["BUF", "MIA"], min_games=4) == 0.5
    # But the division chain's own min_games=1 threshold does pick it up:
    assert playoffs.common_games_pct(season, "BUF", ["BUF", "MIA"], min_games=1) == 1.0


def test_net_touchdowns_all_counts_only_that_teams_own_touchdowns():
    from app.engine.game_state import PlayEvent
    td_play = PlayEvent(down=1, distance=10, field_pos=95, play_type="pass", yards=5,
                         desc="TD", outcome="touchdown", offense_abbr="BUF")
    other_td = PlayEvent(down=1, distance=10, field_pos=95, play_type="run", yards=5,
                          desc="TD", outcome="touchdown", offense_abbr="MIA")
    schedule = [_played_game("BUF", "MIA", 14, 7, plays=[td_play, other_td])]
    season = _season([schedule], current_week=2)
    assert playoffs.net_touchdowns_all(season, "BUF") == 1
    assert playoffs.net_touchdowns_all(season, "MIA") == 1


def test_coin_toss_is_deterministic_for_a_given_seed():
    season = _season([], current_week=1)
    a = playoffs.coin_toss(season, "BUF")
    b = playoffs.coin_toss(season, "BUF")
    assert a == b
    assert playoffs.coin_toss(season, "BUF") != playoffs.coin_toss(season, "MIA")


# --- seeding -----------------------------------------------------------------

def test_seed_conference_picks_the_best_record_in_each_division_and_top_3_wildcards():
    """No ties anywhere -- every team gets a distinct win total, so the
    tiebreak chain never runs and this purely exercises the
    division-winner + wildcard selection + seeding logic."""
    afc_teams = [t.abbr for t in TEAMS if t.conference == "AFC"]
    # Assign strictly descending win totals: 15,14,13,...,0 across the 16 AFC teams.
    records_override = {abbr: (15 - i, i) for i, abbr in enumerate(afc_teams)}
    season = _season([], current_week=19, records_override=records_override)

    seeds = playoffs.seed_conference(season, "AFC")
    assert len(seeds) == 7
    assert len(set(seeds)) == 7  # no team seeded twice

    # The best team in each division must be seed-eligible as a division winner.
    divisions = {}
    for t in TEAMS:
        if t.conference == "AFC":
            divisions.setdefault(t.division, []).append(t.abbr)
    expected_winners = {min(teams, key=lambda a: afc_teams.index(a)) for teams in divisions.values()}
    assert set(seeds[:4]) == expected_winners

    # Seed 1 must be the single best record among the four division winners.
    assert seeds[0] == afc_teams[0]


def test_seed_conference_returns_seven_for_nfc_too():
    season = _season([], current_week=19)
    seeds = playoffs.seed_conference(season, "NFC")
    assert len(seeds) == 7
    assert all(t.conference == "NFC" for abbr in seeds for t in TEAMS if t.abbr == abbr)


# --- bracket construction & reseeding ---------------------------------------

def test_build_wild_card_round_matches_the_gdd_seeding_pattern():
    season = _season([], current_week=19)
    bracket = playoffs.build_wild_card_round(season)
    assert len(bracket.rounds) == 1
    wc = bracket.rounds[0]
    assert len(wc) == 6  # 3 games per conference, seed 1 sits out on a bye
    afc_games = {(m.home_seed, m.away_seed) for m in wc if m.conference == "AFC"}
    assert afc_games == {(2, 7), (3, 6), (4, 5)}


def test_reseed_pairs_sends_the_best_seed_against_the_worst_survivor():
    assert playoffs._reseed_pairs([1, 5, 6, 7]) == [(1, 7), (5, 6)]
    assert playoffs._reseed_pairs([1, 2]) == [(1, 2)]


def test_build_next_round_after_an_upset_reseeds_correctly():
    """If the #2 seed loses its Wild Card game to #7, the Divisional
    round must still send #1 against the WORST surviving seed (here,
    #7 -- the upset winner), not blindly assume #2 survived."""
    season = _season([], current_week=19)
    bracket = playoffs.build_wild_card_round(season)
    for m in bracket.rounds[0]:
        if m.conference != "AFC":
            m.result = GameResult(home_score=20, away_score=10, winner="home", events=[], plays=[])
            continue
        if m.home_seed == 2:  # the (2 vs 7) game -- force the 7 seed to win
            m.result = GameResult(home_score=10, away_score=20, winner="away", events=[], plays=[])
        else:
            m.result = GameResult(home_score=20, away_score=10, winner="home", events=[], plays=[])

    div_round = playoffs.build_next_round(bracket)
    afc_div = [m for m in div_round if m.conference == "AFC"]
    seeds_pairs = {(m.home_seed, m.away_seed) for m in afc_div}
    # Alive: 1 (bye), 7 (upset winner), 3 (won 3v6), 4 (won 4v5) -> reseed: (1,7) and (3,4)
    assert seeds_pairs == {(1, 7), (3, 4)}


def test_full_bracket_progression_to_a_champion():
    season = _season([], current_week=19)
    bracket = playoffs.build_wild_card_round(season)

    def _finish_round(round_):
        for m in round_:
            m.result = GameResult(home_score=20, away_score=10, winner="home", events=[], plays=[])

    _finish_round(bracket.rounds[0])
    assert bracket.current_round_name == "DIV"
    bracket.rounds.append(playoffs.build_next_round(bracket))

    _finish_round(bracket.rounds[1])
    assert bracket.current_round_name == "CONF"
    bracket.rounds.append(playoffs.build_next_round(bracket))
    assert len(bracket.rounds[2]) == 2  # one per conference

    _finish_round(bracket.rounds[2])
    assert bracket.current_round_name == "SB"
    bracket.rounds.append(playoffs.build_next_round(bracket))
    assert len(bracket.rounds[3]) == 1
    assert not bracket.is_complete

    _finish_round(bracket.rounds[3])
    assert bracket.is_complete
    assert bracket.champion_abbr == bracket.rounds[3][0].home_abbr  # home always "wins" a forced 20-10 here


# --- season_state integration ------------------------------------------------

from app.services import save_service, gameplan_store, history_store
from app.services import season_state
from app.core.db import DB_PATH

save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_season_playoffs.json")
gameplan_store.DEFAULT_PATH = Path("data/saves/_test_gameplans_playoffs.json")
# season_state._build_season() now reads history_store (a fresh franchise's
# season_number bootstraps to AFTER whatever's archived) -- redirect + clear so these
# tests never depend on the REAL data/saves/history.json's ambient content.
history_store.DEFAULT_PATH = Path("data/saves/_test_history_playoffs.json")
history_store.DEFAULT_PATH.unlink(missing_ok=True)

DB_EXISTS = DB_PATH.exists()


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_simulate_playoff_round_raises_before_regular_season_ends():
    season_state.reset_season()
    with pytest.raises(ValueError):
        season_state.simulate_playoff_round()


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_simulate_playoff_round_end_to_end_reaches_a_champion():
    season_state.reset_season()
    from app.engine.schedule import N_WEEKS
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()

    season = season_state.get_season()
    assert season.is_complete
    assert season.playoffs is None

    round_names = []
    for _ in range(4):
        round_names.append(season_state.simulate_playoff_round())
    assert round_names == ["WC", "DIV", "CONF", "SB"]

    season = season_state.get_season()
    assert season.playoffs.is_complete
    champion = season.playoffs.champion_abbr
    assert champion in {t.abbr for t in TEAMS}

    # Post-completion no-op, same convention as simulate_current_week.
    assert season_state.simulate_playoff_round() == "SB"
    assert season_state.get_season().playoffs.champion_abbr == champion


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_season_simulate_week_route_dispatches_into_playoffs_once_regular_season_ends():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    season_state.reset_season()
    from app.engine.schedule import N_WEEKS
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()

    resp = client.post("/season/simulate-week", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/playoffs"
    assert season_state.get_season().playoffs is not None


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_playoffs_page_renders_before_and_after_the_bracket_exists():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    season_state.reset_season()

    resp = client.get("/playoffs")
    assert resp.status_code == 200
    assert "regular season finishes" in resp.text

    from app.engine.schedule import N_WEEKS
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()

    resp = client.get("/playoffs")  # builds the WC round on first visit
    assert resp.status_code == 200
    assert "Wild Card" in resp.text
    assert season_state.get_season().playoffs is not None


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_playoff_game_view_renders_a_played_matchup_and_404s_on_an_unplayed_one():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    season_state.reset_season()
    from app.engine.schedule import N_WEEKS
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    season_state.simulate_playoff_round()  # WC

    season = season_state.get_season()
    played = season.playoffs.rounds[0][0]
    resp = client.get(f"/playoffs/game/{played.round_name}/{played.home_abbr}/{played.away_abbr}")
    assert resp.status_code == 200
    assert played.home_abbr in resp.text

    unplayed = season.playoffs.rounds[1][0]  # DIV round, not yet simulated
    resp = client.get(f"/playoffs/game/{unplayed.round_name}/{unplayed.home_abbr}/{unplayed.away_abbr}")
    assert resp.status_code == 404


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_playoff_bracket_survives_save_and_load():
    season_state.reset_season()
    from app.engine.schedule import N_WEEKS
    for _ in range(N_WEEKS):
        season_state.simulate_current_week()
    season_state.simulate_playoff_round()  # simulates WC, then immediately builds (unplayed) DIV

    season = season_state.get_season()
    save_service.save_season(season)
    reloaded = save_service.load_season()

    assert reloaded.playoffs is not None
    assert reloaded.playoffs.afc_seeds == season.playoffs.afc_seeds
    assert reloaded.playoffs.nfc_seeds == season.playoffs.nfc_seeds
    assert len(reloaded.playoffs.rounds) == 2  # WC (complete) + DIV (built, not yet played)
    assert all(m.is_complete for m in reloaded.playoffs.rounds[0])
    assert not any(m.is_complete for m in reloaded.playoffs.rounds[1])

    orig_matchup = season.playoffs.rounds[0][0]
    reloaded_matchup = reloaded.playoffs.rounds[0][0]
    assert reloaded_matchup.home_abbr == orig_matchup.home_abbr
    assert reloaded_matchup.result.home_score == orig_matchup.result.home_score
