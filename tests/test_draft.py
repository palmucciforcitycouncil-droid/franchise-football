"""
Tests for R5: Draft (docs/R5_DRAFT_SYSTEM_SPECIFICATION.md,
app/engine/draft.py). See that module's own docstring for the real,
disclosed scope decisions this implementation made (no new DB tables,
runs every season not just once, no live draft event).
"""
import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.core.db import DB_PATH
from app.engine import draft
from app.engine.draft import GROUP_BANDS, GROUP_POSITIONS
from app.models.coach import Coach, CoachRole, FOCUS_SCOUTING, FOCUS_DEVELOPMENT
from app.models.player import Position
from app.services.season_state import Season, WeekGame, TeamRecord
from app.engine.game_state import GameResult
from app.services import save_service, history_store, headlines_history, draft_store, undrafted_pool

DB_EXISTS = DB_PATH.exists()

save_service.DEFAULT_SAVE_PATH = Path("data/saves/_test_season_draft.json")
history_store.DEFAULT_PATH = Path("data/saves/_test_history_draft.json")
history_store.DEFAULT_PATH.unlink(missing_ok=True)
headlines_history.DEFAULT_PATH = Path("data/saves/_test_headlines_draft.json")
headlines_history.DEFAULT_PATH.unlink(missing_ok=True)
draft_store.DEFAULT_PATH = Path("data/saves/_test_draft_history.json")
draft_store.DEFAULT_PATH.unlink(missing_ok=True)
undrafted_pool.DEFAULT_PATH = Path("data/saves/_test_undrafted_pool.json")
undrafted_pool.DEFAULT_PATH.unlink(missing_ok=True)


# --- generation ---------------------------------------------------------------

def test_generate_draft_class_is_deterministic():
    a = draft.generate_draft_class(2025, 1)
    b = draft.generate_draft_class(2025, 1)
    assert [p.overall_rating for p in a] == [p.overall_rating for p in b]
    assert [p.first_name for p in a] == [p.first_name for p in b]


def test_generate_draft_class_differs_across_seasons():
    a = draft.generate_draft_class(2025, 1)
    b = draft.generate_draft_class(2025, 2)
    assert [p.overall_rating for p in a] != [p.overall_rating for p in b]


def test_generate_draft_class_respects_real_position_quota_bands():
    prospects = draft.generate_draft_class(2025, 1)
    counts = {}
    for p in prospects:
        counts[p.group] = counts.get(p.group, 0) + 1
    for group, (lo, hi) in GROUP_BANDS.items():
        assert lo <= counts.get(group, 0) <= hi, f"{group}: {counts.get(group, 0)} not in [{lo},{hi}]"


def test_generate_draft_class_only_uses_real_position_enum_values():
    prospects = draft.generate_draft_class(2025, 1)
    all_positions = {pos for positions in GROUP_POSITIONS.values() for pos in positions}
    assert all(p.position in all_positions for p in prospects)


def test_attributes_and_overall_are_within_real_bounds():
    prospects = draft.generate_draft_class(2025, 1)
    for p in prospects:
        assert 20 <= p.overall_rating <= 99
        assert p.overall_rating <= p.potential <= 99
        assert all(20 <= v <= 99 for v in p.attrs.values())


def test_position_profile_prospects_score_higher_on_their_own_key_attributes():
    """A real WR should end up with a real speed/catching-driven profile,
    not a uniform-random one -- checked against the OL profile's own key
    attributes (pass_block) as the contrast, not a fabricated threshold."""
    prospects = draft.generate_draft_class(2025, 1)
    wrs = [p for p in prospects if p.position.value == "WR"]
    ols = [p for p in prospects if p.group == "OL"]
    assert wrs and ols
    avg_wr_speed = sum(p.attrs["speed"] for p in wrs) / len(wrs)
    avg_ol_speed = sum(p.attrs["speed"] for p in ols) / len(ols)
    assert avg_wr_speed > avg_ol_speed


# --- rookie scale AAV -----------------------------------------------------------

def test_rookie_scale_aav_declines_by_pick():
    p1 = draft.rookie_scale_aav(1, season_number=0)
    p32 = draft.rookie_scale_aav(32, season_number=0)
    p100 = draft.rookie_scale_aav(100, season_number=0)
    p200 = draft.rookie_scale_aav(200, season_number=0)
    assert p1 > p32 > p100 > p200 > 0


def test_rookie_scale_aav_grows_with_the_real_cap_across_seasons():
    season0 = draft.rookie_scale_aav(1, season_number=24)  # 2026
    season3 = draft.rookie_scale_aav(1, season_number=27)
    assert season3 > season0


# --- draft order ------------------------------------------------------------------

def _game(home, away, home_score, away_score):
    result = GameResult(home_score=home_score, away_score=away_score,
                         winner="home" if home_score >= away_score else "away", events=[], plays=[])
    return WeekGame(home_abbr=home, away_abbr=away, result=result)


def test_compute_draft_order_puts_the_worst_record_first():
    schedule = [[_game("KC", "LV", 30, 10)], [_game("LV", "DEN", 10, 30)]]
    records = {
        "KC": TeamRecord(abbr="KC", location="KC", wins=5, losses=0),
        "LV": TeamRecord(abbr="LV", location="LV", wins=0, losses=5),
        "DEN": TeamRecord(abbr="DEN", location="DEN", wins=3, losses=2),
    }
    season = Season(league_seed=1, schedule=schedule, records=records)
    order = draft.compute_draft_order(season, league_seed=1, season_number=0)
    assert order[0] == "LV"  # worst record picks first
    assert order[-1] == "KC"  # best record picks last


def test_compute_draft_order_is_deterministic():
    schedule = [[_game("KC", "LV", 20, 20)]]
    records = {"KC": TeamRecord(abbr="KC", location="KC"), "LV": TeamRecord(abbr="LV", location="LV")}
    season = Season(league_seed=1, schedule=schedule, records=records)
    a = draft.compute_draft_order(season, 1, 0)
    b = draft.compute_draft_order(season, 1, 0)
    assert a == b


# --- R13 Sec 5.3: Scouting focus -> draft-evaluation noise ----------------------

def test_team_scouting_strength_is_zero_with_nobody_focused_there(monkeypatch):
    from app.services import coach_store as coach_store_module
    monkeypatch.setattr(coach_store_module, "has_coaches", lambda: True)
    monkeypatch.setattr(coach_store_module, "staff_for", lambda abbr: (
        Coach(coach_id="c1", first_name="A", last_name="B", role=CoachRole.HC,
              team_abbr=abbr, focus_area=FOCUS_DEVELOPMENT),
    ))
    assert draft.team_scouting_strength("ZZZ") == 0.0


def test_team_scouting_strength_increases_with_more_scouting_focused_coaches(monkeypatch):
    from app.services import coach_store as coach_store_module
    monkeypatch.setattr(coach_store_module, "has_coaches", lambda: True)
    one = (Coach(coach_id="c1", first_name="A", last_name="B", role=CoachRole.AC,
                  team_abbr="ZZZ", focus_area=FOCUS_SCOUTING),)
    two = one + (Coach(coach_id="c2", first_name="C", last_name="D", role=CoachRole.AC,
                        team_abbr="ZZZ", focus_area=FOCUS_SCOUTING),)

    monkeypatch.setattr(coach_store_module, "staff_for", lambda abbr: one)
    strength_one = draft.team_scouting_strength("ZZZ")
    monkeypatch.setattr(coach_store_module, "staff_for", lambda abbr: two)
    strength_two = draft.team_scouting_strength("ZZZ")
    assert strength_two > strength_one > 0.0


def test_hc_focused_scouting_outweighs_the_same_rating_on_an_assistant(monkeypatch):
    """Brian's own explicit design: "HC focus is more valuable than an
    assistant." Both coaches here have identical ratings (model defaults)
    -- only the role tier differs."""
    from app.services import coach_store as coach_store_module
    monkeypatch.setattr(coach_store_module, "has_coaches", lambda: True)
    hc = (Coach(coach_id="c1", first_name="A", last_name="B", role=CoachRole.HC,
                team_abbr="ZZZ", focus_area=FOCUS_SCOUTING),)
    ac = (Coach(coach_id="c1", first_name="A", last_name="B", role=CoachRole.AC,
                team_abbr="ZZZ", focus_area=FOCUS_SCOUTING),)

    monkeypatch.setattr(coach_store_module, "staff_for", lambda abbr: hc)
    hc_strength = draft.team_scouting_strength("ZZZ")
    monkeypatch.setattr(coach_store_module, "staff_for", lambda abbr: ac)
    ac_strength = draft.team_scouting_strength("ZZZ")
    assert hc_strength > ac_strength > 0.0


def test_perceived_overall_matches_true_overall_with_no_coach_system(monkeypatch):
    """Backward-compat guarantee: a database with no coach system at all
    (predating scripts/import_coaches.py) drafts exactly as it did before
    R13 -- zero noise, not R13's new baseline noise."""
    from app.services import coach_store as coach_store_module
    monkeypatch.setattr(coach_store_module, "has_coaches", lambda: False)
    prospects = draft.generate_draft_class(2025, 1)
    p = prospects[0]
    assert draft.perceived_overall(p, "ZZZ", league_seed=2025, season_number=1) == float(p.overall_rating)


def test_perceived_overall_is_deterministic(monkeypatch):
    from app.services import coach_store as coach_store_module
    monkeypatch.setattr(coach_store_module, "has_coaches", lambda: True)
    monkeypatch.setattr(coach_store_module, "staff_for", lambda abbr: ())
    prospects = draft.generate_draft_class(2025, 1)
    p = prospects[0]
    a = draft.perceived_overall(p, "ZZZ", league_seed=2025, season_number=1)
    b = draft.perceived_overall(p, "ZZZ", league_seed=2025, season_number=1)
    assert a == b


def test_perceived_overall_noise_shrinks_with_real_scouting_investment(monkeypatch):
    """Calibration proof (R13 Sec 8): a team with strong Scouting
    investment must evaluate prospects with LESS average error than a
    team with none, across many trials -- not just a single lucky draw."""
    from app.services import coach_store as coach_store_module
    monkeypatch.setattr(coach_store_module, "has_coaches", lambda: True)

    strong_scouts = tuple(
        Coach(coach_id=f"c{i}", first_name="A", last_name=str(i), role=CoachRole.AC,
              team_abbr="ZZZ", focus_area=FOCUS_SCOUTING, reputation=95)
        for i in range(5)
    )
    prospects = draft.generate_draft_class(2025, 1)[:50]

    monkeypatch.setattr(coach_store_module, "staff_for", lambda abbr: ())
    errors_none = [abs(draft.perceived_overall(p, "ZZZ", 2025, 1) - p.overall_rating) for p in prospects]

    monkeypatch.setattr(coach_store_module, "staff_for", lambda abbr: strong_scouts)
    errors_strong = [abs(draft.perceived_overall(p, "ZZZ", 2025, 1) - p.overall_rating) for p in prospects]

    assert sum(errors_strong) / len(errors_strong) < sum(errors_none) / len(errors_none)


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_simulate_draft_accepts_the_new_required_seed_params():
    """Regression: simulate_draft()'s signature grew league_seed/
    season_number (needed for the deterministic scouting-noise seed) --
    this just confirms the call still works end to end with a tiny class."""
    prospects = draft.generate_draft_class(2025, 1)[:10]
    result = draft.simulate_draft(prospects, ["KC"], league_seed=2025, season_number=1, rounds=1)
    assert len(result.picks) == 1


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_simulate_draft_respects_a_real_traded_pick(monkeypatch):
    """Draft-Pick Trading (GDD Sec 8.5): once KC's round-1 slot is traded
    to BUF, BUF -- not KC -- actually makes that pick."""
    from app.services import draft_pick_store

    # simulate_draft() reads the whole season's ownership once up front via
    # owners_for_season() (the same "fetch once" precedent as this file's
    # own _all_teams_group_counts()), not a per-pick owner_of() call --
    # mock that bulk entry point instead.
    monkeypatch.setattr(draft_pick_store, "owners_for_season",
                         lambda season_number, path=None: {(1, "KC"): "BUF"})

    prospects = draft.generate_draft_class(2025, 1)
    order = ["KC", "BUF", "SF"]
    result = draft.simulate_draft(prospects, order, league_seed=2025, season_number=1, rounds=1)
    picks_by_slot = {(p.round, i): p for i, p in enumerate(result.picks)}
    # KC's own slot (index 0, round 1) was traded to BUF -- BUF should be
    # credited with TWO picks this round (their own + KC's), KC with none.
    team_abbrs_this_round = [p.team_abbr for p in result.picks]
    assert team_abbrs_this_round.count("BUF") == 2
    assert team_abbrs_this_round.count("KC") == 0


def test_estimated_pick_order_rank_and_pick_value_are_pure_and_real():
    """Sanity check that both real building blocks Draft-Pick Trading
    depends on (app/engine/trades.py's pick_trade_value()) are wired to
    the real chart/real live standings, not stubs."""
    from app.services.season_state import Season, TeamRecord
    season = Season(league_seed=1, schedule=[], records={
        "AA": TeamRecord(abbr="AA", location="AA", wins=0, losses=10),
        "BB": TeamRecord(abbr="BB", location="BB", wins=10, losses=0),
    })
    assert draft.estimated_pick_order_rank(season, "AA") == 1
    assert draft.pick_value(1, draft.estimated_pick_order_rank(season, "AA")) == 3000


# --- pick simulation (needs the real DB for _team_needs) -------------------------

@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_simulate_draft_assigns_every_pick_to_a_real_team_across_seven_rounds():
    prospects = draft.generate_draft_class(2025, 1)
    order = ["KC", "BUF", "SF"]
    result = draft.simulate_draft(prospects, order, league_seed=2025, season_number=1, rounds=7)
    assert len(result.picks) == len(order) * 7
    for i, pick in enumerate(result.picks, start=1):
        assert pick.overall_pick == i
        assert pick.round == ((i - 1) // len(order)) + 1
    picked_indexes = {p.prospect_index for p in result.picks}
    assert len(picked_indexes) == len(result.picks)  # no prospect drafted twice
    assert set(picked_indexes) | set(result.undrafted_indexes) == {p.index for p in prospects}


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_run_draft_for_season_creates_real_rostered_players_with_rookie_contracts():
    from app.core import db as db_module
    from app.models.player import Player
    import shutil

    real_db_path = db_module.DB_PATH
    temp_db_path = Path("data/_test_draft_roster.db")
    shutil.copyfile(real_db_path, temp_db_path)
    db_module.DB_PATH = temp_db_path
    db_module._engine = None
    try:
        from app.services import season_state
        season_state.reset_season()
        season = season_state.get_season()

        summary = draft.run_draft_for_season(season, season_number=99)
        assert summary["drafted"] > 0
        assert summary["undrafted"] > 0

        stored = draft_store.get_draft(99)
        assert stored is not None
        assert len(stored["picks"]) == summary["drafted"]

        from app.core.db import get_session
        with get_session() as s:
            first_pick = stored["picks"][0]
            player = s.get(Player, first_pick["player_id"])
            assert player is not None
            assert player.team_abbr == first_pick["team_abbr"]
            assert player.contract_years_remaining == 4
            assert player.salary > 0
            assert player.years_pro == 0
    finally:
        if db_module._engine is not None:
            db_module._engine.dispose()
        db_module.DB_PATH = real_db_path
        db_module._engine = None
        temp_db_path.unlink(missing_ok=True)


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_run_draft_for_season_consumes_that_seasons_pick_inventory():
    """Draft-Pick Trading (GDD Sec 8.5): once a season's real draft
    actually runs, its picks are no longer a tradeable future asset."""
    from app.core import db as db_module
    from app.services import draft_pick_store
    import shutil

    real_db_path = db_module.DB_PATH
    temp_db_path = Path("data/_test_draft_pick_consume.db")
    shutil.copyfile(real_db_path, temp_db_path)
    db_module.DB_PATH = temp_db_path
    db_module._engine = None
    try:
        from app.services import season_state
        season_state.reset_season()
        season = season_state.get_season()

        draft_pick_store.ensure_lookahead_seeded(50)
        assert any(p.season_number == 50 for p in draft_pick_store.all_picks())

        draft.run_draft_for_season(season, season_number=50)

        assert not any(p.season_number == 50 for p in draft_pick_store.all_picks())
    finally:
        if db_module._engine is not None:
            db_module._engine.dispose()
        db_module.DB_PATH = real_db_path
        db_module._engine = None
        temp_db_path.unlink(missing_ok=True)


# --- positional draft value (Brian's 2026-09-14 report: K at #2, P at #5) -------

_TEAMS_32 = [f"T{i:02d}" for i in range(32)]
# A realistic league: every team carries exactly one K and one P (the case
# that used to make both of them a "top-3 need" for every team).
_REALISTIC_COUNTS = {"QB": 3, "RB": 5, "WR": 6, "TE": 4, "OL": 10, "DL": 11, "LB": 6, "CB": 7, "S": 5, "K": 1, "P": 1}


def _league_counts(seed: int) -> dict[str, dict[str, int]]:
    """Deterministic, realistically varied roster depth per team (+-2 around
    the league average per group; exactly one K and one P each)."""
    import random
    rng = random.Random(seed)
    return {
        t: {g: (c if g in ("K", "P") else max(1, c + rng.randint(-2, 2))) for g, c in _REALISTIC_COUNTS.items()}
        for t in _TEAMS_32
    }


def _mock_draft_environment(monkeypatch, counts_seed: int = 0):
    from app.services import draft_pick_store, coach_store as coach_store_module
    monkeypatch.setattr(draft_pick_store, "owners_for_season", lambda season_number, path=None: {})
    monkeypatch.setattr(draft, "_all_teams_group_counts", lambda: _league_counts(counts_seed))
    monkeypatch.setattr(coach_store_module, "has_coaches", lambda: True)
    monkeypatch.setattr(coach_store_module, "staff_for", lambda abbr: ())


def test_simulated_drafts_keep_specialists_late_and_value_premium_positions(monkeypatch):
    """Acceptance criteria for Brian's report: across several full,
    deterministic 7-round drafts, no K/P in the first 100 overall picks,
    none before round 5, at most SPECIALISTS_MAX_PER_ROUND per round, and a
    real share of round 1 spent on QB/EDGE/T/CB."""
    premium_total = 0
    classes = [(2025, 1), (2025, 2), (7, 25), (123, 30), (99, 26), (5, 27)]
    for i, (league_seed, season_number) in enumerate(classes):
        _mock_draft_environment(monkeypatch, counts_seed=i)
        prospects = draft.generate_draft_class(league_seed, season_number)
        by_index = {p.index: p for p in prospects}
        result = draft.simulate_draft(prospects, _TEAMS_32, league_seed=league_seed, season_number=season_number)
        assert len(result.picks) == 32 * draft.ROUNDS

        early = [by_index[pk.prospect_index].position for pk in result.picks if pk.overall_pick <= 100]
        assert Position.K not in early and Position.P not in early

        for rnd in range(1, draft.ROUNDS + 1):
            specialists = [pk for pk in result.picks if pk.round == rnd
                           and by_index[pk.prospect_index].position in draft.SPECIALIST_POSITIONS]
            assert len(specialists) <= draft.SPECIALISTS_MAX_PER_ROUND
            if rnd < draft.SPECIALIST_EARLIEST_ROUND:
                assert specialists == []

        round_one = [by_index[pk.prospect_index].position for pk in result.picks if pk.round == 1]
        premium = sum(1 for pos in round_one if pos in (Position.QB, Position.EDGE, Position.T, Position.CB))
        assert premium >= 6, f"only {premium}/32 premium-position picks in round 1: {round_one}"
        premium_total += premium
    # QB/EDGE/T/CB are ~26% of a generated class; value weighting should
    # push their round-1 share clearly above that.
    assert premium_total / (32 * len(classes)) >= 0.33


def test_live_resolve_one_pick_obeys_the_same_specialist_rule(monkeypatch):
    _mock_draft_environment(monkeypatch)
    prospects = draft.generate_draft_class(2025, 1)
    by_index = {p.index: p for p in prospects}
    # A team with NO kicker or punter at all -- the strongest possible need.
    counts = {"T00": {**_REALISTIC_COUNTS, "K": 0, "P": 0}}
    for rnd in range(1, draft.SPECIALIST_EARLIEST_ROUND):
        pick = draft.resolve_one_pick(by_index, set(), "T00", {k: dict(v) for k, v in counts.items()}, round_num=rnd)
        assert pick.position not in draft.SPECIALIST_POSITIONS
    # ...and the per-round quota still blocks one once it's used up.
    pick = draft.resolve_one_pick(by_index, set(), "T00", {k: dict(v) for k, v in counts.items()},
                                  round_num=draft.SPECIALIST_EARLIEST_ROUND,
                                  specialists_taken_this_round=draft.SPECIALISTS_MAX_PER_ROUND)
    assert pick.position not in draft.SPECIALIST_POSITIONS


def test_needs_are_relative_to_typical_depth_not_raw_count():
    needs = draft._needs_from_counts(dict(_REALISTIC_COUNTS))
    assert "K" not in needs[:3] and "P" not in needs[:3]
    assert draft._needs_from_counts({**_REALISTIC_COUNTS, "QB": 1})[0] == "QB"


def test_fullbacks_count_toward_the_rb_group():
    assert draft._group_for(Position.FB) == "RB"


def test_projected_rounds_follow_draft_value_and_never_project_a_specialist_early():
    prospects = draft.generate_draft_class(2025, 1)
    proj = draft.projected_rounds(prospects)
    assert set(proj) == {p.index for p in prospects}
    for p in prospects:
        if p.position in draft.SPECIALIST_POSITIONS and proj[p.index] is not None:
            assert proj[p.index] >= draft.SPECIALIST_EARLIEST_ROUND
    ranked = sorted(prospects, key=lambda p: -draft.draft_value(p))
    assert proj[ranked[0].index] == 1
    assert sum(1 for r in proj.values() if r == 1) == 32


def test_drafted_player_gets_acquisition_fields_and_undrafted_does_not():
    prospect = draft.generate_draft_class(2025, 1)[0]
    drafted = draft._prospect_to_player(prospect, 2025, 25, "KC", 1_000_000, 4, draft_round=2, overall_pick=40)
    assert drafted.acquisition_type == "Draft"
    assert drafted.acquisition_season == 2027
    assert drafted.acquisition_round == 2 and drafted.acquisition_pick == 40
    undrafted = draft._prospect_to_player(prospect, 2025, 25, None, draft.LEAGUE_MINIMUM_BASE, 1)
    assert undrafted.acquisition_type is None and undrafted.acquisition_season is None


# --- undrafted pool expiration --------------------------------------------------

def test_undrafted_pool_add_and_expire_after_three_offseasons():
    undrafted_pool.add_undrafted(["p1", "p2"])
    assert undrafted_pool.years_remaining("p1") == 3

    # Years 3 -> 2 -> 1 -> 0: expires on the 3rd decrement, real Player
    # rows don't exist for these fake ids, so the DB-delete branch just
    # no-ops (player is None) -- exercised for real in the end-to-end test.
    undrafted_pool.decrement_and_expire()
    assert undrafted_pool.years_remaining("p1") == 2
    undrafted_pool.decrement_and_expire()
    assert undrafted_pool.years_remaining("p1") == 1
    expired = undrafted_pool.decrement_and_expire()
    assert "p1" in expired and "p2" in expired
    assert undrafted_pool.years_remaining("p1") is None


def test_undrafted_pool_remove_is_a_safe_noop_for_an_untracked_player():
    undrafted_pool.remove("not-in-the-pool")  # must not raise
