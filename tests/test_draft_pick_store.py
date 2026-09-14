"""
Persistent Draft Pick ownership tests (GDD Sec 8.5,
app/services/draft_pick_store.py). Every test here uses its own
throwaway `path` (never DEFAULT_PATH) via `tmp_path` -- conftest.py's
own session-scoped isolation redirects DEFAULT_PATH for the whole
session, but a per-test throwaway keeps these tests independent of each
other too, same discipline test_save_manager.py's own fixture uses.
"""
from __future__ import annotations

from app.services import draft_pick_store as pick_store


def test_ensure_lookahead_seeded_covers_every_team_every_round_for_current_plus_five_seasons(tmp_path):
    path = tmp_path / "picks.json"
    pick_store.ensure_lookahead_seeded(10, path=path)
    picks = pick_store.all_picks(path)
    seasons = {p.season_number for p in picks}
    assert seasons == {10, 11, 12, 13, 14, 15}
    # 32 teams x 7 rounds x (current + next 5 drafts)
    assert len(picks) == 32 * 7 * 6


def test_a_fresh_pick_is_owned_by_its_own_original_team(tmp_path):
    path = tmp_path / "picks.json"
    pick_store.ensure_lookahead_seeded(5, path=path)
    assert pick_store.owner_of(5, 1, "KC", path=path) == "KC"


def test_owner_of_defaults_to_the_original_team_when_never_seeded(tmp_path):
    """Backward-compat guarantee: a genuinely empty inventory (a fresh
    save/test that never called ensure_lookahead_seeded()) never breaks
    the draft -- every slot just defaults to its own original team."""
    path = tmp_path / "picks.json"
    assert pick_store.owner_of(99, 3, "BUF", path=path) == "BUF"


def test_transfer_pick_moves_real_ownership(tmp_path):
    path = tmp_path / "picks.json"
    pick_store.ensure_lookahead_seeded(5, path=path)
    pick_store.transfer_pick(5, 1, "KC", "BUF", path=path)
    assert pick_store.owner_of(5, 1, "KC", path=path) == "BUF"
    # The SLOT identity (original team) never changes -- only who owns it.
    picks = pick_store.picks_owned_by("BUF", path=path)
    assert any(p.season_number == 5 and p.round == 1 and p.original_team_abbr == "KC" for p in picks)


def test_transfer_pick_creates_the_slot_if_it_was_never_seeded(tmp_path):
    path = tmp_path / "picks.json"
    pick_store.transfer_pick(7, 4, "SF", "DAL", path=path)
    assert pick_store.owner_of(7, 4, "SF", path=path) == "DAL"


def test_picks_owned_by_reflects_trades_both_ways(tmp_path):
    path = tmp_path / "picks.json"
    pick_store.ensure_lookahead_seeded(1, path=path)
    before_kc = len(pick_store.picks_owned_by("KC", path=path))
    before_buf = len(pick_store.picks_owned_by("BUF", path=path))
    pick_store.transfer_pick(1, 2, "KC", "BUF", path=path)
    after_kc = len(pick_store.picks_owned_by("KC", path=path))
    after_buf = len(pick_store.picks_owned_by("BUF", path=path))
    assert after_kc == before_kc - 1
    assert after_buf == before_buf + 1


def test_consume_season_removes_only_that_seasons_picks(tmp_path):
    path = tmp_path / "picks.json"
    pick_store.ensure_lookahead_seeded(1, path=path)  # seeds seasons 1-6
    consumed = pick_store.consume_season(1, path=path)
    assert len(consumed) == 32 * 7
    remaining_seasons = {p.season_number for p in pick_store.all_picks(path)}
    assert remaining_seasons == {2, 3, 4, 5, 6}


def test_pick_id_round_trips_through_parse_pick_id():
    pick = pick_store.PickAsset(season_number=5, round=3, original_team_abbr="KC", current_owner_abbr="BUF")
    season_number, round_, original_team_abbr = pick_store.parse_pick_id(pick.pick_id)
    assert (season_number, round_, original_team_abbr) == (5, 3, "KC")


def test_tradeable_picks_are_the_next_five_drafts_not_the_current_season(tmp_path):
    """The live draft run at the end of season N is season N+1's -- so
    season N's own slot is already spent while you're playing it; trades
    offer exactly the next 5 drafts (Brian, 2026-09-14)."""
    path = tmp_path / "picks.json"
    pick_store.ensure_lookahead_seeded(24, path=path)
    picks = pick_store.tradeable_picks_owned_by("NYJ", 24, path=path)
    assert {p.season_number for p in picks} == {25, 26, 27, 28, 29}
    assert len(picks) == 7 * 5
    pick_store.transfer_pick(26, 1, "NYJ", "KC", path=path)
    assert any(p.original_team_abbr == "NYJ" for p in pick_store.tradeable_picks_owned_by("KC", 24, path=path))
