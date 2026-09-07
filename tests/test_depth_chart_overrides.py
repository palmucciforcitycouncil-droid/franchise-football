"""
Tests for the user-settable depth chart override
(app/services/depth_chart_overrides.py) -- verifies an override
actually changes who get_offensive_starters picks, not just that the
JSON round-trips in isolation.

Requires the imported roster DB, same as test_player_ai.py.
"""
import os
os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest

from app.core.db import DB_PATH

DB_EXISTS = DB_PATH.exists()
pytestmark = pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")


def test_resolve_order_falls_back_to_rating_with_no_override(tmp_path):
    from app.services import depth_chart_overrides as dco
    from app.services.depth_chart import _load_roster
    from app.models.player import Position

    path = tmp_path / "overrides.json"
    qbs = [p for p in _load_roster("KC") if p.position == Position.QB]
    resolved = dco.resolve_order("KC", "QB", qbs, path=path)

    assert resolved == sorted(qbs, key=lambda p: -p.overall_rating)


def test_move_player_persists_and_resolve_order_reflects_it(tmp_path):
    from app.services import depth_chart_overrides as dco
    from app.services.depth_chart import _load_roster
    from app.models.player import Position

    path = tmp_path / "overrides.json"
    qbs = [p for p in _load_roster("KC") if p.position == Position.QB]
    default_order = [p.player_id for p in sorted(qbs, key=lambda p: -p.overall_rating)]
    assert len(default_order) >= 2  # sanity-check the fixture assumption (KC has QB depth)

    backup_id = default_order[1]
    dco.move_player("KC", "QB", default_order, backup_id, "up", path=path)

    resolved = dco.resolve_order("KC", "QB", qbs, path=path)
    assert resolved[0].player_id == backup_id


def test_move_up_at_top_of_list_is_a_no_op(tmp_path):
    from app.services import depth_chart_overrides as dco

    path = tmp_path / "overrides.json"
    ids = ["a", "b", "c"]
    dco.move_player("KC", "QB", ids, "a", "up", path=path)
    assert dco.get_order("KC", "QB", path=path) == ids


def test_get_offensive_starters_respects_an_override(monkeypatch, tmp_path):
    """The real integration point: an override changes which player the
    engine actually starts with, not just what resolve_order returns in
    isolation."""
    from app.services import depth_chart_overrides as dco
    from app.services.depth_chart import _load_roster, get_offensive_starters, clear_starters_cache
    from app.models.player import Position

    monkeypatch.setattr(dco, "DEFAULT_PATH", tmp_path / "overrides.json")

    qbs = sorted((p for p in _load_roster("KC") if p.position == Position.QB), key=lambda p: -p.overall_rating)
    assert len(qbs) >= 2
    backup = qbs[1]

    dco.set_order("KC", "QB", [backup.player_id] + [p.player_id for p in qbs if p.player_id != backup.player_id])
    clear_starters_cache()
    try:
        starters = get_offensive_starters("KC")
        assert starters.qb.player_id == backup.player_id
    finally:
        clear_starters_cache()
