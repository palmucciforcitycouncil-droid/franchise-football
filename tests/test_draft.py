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
    season0 = draft.rookie_scale_aav(1, season_number=0)
    season3 = draft.rookie_scale_aav(1, season_number=3)
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

    monkeypatch.setattr(draft_pick_store, "owner_of",
                         lambda season_number, round, original_team_abbr, path=None:
                             "BUF" if (round, original_team_abbr) == (1, "KC") else original_team_abbr)

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
