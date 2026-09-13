"""
Shared isolation setup for standalone verification scripts that call
season_state (or anything under it) OUTSIDE pytest.

READ ROADMAP.md Sec 2b before writing a script that imports this or
does something similar by hand -- three real, documented incidents
(M12, M14, and R1's own build) all came from a one-off script touching
one or more of season_state's persistence surfaces without redirecting
every one of them first. Import this module and call setup() BEFORE
importing/using app.services.season_state (or anything that transitively
imports it) at all.
"""
from __future__ import annotations
import shutil
from pathlib import Path

from app.core import db as db_module

REAL_DB_PATH = db_module.DB_PATH
_SCRATCH_DB_PATH = Path("data/_verify_scratch.db")


def setup(tag: str = "verify") -> None:
    from app.services import (
        gameplan_store, history_store, power_rank_history, save_service,
        owner_pressure_store, team_expectations,
    )

    shutil.copy(REAL_DB_PATH, _SCRATCH_DB_PATH)
    db_module.DB_PATH = _SCRATCH_DB_PATH
    db_module._engine = None

    paths = [
        Path(f"data/saves/_{tag}_season.json"),
        Path(f"data/saves/_{tag}_history.json"),
        Path(f"data/saves/_{tag}_gameplans.json"),
        Path(f"data/saves/_{tag}_power_rank.json"),
        Path(f"data/saves/_{tag}_owner_pressure.json"),
        Path(f"data/saves/_{tag}_team_expectations.json"),
    ]
    save_service.DEFAULT_SAVE_PATH, history_store.DEFAULT_PATH, \
        gameplan_store.DEFAULT_PATH, power_rank_history.DEFAULT_PATH, \
        owner_pressure_store.DEFAULT_PATH, team_expectations.DEFAULT_PATH = paths
    for p in paths:
        p.unlink(missing_ok=True)

    from app.services import coach_store, depth_chart, injury_store
    depth_chart.clear_starters_cache()
    coach_store.clear_cache()
    injury_store.clear_cache()
    owner_pressure_store.clear_cache()
    team_expectations.clear_cache()


def teardown(tag: str = "verify") -> None:
    from app.services import (
        gameplan_store, history_store, power_rank_history, save_service,
        owner_pressure_store, team_expectations,
    )

    if db_module._engine is not None:
        db_module._engine.dispose()
    db_module.DB_PATH = REAL_DB_PATH
    db_module._engine = None
    _SCRATCH_DB_PATH.unlink(missing_ok=True)

    from app.services import coach_store, depth_chart, injury_store
    depth_chart.clear_starters_cache()
    coach_store.clear_cache()
    injury_store.clear_cache()
    owner_pressure_store.clear_cache()
    team_expectations.clear_cache()

    for p in [
        Path(f"data/saves/_{tag}_season.json"),
        Path(f"data/saves/_{tag}_history.json"),
        Path(f"data/saves/_{tag}_gameplans.json"),
        Path(f"data/saves/_{tag}_power_rank.json"),
        Path(f"data/saves/_{tag}_owner_pressure.json"),
        Path(f"data/saves/_{tag}_team_expectations.json"),
    ]:
        p.unlink(missing_ok=True)
    # These module-level attrs stay pointed at the throwaway paths in
    # THIS process -- fine for a one-shot script (process exits right
    # after), not safe to import into a long-lived process without
    # restoring save_service.DEFAULT_SAVE_PATH etc. too.
