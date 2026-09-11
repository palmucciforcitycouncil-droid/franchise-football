"""
Tests for the persisted weekly Power Ranking snapshot store
(app/services/power_rank_history.py, ROADMAP.md Sec2d-B item 10).

Every test passes an explicit tmp_path `path=` rather than touching the
module's DEFAULT_PATH -- same convention as test_depth_chart_overrides.py
-- so this file needs no isolation fixture of its own; it never comes
near the real save (tests/conftest.py's session fixture also redirects
DEFAULT_PATH as a second line of defense for anything that forgets to
pass path=).
"""
from app.services import power_rank_history as prh


def test_get_ranks_returns_none_for_an_unrecorded_week(tmp_path):
    path = tmp_path / "power_ranks.json"
    assert prh.get_ranks(0, 1, path=path) is None


def test_record_and_get_round_trip(tmp_path):
    path = tmp_path / "power_ranks.json"
    ranks = {"KC": 1, "BUF": 2, "SF": 3}
    prh.record_snapshot(0, 5, ranks, path=path)

    assert prh.get_ranks(0, 5, path=path) == ranks
    assert prh.get_ranks(0, 4, path=path) is None  # adjacent week untouched


def test_different_weeks_dont_clobber_each_other(tmp_path):
    path = tmp_path / "power_ranks.json"
    prh.record_snapshot(0, 1, {"KC": 5}, path=path)
    prh.record_snapshot(0, 2, {"KC": 3}, path=path)

    assert prh.get_ranks(0, 1, path=path) == {"KC": 5}
    assert prh.get_ranks(0, 2, path=path) == {"KC": 3}


def test_re_recording_the_same_week_overwrites_it(tmp_path):
    path = tmp_path / "power_ranks.json"
    prh.record_snapshot(0, 1, {"KC": 5}, path=path)
    prh.record_snapshot(0, 1, {"KC": 1}, path=path)

    assert prh.get_ranks(0, 1, path=path) == {"KC": 1}


def test_season_numbers_are_isolated_from_each_other(tmp_path):
    """A delta must never silently cross a season boundary -- week 1 of
    season 1 has no meaningful relationship to week 1 of season 0, even
    though both are stored under the same week key."""
    path = tmp_path / "power_ranks.json"
    prh.record_snapshot(0, 18, {"KC": 1}, path=path)
    prh.record_snapshot(1, 1, {"KC": 20}, path=path)

    assert prh.get_ranks(0, 18, path=path) == {"KC": 1}
    assert prh.get_ranks(1, 1, path=path) == {"KC": 20}
    assert prh.get_ranks(1, 18, path=path) is None
