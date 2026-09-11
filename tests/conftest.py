"""
Session-wide test isolation for the Season save file (GDD Part 1 Sec 8).

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
10): simulate_current_week() now writes a weekly Power Ranking snapshot
via that module on every call, using the exact same DEFAULT_PATH-resolved-
at-call-time convention as save_service -- every one of the 7+ test files
above that call simulate_current_week()/reset_season() directly would
otherwise also be silently writing to the real data/saves/power_rank_history.json
on every run, the identical class of gap this fixture already closes for
the season save file itself.
"""
from pathlib import Path

import pytest

from app.services import save_service, power_rank_history


@pytest.fixture(autouse=True, scope="session")
def _isolate_season_save_path():
    real_save_path = save_service.DEFAULT_SAVE_PATH
    real_power_rank_path = power_rank_history.DEFAULT_PATH
    test_path = Path("data/saves/_test_isolated_current_season.json")
    test_power_rank_path = Path("data/saves/_test_isolated_power_rank_history.json")
    test_path.unlink(missing_ok=True)  # clear any leftover from an interrupted prior run
    test_power_rank_path.unlink(missing_ok=True)
    save_service.DEFAULT_SAVE_PATH = test_path
    power_rank_history.DEFAULT_PATH = test_power_rank_path
    try:
        yield
    finally:
        save_service.DEFAULT_SAVE_PATH = real_save_path
        power_rank_history.DEFAULT_PATH = real_power_rank_path
        test_path.unlink(missing_ok=True)
        test_power_rank_path.unlink(missing_ok=True)
