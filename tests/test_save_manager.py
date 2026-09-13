"""
Tests for app/services/save_manager.py -- multi-save-game management
(start new / save / load / rename / delete named franchise saves).

Requires the imported roster DB (used as the throwaway "template" every
new save is seeded from, copied into a tmp_path so these tests never
touch the real data/franchise_template.db) -- skips if it hasn't been
built yet, same convention as every other DB-backed test file here.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.db import DB_PATH
from app.core import db as db_module
from app.main import app
from app.services import (
    save_manager, save_service, season_state, history_store, power_rank_history,
    gameplan_store, award_race_history, owner_pressure_store, team_expectations, depth_chart_overrides,
)

DB_EXISTS = DB_PATH.exists()
pytestmark = pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_template(tmp_path):
    """Every test gets its own throwaway template DB (a real copy of
    the actual roster DB, never mutated) and its own registry/saves
    root -- conftest.py's own session-scoped isolation already redirects
    save_manager.REGISTRY_PATH/SAVES_ROOT, but each test still needs a
    FRESH root so saves from one test can't leak into the next.

    save_manager.create_save()/load_save() reassign EVERY module-level
    DEFAULT_PATH this app has (that's the whole point of the module) --
    including several conftest.py only isolates SESSION-wide (save_
    service, power_rank_history, owner_pressure_store, team_expectations,
    award_race_history) or not at all (history_store, gameplan_store,
    depth_chart_overrides). Left unrestored, a save created HERE would
    leak its now-deleted tmp_path into every test file that runs after
    this one. Captured and restored the same explicit way tests/
    conftest.py's own fixtures already do for the ones they DO own."""
    template_path = tmp_path / "template.db"
    shutil.copy(db_module.DB_PATH, template_path)

    originals = {
        "TEMPLATE_DB_PATH": save_manager.TEMPLATE_DB_PATH,
        "REGISTRY_PATH": save_manager.REGISTRY_PATH,
        "SAVES_ROOT": save_manager.SAVES_ROOT,
        "db_path": db_module.DB_PATH,
        "save_service": save_service.DEFAULT_SAVE_PATH,
        "history_store": history_store.DEFAULT_PATH,
        "power_rank_history": power_rank_history.DEFAULT_PATH,
        "gameplan_store": gameplan_store.DEFAULT_PATH,
        "award_race_history": award_race_history.DEFAULT_PATH,
        "owner_pressure_store": owner_pressure_store.DEFAULT_PATH,
        "team_expectations": team_expectations.DEFAULT_PATH,
        "depth_chart_overrides": depth_chart_overrides.DEFAULT_PATH,
    }
    save_manager.TEMPLATE_DB_PATH = template_path
    save_manager.REGISTRY_PATH = tmp_path / "registry.json"
    save_manager.SAVES_ROOT = tmp_path / "games"
    try:
        yield
    finally:
        save_manager.TEMPLATE_DB_PATH = originals["TEMPLATE_DB_PATH"]
        save_manager.REGISTRY_PATH = originals["REGISTRY_PATH"]
        save_manager.SAVES_ROOT = originals["SAVES_ROOT"]
        if db_module._engine is not None:
            db_module._engine.dispose()
        db_module.DB_PATH = originals["db_path"]
        db_module._engine = None
        db_module._engine_path = None
        save_service.DEFAULT_SAVE_PATH = originals["save_service"]
        history_store.DEFAULT_PATH = originals["history_store"]
        power_rank_history.DEFAULT_PATH = originals["power_rank_history"]
        gameplan_store.DEFAULT_PATH = originals["gameplan_store"]
        award_race_history.DEFAULT_PATH = originals["award_race_history"]
        owner_pressure_store.DEFAULT_PATH = originals["owner_pressure_store"]
        team_expectations.DEFAULT_PATH = originals["team_expectations"]
        depth_chart_overrides.DEFAULT_PATH = originals["depth_chart_overrides"]
        season_state._season = None
        from app.services import coach_store, depth_chart, injury_store
        coach_store.clear_cache()
        depth_chart.clear_starters_cache()
        injury_store.clear_cache()
        history_store.clear_career_stats_cache()
        owner_pressure_store.clear_cache()
        team_expectations.clear_cache()


def test_no_saves_initially():
    assert save_manager.list_saves() == []
    assert save_manager.get_active_save_id() is None
    assert not save_manager.has_active_save()


def test_create_save_makes_it_active_and_redirects_every_global():
    save_id = save_manager.create_save("Test Franchise")

    assert save_manager.get_active_save_id() == save_id
    assert save_manager.has_active_save()
    saves = save_manager.list_saves()
    assert len(saves) == 1
    assert saves[0].name == "Test Franchise"

    save_dir = save_manager._save_dir(save_id)
    assert db_module.DB_PATH == save_dir / "franchise.db"
    assert db_module.DB_PATH.exists()
    assert save_service.DEFAULT_SAVE_PATH == save_dir / "season.json"


def test_create_save_raises_without_a_template():
    save_manager.TEMPLATE_DB_PATH = Path("nonexistent_template.db")
    with pytest.raises(RuntimeError):
        save_manager.create_save("Should Fail")


def test_two_saves_are_fully_independent():
    save_a = save_manager.create_save("Save A")
    season_state.reset_season()
    season_state.set_user_team("KC")
    season_state.simulate_current_week()

    save_b = save_manager.create_save("Save B")
    season_state.reset_season()
    season_state.set_user_team("BUF")

    assert season_state.get_season().user_team_abbr == "BUF"

    save_manager.load_save(save_a)
    assert season_state.get_season().user_team_abbr == "KC"
    assert season_state.get_season().current_week == 2  # the week it simulated before switching

    save_manager.load_save(save_b)
    assert season_state.get_season().user_team_abbr == "BUF"


def test_sync_active_save_summary_reflects_real_progress():
    save_manager.create_save("Progress Test")
    season_state.reset_season()
    season_state.set_user_team("KC")
    season_state.simulate_current_week()

    meta = save_manager.list_saves()[0]
    assert meta.user_team_abbr == "KC"
    assert meta.current_week == 2
    assert meta.season_number == 0


def test_rename_save():
    save_id = save_manager.create_save("Old Name")
    save_manager.rename_save(save_id, "New Name")
    assert save_manager.list_saves()[0].name == "New Name"


def test_rename_unknown_save_raises():
    with pytest.raises(ValueError):
        save_manager.rename_save("nonexistent", "X")


def test_delete_save_removes_its_directory_and_registry_entry():
    save_id = save_manager.create_save("To Delete")
    save_dir = save_manager._save_dir(save_id)
    assert save_dir.exists()

    save_manager.delete_save(save_id)
    assert save_manager.list_saves() == []
    assert not save_dir.exists()


def test_deleting_the_active_save_clears_active_save_id():
    save_id = save_manager.create_save("Active One")
    save_manager.delete_save(save_id)
    assert save_manager.get_active_save_id() is None


def test_delete_unknown_save_raises():
    with pytest.raises(ValueError):
        save_manager.delete_save("nonexistent")


def test_load_unknown_save_raises():
    with pytest.raises(ValueError):
        save_manager.load_save("nonexistent")


def test_ensure_active_save_loaded_returns_false_with_no_active_save():
    assert save_manager.ensure_active_save_loaded() is False


def test_ensure_active_save_loaded_resumes_the_real_active_save():
    save_id = save_manager.create_save("Resume Me")
    season_state.reset_season()
    season_state.set_user_team("SF")

    # Simulate a fresh process: forget everything in memory, then resume.
    season_state._season = None
    assert save_manager.ensure_active_save_loaded() is True
    assert season_state.get_season().user_team_abbr == "SF"
    assert save_manager.get_active_save_id() == save_id


# --- Routes ------------------------------------------------------------------

def test_saves_page_loads_and_lists_no_saves_initially():
    resp = client.get("/saves")
    assert resp.status_code == 200
    assert "No saves yet" in resp.text


def test_saves_new_route_creates_a_save_and_redirects_to_team_select():
    resp = client.post("/saves/new", data={"name": "Route Test"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/team-select"
    assert any(s.name == "Route Test" for s in save_manager.list_saves())


def test_saves_page_shows_a_created_save():
    save_manager.create_save("Visible Save")
    resp = client.get("/saves")
    assert resp.status_code == 200
    assert "Visible Save" in resp.text


def test_saves_load_route_switches_the_active_save():
    save_a = save_manager.create_save("Save One")
    season_state.reset_season()
    season_state.set_user_team("KC")
    save_b = save_manager.create_save("Save Two")
    season_state.reset_season()
    season_state.set_user_team("BUF")

    resp = client.post(f"/saves/{save_a}/load", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"
    assert season_state.get_season().user_team_abbr == "KC"


def test_saves_rename_route():
    save_id = save_manager.create_save("Before Rename")
    resp = client.post(f"/saves/{save_id}/rename", data={"name": "After Rename"}, follow_redirects=False)
    assert resp.status_code == 303
    assert save_manager.list_saves()[0].name == "After Rename"


def test_saves_delete_route():
    save_id = save_manager.create_save("Delete Me")
    resp = client.post(f"/saves/{save_id}/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert save_manager.list_saves() == []


def test_saves_load_route_404s_for_unknown_save():
    resp = client.post("/saves/nonexistent/load")
    assert resp.status_code == 404


def test_dashboard_redirects_to_saves_when_registry_exists_with_no_active_save():
    """Once this machine has ever used the /saves picker (a real
    registry.json exists) but nothing is currently active (e.g. right
    after deleting the active save), /dashboard must send the user to
    /saves rather than silently building a season on old, un-named
    default paths."""
    save_id = save_manager.create_save("Will Delete")
    save_manager.delete_save(save_id)
    assert save_manager.REGISTRY_PATH.exists()
    assert not save_manager.has_active_save()

    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/saves"
