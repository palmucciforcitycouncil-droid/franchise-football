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


# --- pick simulation (needs the real DB for _team_needs) -------------------------

@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_simulate_draft_assigns_every_pick_to_a_real_team_across_seven_rounds():
    prospects = draft.generate_draft_class(2025, 1)
    order = ["KC", "BUF", "SF"]
    result = draft.simulate_draft(prospects, order, rounds=7)
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
