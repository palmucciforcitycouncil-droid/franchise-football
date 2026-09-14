"""
Session-wide test isolation for the Season save file (GDD Part 1 Sec 8)
and the Player/Coach/Injury database.

`save_service.DEFAULT_SAVE_PATH` points at the REAL save
(data/saves/current_season.json) that the live app/dev server actually
reads and writes on every request. Several test files call
`season_state.reset_season()`/`simulate_current_week()`/etc directly
(test_playoffs.py, test_season.py, test_season_rollover.py, test_awards.py,
test_scouting.py, test_stat_realism.py, test_history_store.py) -- every one
of those calls `save_service.save_season()` with no path override, which
had been writing straight over the real save file on every single test
run, with no isolation at all (unlike `history_store.DEFAULT_PATH`, which
individual tests already redirect per-test -- season_state's save path
never got the same treatment anywhere).

Discovered the hard way in a live session (2026-09-09): a one-off
verification script -- and, it turned out, the test suite itself, on a
routine "run the full suite" verification step -- overwrote a real,
in-progress franchise save. Recovered via a still-running server's correct
in-memory state (never touch `data/saves/` directly to "fix" a bad save --
if a live app process is still running with the correct state, get IT to
re-save, don't hand-edit the JSON), but the underlying gap needed a real
fix, not just a one-time recovery.

This autouse, session-scoped fixture redirects `save_service.DEFAULT_SAVE_PATH`
to a throwaway file under data/saves/ for the entire pytest run, so no
test -- present or future, regardless of which season_state functions it
calls -- can ever touch the real save again. Session-scoped rather than
per-test: no test anywhere in this suite wants the real path, so repointing
it once is both simpler and cheaper than adding the same try/finally
redirect to 7+ individual test files.

Also redirects `power_rank_history.DEFAULT_PATH` (ROADMAP.md Sec2d-B item
10) the same way, for the same reason.

**Third surface, added for R1 (2026-09-12): `app.core.db.DB_PATH` itself.**
Before R1 (the injury system), nothing `simulate_current_week()` touched
during a WEEKLY sim (as opposed to `start_new_season()`'s offseason
progression pass) ever wrote to the Player/Coach database -- only
`test_coaching.py`, `test_history_store.py`, and `test_season_rollover.py`
needed their own per-test DB_PATH isolation, precisely because only they
called `start_new_season()`. R1 changed that premise: `roll_injuries_for_
week()`/`apply_weekly_decay()` now write to the real `Injury` table on
EVERY `simulate_current_week()` call, which `test_playoffs.py`,
`test_scouting.py`, `test_awards.py`, `test_stat_realism.py`, and
`test_season.py` all call without ever expecting to need DB isolation --
a real, live incident (ROADMAP.md Sec 2b's third entry): 546 bogus
Injury rows leaked into the production `data/franchise_football.db`
from exactly this gap before this fixture existed.

**A first fix here (session-scoped DB_PATH redirect, tried and reverted
same day) had a second real bug**: sharing ONE throwaway DB copy for the
whole session stops any test from touching the REAL file, but doesn't
stop tests from polluting EACH OTHER -- `resolve_all_active()` only
soft-deletes injuries (is_active=False), it never rows-deletes, and a
full-season test that never calls it again after its own last simulated
week leaves genuinely-still-active injuries sitting in the shared file.
A LATER test's own `shutil.copy()` of "the current DB_PATH" then inherits
that pollution -- caught via `test_injuries.py`'s own
`currently_out_player_ids() == frozenset()` assertion failing only when
run as part of the full suite, never standalone. **The actual fix**:
`_golden_db_path` (session-scoped) is copied from the real file ONCE and
never written to directly by any test; `_isolate_db_path` (function-
scoped, autouse) re-copies FROM that golden copy to a fresh per-test
file before every single test function and redirects DB_PATH to it, so
no test can ever see another test's writes, while still only touching
the real file with one read at session start. Tests that need their OWN
further-isolated throwaway (test_coaching.py etc.) still work unchanged
-- they capture "the current DB_PATH" at their own fixture's setup time
(now this test's fresh per-function copy) and restore to THAT in their
own `finally`; nested isolation composes safely.
"""
import shutil
from pathlib import Path

import pytest

from app.core import db as db_module
from app.services import save_service, power_rank_history, owner_pressure_store, team_expectations, award_race_history, save_manager, headlines_history, draft_store, undrafted_pool, draft_class_store, draft_board_store, draft_progress_store, offseason_recap_store, draft_pick_store

# Captured once, at collection time, before any fixture below ever
# reassigns `db_module.DB_PATH` -- the one stable reference point
# `_isolate_db_path` needs to tell "nothing else has touched DB_PATH
# yet" apart from "a broader-scoped fixture already redirected it"
# (see that fixture's own docstring for the real bug this fixes).
_REAL_DB_PATH = db_module.DB_PATH


@pytest.fixture(autouse=True, scope="session")
def _isolate_season_save_path():
    real_save_path = save_service.DEFAULT_SAVE_PATH
    real_power_rank_path = power_rank_history.DEFAULT_PATH
    # R3d's two new persistent stores get the exact same session-scoped
    # throwaway-path treatment power_rank_history already has -- both
    # are, like it, a plain JSON dict keyed by season_number (and, for
    # owner_pressure_store, team_abbr), never the real save the live
    # server reads.
    real_owner_pressure_path = owner_pressure_store.DEFAULT_PATH
    real_team_expectations_path = team_expectations.DEFAULT_PATH
    # R8 (Awards Page): same session-scoped throwaway-path treatment as
    # power_rank_history above -- a plain JSON dict keyed by season_number,
    # written once per simulated week by season_state.simulate_current_
    # week(), never the real save the live server reads.
    real_award_race_path = award_race_history.DEFAULT_PATH
    # R9 (Weekly Headlines): same session-scoped throwaway-path treatment
    # as power_rank_history/award_race_history above -- written once per
    # simulated week by season_state.simulate_current_week().
    real_headlines_path = headlines_history.DEFAULT_PATH
    # R5 (Draft): same session-scoped throwaway-path treatment as every
    # other store above -- draft_store.py's real results and undrafted_
    # pool.py's real 3-year expiration clock, both written once per
    # simulated offseason by season_state.start_new_season().
    real_draft_path = draft_store.DEFAULT_PATH
    real_undrafted_path = undrafted_pool.DEFAULT_PATH
    # Live, interactive draft rebuild (Brian's ask, 2026-09-13): season_
    # state._build_season() now generates + persists next season's real
    # prospect class (draft_class_store) every time it runs -- including
    # from reset_season(), i.e. every single test in this whole suite
    # that builds a fresh season at all -- plus the live pick-by-pick
    # engine's own in-progress state and the user's personal board.
    # Same session-scoped throwaway-path treatment as every store above.
    real_draft_class_path = draft_class_store.DEFAULT_PATH
    real_draft_board_path = draft_board_store.DEFAULT_PATH
    real_draft_progress_path = draft_progress_store.DEFAULT_PATH
    # Offseason Recap (Brian's ask, 2026-09-13): begin_offseason() now
    # ALSO snapshots the whole real roster every time it runs -- same
    # session-scoped throwaway-path treatment as every store above.
    real_offseason_recap_path = offseason_recap_store.DEFAULT_PATH
    # Draft-Pick Trading (GDD Sec 8.5): same session-scoped throwaway-path
    # treatment as draft_store/undrafted_pool above -- real persistent
    # pick ownership, written by every real rollover (season_state.py's
    # _build_season()) and by app/engine/trades.py's execute_trade().
    real_pick_inventory_path = draft_pick_store.DEFAULT_PATH
    # Multi-save games (save_manager.py): defense in depth -- no existing
    # test creates/loads/deletes a save (see that module's own docstring
    # for why its registry-existence check already makes it a no-op in
    # a real CI/fresh-checkout environment regardless), but redirecting
    # its registry + save-bundle root here too means a test that someday
    # does touch it still can't come near the real data/saves/registry.json
    # or data/saves/games/ a real dev machine might have.
    real_registry_path = save_manager.REGISTRY_PATH
    real_saves_root = save_manager.SAVES_ROOT
    test_path = Path("data/saves/_test_isolated_current_season.json")
    test_power_rank_path = Path("data/saves/_test_isolated_power_rank_history.json")
    test_owner_pressure_path = Path("data/saves/_test_isolated_owner_pressure.json")
    test_team_expectations_path = Path("data/saves/_test_isolated_team_expectations.json")
    test_award_race_path = Path("data/saves/_test_isolated_award_race_history.json")
    test_headlines_path = Path("data/saves/_test_isolated_headlines_history.json")
    test_draft_path = Path("data/saves/_test_isolated_draft_history.json")
    test_undrafted_path = Path("data/saves/_test_isolated_undrafted_pool.json")
    test_pick_inventory_path = Path("data/saves/_test_isolated_pick_inventory.json")
    test_registry_path = Path("data/saves/_test_isolated_registry.json")
    test_saves_root = Path("data/saves/_test_isolated_games")
    test_draft_class_path = Path("data/saves/_test_isolated_draft_classes.json")
    test_draft_board_path = Path("data/saves/_test_isolated_draft_board.json")
    test_draft_progress_path = Path("data/saves/_test_isolated_draft_progress.json")
    test_offseason_recap_path = Path("data/saves/_test_isolated_offseason_recap.json")
    for p in (test_path, test_power_rank_path, test_owner_pressure_path, test_team_expectations_path, test_award_race_path, test_headlines_path, test_draft_path, test_undrafted_path, test_pick_inventory_path, test_registry_path, test_draft_class_path, test_draft_board_path, test_draft_progress_path, test_offseason_recap_path):
        p.unlink(missing_ok=True)  # clear any leftover from an interrupted prior run
    shutil.rmtree(test_saves_root, ignore_errors=True)
    save_service.DEFAULT_SAVE_PATH = test_path
    power_rank_history.DEFAULT_PATH = test_power_rank_path
    owner_pressure_store.DEFAULT_PATH = test_owner_pressure_path
    team_expectations.DEFAULT_PATH = test_team_expectations_path
    award_race_history.DEFAULT_PATH = test_award_race_path
    headlines_history.DEFAULT_PATH = test_headlines_path
    draft_store.DEFAULT_PATH = test_draft_path
    undrafted_pool.DEFAULT_PATH = test_undrafted_path
    draft_pick_store.DEFAULT_PATH = test_pick_inventory_path
    save_manager.REGISTRY_PATH = test_registry_path
    save_manager.SAVES_ROOT = test_saves_root
    draft_class_store.DEFAULT_PATH = test_draft_class_path
    draft_board_store.DEFAULT_PATH = test_draft_board_path
    draft_progress_store.DEFAULT_PATH = test_draft_progress_path
    offseason_recap_store.DEFAULT_PATH = test_offseason_recap_path
    owner_pressure_store.clear_cache()
    team_expectations.clear_cache()
    try:
        yield
    finally:
        save_service.DEFAULT_SAVE_PATH = real_save_path
        power_rank_history.DEFAULT_PATH = real_power_rank_path
        owner_pressure_store.DEFAULT_PATH = real_owner_pressure_path
        team_expectations.DEFAULT_PATH = real_team_expectations_path
        award_race_history.DEFAULT_PATH = real_award_race_path
        headlines_history.DEFAULT_PATH = real_headlines_path
        draft_store.DEFAULT_PATH = real_draft_path
        undrafted_pool.DEFAULT_PATH = real_undrafted_path
        draft_pick_store.DEFAULT_PATH = real_pick_inventory_path
        save_manager.REGISTRY_PATH = real_registry_path
        save_manager.SAVES_ROOT = real_saves_root
        draft_class_store.DEFAULT_PATH = real_draft_class_path
        draft_board_store.DEFAULT_PATH = real_draft_board_path
        draft_progress_store.DEFAULT_PATH = real_draft_progress_path
        offseason_recap_store.DEFAULT_PATH = real_offseason_recap_path
        owner_pressure_store.clear_cache()
        team_expectations.clear_cache()
        for p in (test_path, test_power_rank_path, test_owner_pressure_path, test_team_expectations_path, test_award_race_path, test_headlines_path, test_draft_path, test_undrafted_path, test_pick_inventory_path, test_registry_path, test_draft_class_path, test_draft_board_path, test_draft_progress_path, test_offseason_recap_path):
            p.unlink(missing_ok=True)
        shutil.rmtree(test_saves_root, ignore_errors=True)


@pytest.fixture(scope="session")
def _golden_db_path():
    """A read-only reference copy of the real DB, made exactly once.
    Never redirected into `db_module.DB_PATH` directly (except briefly,
    below, to scrub it) -- only `_isolate_db_path` below copies FROM
    this, per test function.

    Real incident (2026-09-12, R2b session): a real, currently-playing
    franchise can have real ACTIVE injuries in `data/franchise_football.
    db` at the exact moment a test run starts -- test_injuries.py's
    `test_decay_tapers_rtp_penalty_and_eventually_auto_closes` asserts
    `currently_out_player_ids() == frozenset()` after resolving the ONE
    synthetic injury it created, which fails the instant the golden copy
    (taken from that live, in-progress save) already carries OTHER real
    active injuries -- nothing to do with that test's own logic, or
    whatever the current test session actually changed. Scrubbed here,
    once, via the exact same `resolve_all_active()` a real season
    rollover already uses (`season_state.reset_season()`/
    `start_new_season()`), so every test's own copy starts from a
    genuinely clean bill of health regardless of the live franchise's
    real state when the suite happens to run."""
    real_db_path = db_module.DB_PATH
    golden_path = Path("data/_test_golden_franchise.db")
    golden_path.unlink(missing_ok=True)
    shutil.copy(real_db_path, golden_path)

    from app.services import injury_store
    db_module.DB_PATH = golden_path
    db_module._engine = None
    try:
        injury_store.resolve_all_active()
    finally:
        if db_module._engine is not None:
            db_module._engine.dispose()
        db_module.DB_PATH = real_db_path
        db_module._engine = None
        injury_store.clear_cache()

    try:
        yield golden_path
    finally:
        golden_path.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _isolate_db_path(_golden_db_path):
    """Function-scoped (not session-scoped, see module docstring for the
    real bug that distinction fixes): every single test gets its OWN
    fresh copy of the golden reference DB, so no test can ever see
    another test's writes, and the real file is never touched at all.

    **A second real bug, found and fixed 2026-09-12**: a module-scoped
    fixture that does its OWN `db_module.DB_PATH` redirect before this
    one runs (test_coaching.py's `completed_season`, which simulates a
    full season + playoffs against its own throwaway DB, entirely
    BEFORE any test function body executes) sets up FIRST -- pytest
    instantiates broader-scoped fixtures before narrower-scoped ones,
    regardless of declaration order. This fixture used to always copy
    from the untouched session-level `_golden_db_path` regardless,
    silently discarding whatever `completed_season` had just
    populated (its real, fully-simulated championship credits included)
    and running the actual test body against a pristine, pre-simulation
    database instead. Confirmed via instrumentation: `credit_championship_
    round()` was writing `hc_super_bowl_wins` correctly to
    `completed_season`'s own DB; the failing assertion was reading it
    back from a DIFFERENT, wrong file this fixture had substituted in.
    Fixed by sourcing the per-test copy from whatever `db_module.DB_PATH`
    CURRENTLY is when it differs from `_REAL_DB_PATH` (i.e. a broader
    fixture already redirected it) -- and from the golden copy otherwise,
    unchanged from before for every test that doesn't nest like this."""
    real_db_path = db_module.DB_PATH
    per_test_path = Path("data/_test_isolated_franchise.db")
    per_test_path.unlink(missing_ok=True)
    source = real_db_path if real_db_path != _REAL_DB_PATH else _golden_db_path
    shutil.copy(source, per_test_path)
    db_module.DB_PATH = per_test_path
    db_module._engine = None
    _clear_db_backed_caches()
    try:
        yield
    finally:
        if db_module._engine is not None:
            db_module._engine.dispose()  # Windows keeps the file locked otherwise
        db_module.DB_PATH = real_db_path
        db_module._engine = None
        per_test_path.unlink(missing_ok=True)
        _clear_db_backed_caches()


@pytest.fixture(autouse=True)
def _isolate_negotiation_store():
    """Contract negotiation mood (app/services/negotiation_store.py,
    2026-09-14): written by every offer route. Function-scoped, not
    session-scoped like the stores above, because a mood/refusal left
    behind by one test's offers would silently change the verdict another
    test's identical offer gets (same window, team and player)."""
    from app.services import negotiation_store
    real_path = negotiation_store.DEFAULT_PATH
    test_path = Path("data/saves/_test_isolated_negotiations.json")
    test_path.unlink(missing_ok=True)
    negotiation_store.DEFAULT_PATH = test_path
    try:
        yield
    finally:
        negotiation_store.DEFAULT_PATH = real_path
        test_path.unlink(missing_ok=True)


def _clear_db_backed_caches() -> None:
    """Every lru_cache keyed off DB content, cleared on both sides of
    _isolate_db_path's swap -- otherwise a query answered before this
    fixture ran (or by whichever test ran immediately before this one)
    can serve stale data pointed at a file that no longer exists."""
    from app.services import coach_store, depth_chart, injury_store
    coach_store.clear_cache()
    depth_chart.clear_starters_cache()  # also clears injury_store's cache, see that function's own note
    injury_store.clear_cache()
