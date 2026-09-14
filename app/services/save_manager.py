"""
Multi-save-game management: start a new franchise, save it under a real
name, and come back to it later -- the piece this app never actually
had (the engine always assumed exactly one always-active franchise,
persisted to one fixed set of files).

Real architecture: every one of this app's persistence surfaces --
app/core/db.py's DB_PATH (the Player/Coach/Injury roster) plus every
app/services/*.py store's own DEFAULT_PATH (season state, gameplans,
power rankings, awards race, league history, depth chart overrides,
owner pressure, team expectations) -- was always just a fixed, SWAPPABLE
global path. That's the exact convention tests/conftest.py already
exploits for test isolation (redirect the globals, clear the caches,
reload). A "save" here is nothing more than a directory holding all of
those files together; "loading" a save means doing that same
redirect-and-clear operation for real, not just for the duration of one
test.

Exactly one save is "active" at a time -- the one every route currently
reads/writes through, tracked in REGISTRY_PATH so a server restart
resumes the same save automatically (see ensure_active_save_loaded()).
"""
from __future__ import annotations
import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core import db as db_module

SAVES_ROOT = Path("data/saves/games")
REGISTRY_PATH = Path("data/saves/registry.json")

# The pristine, never-played roster DB every new save is seeded from.
# NOT the same file as app.core.db.DB_PATH, which is wherever the
# CURRENTLY ACTIVE save's own (already-played, mutating) roster copy
# lives -- see create_save().
TEMPLATE_DB_PATH = Path("data/franchise_template.db")

# The real 2002-2025 NFL-history-imported League History (scripts/
# import_nfl_history.py) every NEW save's own history.json is seeded
# from -- built by scripts/build_franchise_template_history.py. NOT the
# same file as history_store.DEFAULT_PATH, which (once _redirect_globals
# below points it at the active save's own directory) is wherever that
# save's own history -- the real imported seasons PLUS whatever seasons
# that franchise has since actually played -- lives.
#
# Without this, a brand-new save's history.json never existed at all,
# so history_store.get_history() returned [] and season_state.py's
# _bootstrap_season_number() (len(history_store.get_history())) started
# every new franchise at season_number 0 -- app/config.py's season_year(0)
# = FIRST_SEASON = 2002, even though the real league timeline is already
# sitting at 2026+. Seeding the real 24 imported seasons here means a
# fresh save's own history.json already has them, so _bootstrap_season_
# number() naturally continues chronologically after them, exactly like
# it already does for a second franchise created after a first one has
# played real seasons -- there was never anything special-casing "a
# save's FIRST franchise" other than this file not existing yet.
TEMPLATE_HISTORY_PATH = Path("data/franchise_template_history.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SaveMeta:
    save_id: str
    name: str
    created_at: str
    last_played_at: str
    user_team_abbr: str | None = None
    current_week: int | None = None
    season_number: int | None = None


def _load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"active_save_id": None, "saves": {}}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _write_registry(data: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_saves() -> list[SaveMeta]:
    reg = _load_registry()
    return sorted(
        (SaveMeta(save_id=sid, **meta) for sid, meta in reg["saves"].items()),
        key=lambda m: m.last_played_at, reverse=True,
    )


def get_active_save_id() -> str | None:
    return _load_registry().get("active_save_id")


def has_active_save() -> bool:
    return get_active_save_id() is not None


def _save_dir(save_id: str) -> Path:
    return SAVES_ROOT / save_id


def _paths_for(save_dir: Path) -> dict[str, Path]:
    return {
        "db": save_dir / "franchise.db",
        "season": save_dir / "season.json",
        "history": save_dir / "history.json",
        "power_rank": save_dir / "power_rank_history.json",
        "gameplans": save_dir / "gameplans.json",
        "award_race": save_dir / "award_race_history.json",
        "owner_pressure": save_dir / "owner_pressure.json",
        "team_expectations": save_dir / "team_expectations.json",
        "depth_chart_overrides": save_dir / "depth_chart_overrides.json",
        # Brian's report, 2026-09-13: these were never redirected per-save,
        # so every save shared (and overwrote each other's) headlines and
        # draft state through the same fixed data/saves/*.json files the
        # instant a second franchise existed -- season_state.py keys
        # draft_class_store/offseason_recap_store by season_number alone,
        # and two saves both starting at season_number 0 (the common case)
        # collide outright. scripts/_verify_isolated.py already treated
        # this full set as one unit for test isolation; save_manager just
        # never grew the matching per-save entries when these stores were
        # added.
        "headlines": save_dir / "headlines_history.json",
        "pick_inventory": save_dir / "pick_inventory.json",
        "draft_history": save_dir / "draft_history.json",
        "undrafted_pool": save_dir / "undrafted_pool.json",
        "draft_progress": save_dir / "draft_progress.json",
        "draft_classes": save_dir / "draft_classes.json",
        "draft_board": save_dir / "draft_board.json",
        "offseason_recap": save_dir / "offseason_recap.json",
    }


def _redirect_globals(save_dir: Path) -> None:
    """The real "load" operation -- every module-level DEFAULT_PATH this
    app has now points into `save_dir` instead of wherever it pointed
    before. Imported lazily (not at module load) to avoid a circular
    import, same convention app/services/save_service.py's own
    season_from_dict() already uses."""
    from app.services import (
        save_service, history_store, power_rank_history, gameplan_store,
        award_race_history, owner_pressure_store, team_expectations, depth_chart_overrides,
        headlines_history, draft_pick_store, draft_store, undrafted_pool,
        draft_progress_store, draft_class_store, draft_board_store, offseason_recap_store,
    )
    p = _paths_for(save_dir)
    db_module.DB_PATH = p["db"]
    save_service.DEFAULT_SAVE_PATH = p["season"]
    history_store.DEFAULT_PATH = p["history"]
    power_rank_history.DEFAULT_PATH = p["power_rank"]
    gameplan_store.DEFAULT_PATH = p["gameplans"]
    award_race_history.DEFAULT_PATH = p["award_race"]
    owner_pressure_store.DEFAULT_PATH = p["owner_pressure"]
    team_expectations.DEFAULT_PATH = p["team_expectations"]
    depth_chart_overrides.DEFAULT_PATH = p["depth_chart_overrides"]
    headlines_history.DEFAULT_PATH = p["headlines"]
    draft_pick_store.DEFAULT_PATH = p["pick_inventory"]
    draft_store.DEFAULT_PATH = p["draft_history"]
    undrafted_pool.DEFAULT_PATH = p["undrafted_pool"]
    draft_progress_store.DEFAULT_PATH = p["draft_progress"]
    draft_class_store.DEFAULT_PATH = p["draft_classes"]
    draft_board_store.DEFAULT_PATH = p["draft_board"]
    offseason_recap_store.DEFAULT_PATH = p["offseason_recap"]


def _clear_all_caches() -> None:
    """Every in-memory, DB-or-season-backed cache this app has, cleared
    in one place -- the same set tests/conftest.py's own
    _clear_db_backed_caches() already tracks, plus season_state's own
    lazy-singleton and main.py's Stats-page aggregates cache. Missing
    even one of these would silently keep serving the PREVIOUS save's
    data for the rest of the process's life after a load/switch."""
    from app.services import coach_store, depth_chart, injury_store, history_store
    from app.services import owner_pressure_store, team_expectations, season_state
    from app.engine import season_stats

    coach_store.clear_cache()
    depth_chart.clear_starters_cache()  # also clears injury_store's own cache, see that function's docstring
    injury_store.clear_cache()
    history_store.clear_career_stats_cache()
    season_stats.clear_current_season_cache()
    owner_pressure_store.clear_cache()
    team_expectations.clear_cache()
    season_state._season = None  # force a fresh load from the (now-redirected) season path

    if db_module._engine is not None:
        db_module._engine.dispose()  # Windows keeps the file locked otherwise
    db_module._engine = None
    db_module._engine_path = None

    try:
        import app.main as main_module
        main_module._clear_stats_page_aggregates_cache()
    except Exception:
        pass  # app.main may not be fully imported yet (e.g. called from a script)


def create_save(name: str) -> str:
    """A brand-new franchise, seeded from the pristine TEMPLATE_DB_PATH
    (never itself mutated by play) rather than whatever the currently
    active save's own roster looks like after real games/trades/
    progression -- every new save starts from the same real, unplayed
    roster. Also seeded from TEMPLATE_HISTORY_PATH's real 2002-2025
    League History, the same way and for the same reason -- see that
    constant's own docstring for the season_number bug this fixes.
    Becomes the active save immediately; the caller still needs to send
    the user to /team-select (GDD Sec 10.1 -- team choice is a separate
    step, unchanged)."""
    if not TEMPLATE_DB_PATH.exists():
        raise RuntimeError(
            f"No template roster DB at {TEMPLATE_DB_PATH} -- run "
            "scripts/import_players.py + scripts/import_coaches.py, then "
            "copy the resulting data/franchise_football.db to this path."
        )
    if not TEMPLATE_HISTORY_PATH.exists():
        raise RuntimeError(
            f"No template League History at {TEMPLATE_HISTORY_PATH} -- run "
            "scripts/import_nfl_history.py (if data/saves/history.json doesn't "
            "already have the real 2002-2025 seasons archived), then "
            "scripts/build_franchise_template_history.py to extract them."
        )
    save_id = uuid.uuid4().hex[:12]
    save_dir = _save_dir(save_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    paths = _paths_for(save_dir)
    shutil.copy(TEMPLATE_DB_PATH, paths["db"])
    shutil.copy(TEMPLATE_HISTORY_PATH, paths["history"])

    now = _now()
    reg = _load_registry()
    reg["saves"][save_id] = {
        "name": name, "created_at": now, "last_played_at": now,
        "user_team_abbr": None, "current_week": None, "season_number": None,
    }
    reg["active_save_id"] = save_id
    _write_registry(reg)

    _redirect_globals(save_dir)
    _clear_all_caches()
    return save_id


def load_save(save_id: str) -> None:
    reg = _load_registry()
    if save_id not in reg["saves"]:
        raise ValueError(f"No such save: {save_id!r}")
    reg["saves"][save_id]["last_played_at"] = _now()
    reg["active_save_id"] = save_id
    _write_registry(reg)

    _redirect_globals(_save_dir(save_id))
    _clear_all_caches()


def rename_save(save_id: str, name: str) -> None:
    reg = _load_registry()
    if save_id not in reg["saves"]:
        raise ValueError(f"No such save: {save_id!r}")
    reg["saves"][save_id]["name"] = name
    _write_registry(reg)


def delete_save(save_id: str) -> None:
    """Permanently deletes a save's own directory (its roster DB and
    every JSON store it owns). If it was the active one, active_save_id
    is cleared -- the caller's job (the /saves route) to send the user
    back to the save picker rather than silently keep operating on a
    now-deleted save's stale in-memory state."""
    reg = _load_registry()
    if save_id not in reg["saves"]:
        raise ValueError(f"No such save: {save_id!r}")
    del reg["saves"][save_id]
    if reg.get("active_save_id") == save_id:
        reg["active_save_id"] = None
    _write_registry(reg)
    shutil.rmtree(_save_dir(save_id), ignore_errors=True)


def sync_active_save_summary() -> None:
    """Refreshes the active save's own registry row (user_team_abbr,
    current_week, season_number) so the /saves picker can show real,
    up-to-date progress without opening every save's own season.json --
    called from season_state.py's own mutating calls (simulate_current_
    week, set_user_team, reset_season, start_new_season). A no-op if no
    save is active (e.g. a test or script that never called create_save/
    load_save at all)."""
    active_id = get_active_save_id()
    if active_id is None:
        return
    from app.services import season_state
    season = season_state.get_season()
    reg = _load_registry()
    if active_id not in reg["saves"]:
        return
    reg["saves"][active_id].update({
        "user_team_abbr": season.user_team_abbr,
        "current_week": season.current_week,
        "season_number": season.season_number,
    })
    _write_registry(reg)


def ensure_active_save_loaded() -> bool:
    """Called once at real process startup (mirrors season_state.get_
    season()'s own lazy-load, just for the whole save bundle instead of
    one file) -- redirects every global to whichever save was active
    when the server last stopped, so a restart resumes exactly where the
    user left off.

    Also unconditionally touches REGISTRY_PATH into existence (an empty
    {"active_save_id": None, "saves": {}} registry) if it doesn't exist
    at all yet -- a genuinely brand-new install. This is deliberately
    the ONLY place that happens: app/main.py's entry routes gate on
    "REGISTRY_PATH.exists() and not has_active_save()" to decide whether
    to send the user to /saves, and this function is only ever called
    from a real ASGI startup event (uvicorn), never from TestClient-based
    tests (which don't trigger FastAPI's startup/shutdown lifecycle
    unless used as a `with` context manager, which nothing in this test
    suite does) -- so a fresh checkout/CI run never gets a registry.json
    written at all, and every existing route test keeps working exactly
    as it did before this feature existed. A REAL server's very first
    startup, by contrast, always ends up with a real (if initially
    saveless) registry.json, so its very first request already gates
    correctly.

    Returns False if there's no active save (a brand-new install, one
    that predates this feature, or one where the active save was
    deleted) -- the signal app/main.py's entry routes use to send the
    user to /saves instead of silently building a season on old,
    un-named default paths."""
    if not REGISTRY_PATH.exists():
        _write_registry({"active_save_id": None, "saves": {}})

    active_id = get_active_save_id()
    if active_id is None:
        return False
    _redirect_globals(_save_dir(active_id))
    return True
