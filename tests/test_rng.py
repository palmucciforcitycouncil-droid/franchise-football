"""
Tests for app.engine.rng.stable_seed -- the fix for a real bug where
seeding via Python's builtin hash() on a tuple containing strings gave a
DIFFERENT value every server restart (hash randomization, on by default
since Python 3.3), silently breaking the app's own "deterministic:
replaying these two teams with this seed always produces this result"
claim. See stable_seed's docstring and HANDOFF.md for the full story.
"""
import subprocess
import sys


def test_stable_seed_is_a_pure_function():
    from app.engine.rng import stable_seed
    assert stable_seed(2025, "KC", "BUF", "demo_game") == stable_seed(2025, "KC", "BUF", "demo_game")


def test_stable_seed_differs_for_different_inputs():
    from app.engine.rng import stable_seed
    assert stable_seed(2025, "KC", "BUF") != stable_seed(2025, "BUF", "KC")


def test_stable_seed_is_actually_stable_across_processes():
    """The regression test that matters: a same-process test can't catch
    hash randomization on its own, since a process's hash seed is fixed
    for its own lifetime. Run it in fresh subprocesses instead -- this is
    exactly the scenario (server restart, same matchup) that was broken."""
    code = "from app.engine.rng import stable_seed; print(stable_seed(2025, 'KC', 'BUF', 'demo_game'))"
    results = {
        subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
        for _ in range(3)
    }
    assert len(results) == 1, f"stable_seed gave different values across processes: {results}"
