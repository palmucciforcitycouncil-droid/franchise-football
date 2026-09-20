"""
Draft page (app/templates/draft.html, app/main.py draft_view) after the
2026-09-14 rebuild: Figma DraftPageV2 layout, full sortable ratings table
with POT after OVR, used Team Picks replaced by the drafted player, and
acquisition tracking on drafted rookies. Every store and the DB are
isolated per test by tests/conftest.py.
"""
import os
import re

os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.core.db import DB_PATH, get_session
from app.engine import draft
from app.models.player import Player
from app.services import season_state, draft_class_store, draft_progress_store

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="data/franchise_football.db not built")

USER = "KC"


def _open_live_draft(user_slot: int = 1):
    """A live draft without simulating a whole season: the real stage flag,
    a real class, and a real progress record, with the user's team placed
    at `user_slot` (0-based) in the order."""
    from app.data.teams import TEAMS

    season_state.reset_season()
    season_state.set_user_team(USER)
    season = season_state.get_season()
    next_number = season.season_number + 1
    if draft_class_store.get_class(next_number) is None:
        draft_class_store.save_class(next_number, draft.generate_draft_class(season.league_seed, next_number))
    order = [t.abbr for t in TEAMS if t.abbr != USER]
    order.insert(user_slot, USER)
    season.offseason_stage = "draft"
    draft_progress_store.clear(next_number)  # start() is idempotent; the JSON store is session-shared
    draft_progress_store.start(next_number, order)
    return season, next_number


def test_live_draft_page_renders_full_sortable_ratings_with_pot_after_ovr():
    _open_live_draft()
    client = TestClient(app_module().app)
    resp = client.get("/draft")
    assert resp.status_code == 200
    html = resp.text
    assert "NFL Draft" in html
    headers = re.findall(r'<th[^>]*data-sort="([a-z]+)"', html)
    assert headers.index("ovr") + 1 == headers.index("pot")
    # Every rating column is present and sortable, Roster-page abbreviations first.
    for key, _label, _attr, _title in app_module().PROSPECT_RATING_COLUMNS:
        assert key in headers
    assert headers[headers.index("pot") + 1:headers.index("pot") + 4] == ["spd", "str", "agi"]
    # Filter chips carry real counts, and nothing on the page is a GET-reload sort link any more.
    assert re.search(r'data-group="ALL">ALL \d+<', html)
    assert "/draft?group=" not in html and "/draft?sort=" not in html


def test_prospect_rating_columns_cover_every_generated_attribute():
    main = app_module()
    covered = {attr for _k, _l, attr, _t in main.PROSPECT_RATING_COLUMNS if attr}
    # durability is shown as INJ (99 - durability) and the throw-accuracy
    # splits also roll up into TAC -- both derived, same as the Roster page.
    assert set(draft.ALL_ATTR_FIELDS) - covered == {"durability"}


def test_draft_page_your_roster_shows_offseason_progression_delta():
    """Brian's playtest report ("the roster on the draft page should be
    the same as on the roster page") -- the draft page's "Your Roster"
    table is a deliberately separate, client-side-sorted component (see
    draft.html's own comment on why), but it should still show the same
    real data the Roster page's table shows, including the Δ OVR column
    added there for the offseason-progression report."""
    from app.services import offseason_recap_store

    season, _next_number = _open_live_draft()
    season.season_number = 1
    try:
        with get_session() as s:
            kc_roster = list(s.exec(select(Player).where(Player.team_abbr == USER)))
        riser = max(kc_roster, key=lambda p: p.overall_rating)
        offseason_recap_store.save_before_snapshot(0, {riser.player_id: ("KC", riser.overall_rating - 5)})

        client = TestClient(app_module().app)
        html = client.get("/draft").text
        assert 'data-sort="delta"' in html
        assert '<span class="delta-up">+5</span>' in html
    finally:
        offseason_recap_store.clear_season(0)


def test_used_team_pick_shows_the_drafted_player_and_rookie_gets_acquisition_fields():
    season, next_number = _open_live_draft(user_slot=1)
    client = TestClient(app_module().app)

    resp = client.post("/draft/sim-pick", follow_redirects=False)
    assert resp.status_code == 303
    progress = draft_progress_store.get(next_number)
    assert progress["current_pick_index"] == 1

    prospects = draft_class_store.get_class(next_number)
    choice = next(p for p in prospects if p.index not in set(progress["drafted_indexes"]))
    resp = client.post("/draft/pick", data={"prospect_index": choice.index}, follow_redirects=False)
    assert resp.status_code == 303

    html = client.get("/draft").text
    label = f"{choice.first_name[0]}. {choice.last_name} ({choice.position.value})"
    assert label in html
    assert "Round 1 &middot; Pick #2" in html

    pick = draft_progress_store.get(next_number)["picks"][1]
    with get_session() as s:
        player = s.get(Player, pick["player_id"])
    assert player.team_abbr == USER
    assert player.acquisition_type == "Draft"
    assert player.acquisition_season == draft_season_year(next_number)
    assert player.acquisition_round == 1 and player.acquisition_pick == 2


def test_live_ai_picks_never_take_a_specialist_early():
    season, next_number = _open_live_draft(user_slot=31)
    client = TestClient(app_module().app)
    for _ in range(31):
        client.post("/draft/sim-pick", follow_redirects=False)
    picks = draft_progress_store.get(next_number)["picks"]
    assert len(picks) == 31
    assert not any(p["position"] in ("K", "P") for p in picks)


def test_prospects_mode_renders_before_the_draft_opens():
    season_state.reset_season()
    season_state.set_user_team(USER)
    season = season_state.get_season()
    if draft_class_store.get_class(season.season_number + 1) is None:
        draft_class_store.save_class(season.season_number + 1,
                                     draft.generate_draft_class(season.league_seed, season.season_number + 1))
    resp = TestClient(app_module().app).get("/draft")
    assert resp.status_code == 200
    assert "Team Needs" in resp.text and "Draft Board" in resp.text
    assert 'id="dp-table"' in resp.text


def app_module():
    import app.main as main
    return main


def draft_season_year(season_number: int) -> int:
    from app.config import season_year
    return season_year(season_number)
