"""
Persistent Draft Pick ownership (GDD Part 1 Sec 8.5: trades "can include
players and picks from the current draft and the next two drafts").

**The real gap this closes**: app/engine/draft.py's compute_draft_order()
has always computed a fresh worst-to-best team list every season, with
NO ownership indirection anywhere -- the slot IS the team, with nowhere
for a traded pick to live (confirmed: no DraftPick/pick-ownership entity
existed anywhere in this codebase before this module). This store is
that missing persistent layer: for every (season_number, round,
original_team_abbr) slot across the current season plus the next two,
who currently owns the right to make that pick. A team owns its own
picks by default; app/engine/trades.py's execute_trade() is the only
real write path that ever moves one.

**"Original" vs. "owner", and why both matter**: the SLOT is still
earned by the ORIGINAL team's real record -- app/engine/draft.py's
compute_draft_order() is completely UNCHANGED by this module, still a
pure function of real standings. Trading a pick only ever changes who
gets to MAKE it, never which record-rank it represents -- the same real
distinction a traded first-round pick has in the NFL (it's still "the
Bears' natural first," just owned by whoever traded for it).

**Lookahead window**: exactly 3 draft-years of inventory exist at any
time (this season's + the next two, per Sec 8.5's own "current draft and
the next two drafts"). `ensure_lookahead_seeded()` is called once per
real rollover (app/services/season_state.py's `_build_season()`) to keep
that window current; `consume_season()` is called once a season's real
draft actually runs (app/engine/draft.py's `run_draft_for_season()`),
since a resolved pick is no longer a tradeable future asset.

Persisted as JSON (data/saves/pick_inventory.json, gitignored), same
DEFAULT_PATH-resolved-at-call-time convention as draft_store.py/every
other *_history.py store in this project -- isolates in tests the same
way. READ ROADMAP.md Sec2's incident history before adding a standalone
script that touches this without redirecting DEFAULT_PATH first.
"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.data.teams import TEAMS

DEFAULT_PATH = Path("data/saves/pick_inventory.json")

ROUNDS = 7
LOOKAHEAD_SEASONS = 3  # Sec 8.5: "the current draft and the next two drafts"


@dataclass(frozen=True)
class PickAsset:
    season_number: int
    round: int
    original_team_abbr: str
    current_owner_abbr: str

    @property
    def pick_id(self) -> str:
        """A stable, parseable string id for this exact pick slot -- used
        as the HTML checkbox `value` on the GM Desk trade panel."""
        return f"{self.season_number}_{self.round}_{self.original_team_abbr}"


def parse_pick_id(pick_id: str) -> tuple[int, int, str]:
    """(season_number, round, original_team_abbr) -- the inverse of
    PickAsset.pick_id, for parsing a submitted trade form's checkbox
    values back into a real pick reference."""
    season_str, round_str, team_abbr = pick_id.split("_", 2)
    return int(season_str), int(round_str), team_abbr


def _load(path: Path | None) -> list[dict]:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _save(entries: list[dict], path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def all_picks(path: Path | None = None) -> list[PickAsset]:
    return [PickAsset(**d) for d in _load(path)]


def picks_owned_by(team_abbr: str, path: Path | None = None) -> list[PickAsset]:
    return sorted(
        (p for p in all_picks(path) if p.current_owner_abbr == team_abbr),
        key=lambda p: (p.season_number, p.round),
    )


def owner_of(season_number: int, round: int, original_team_abbr: str, path: Path | None = None) -> str:
    """Who currently owns this slot -- the original team, unless a real
    trade moved it. Defaults to the original team even if this exact
    slot was never explicitly seeded (a genuinely fresh save/test that
    skipped ensure_lookahead_seeded()), so a missing inventory never
    breaks the draft -- same graceful-degradation guarantee every other
    coaching/focus hook in this engine already has for an absent store.

    A single-slot lookup -- fine for one-off callers (the GM Desk trade
    route), but re-reads and re-parses the ENTIRE inventory file from
    disk every call. app/engine/draft.py's simulate_draft() asks this
    once per (round, team) -- 224 times for a full 7-round/32-team draft
    -- so it uses owners_for_season() below instead, the same
    "fetch once up front" precedent this module's own docstring already
    follows for _all_teams_group_counts()."""
    for p in all_picks(path):
        if (p.season_number, p.round, p.original_team_abbr) == (season_number, round, original_team_abbr):
            return p.current_owner_abbr
    return original_team_abbr


def owners_for_season(season_number: int, path: Path | None = None) -> dict[tuple[int, str], str]:
    """Every (round, original_team_abbr) -> current_owner_abbr mapping for
    one draft season, in a single file read -- the bulk equivalent of
    calling owner_of() in a loop. A slot missing from the returned dict
    means untraded (still owned by the original team), matching
    owner_of()'s own default -- callers should look up with
    `.get((round, original_team_abbr), original_team_abbr)`."""
    return {
        (p.round, p.original_team_abbr): p.current_owner_abbr
        for p in all_picks(path) if p.season_number == season_number
    }


def ensure_lookahead_seeded(current_season_number: int, path: Path | None = None) -> None:
    """Guarantees every team owns its own real pick, every round, for
    `current_season_number` through `current_season_number + 2` (Sec
    8.5's 3-draft lookahead) -- called once per real rollover so the
    inventory always covers a full window, never left short as seasons
    advance. Existing entries (already-traded picks included) are
    untouched; only genuinely missing (season, round, team) slots get a
    fresh, owned-by-the-original-team entry."""
    entries = _load(path)
    existing = {(e["season_number"], e["round"], e["original_team_abbr"]) for e in entries}
    added = False
    for offset in range(LOOKAHEAD_SEASONS):
        season_number = current_season_number + offset
        for team in TEAMS:
            for rnd in range(1, ROUNDS + 1):
                key = (season_number, rnd, team.abbr)
                if key not in existing:
                    entries.append(asdict(PickAsset(season_number, rnd, team.abbr, team.abbr)))
                    existing.add(key)
                    added = True
    if added:
        _save(entries, path)


def transfer_pick(season_number: int, round: int, original_team_abbr: str, new_owner_abbr: str,
                   path: Path | None = None) -> None:
    """The one real write path (app/engine/trades.py's execute_trade()).
    Creates the slot (previously owned by the original team) if it
    somehow wasn't already seeded, rather than silently no-op-ing."""
    entries = _load(path)
    for e in entries:
        if (e["season_number"], e["round"], e["original_team_abbr"]) == (season_number, round, original_team_abbr):
            e["current_owner_abbr"] = new_owner_abbr
            _save(entries, path)
            return
    entries.append(asdict(PickAsset(season_number, round, original_team_abbr, new_owner_abbr)))
    _save(entries, path)


def consume_season(season_number: int, path: Path | None = None) -> list[PickAsset]:
    """Removes and returns every pick for `season_number` -- called once
    that season's real draft has actually run (app/engine/draft.py's
    run_draft_for_season()), since a resolved pick is no longer a
    tradeable future asset."""
    entries = _load(path)
    consumed = [PickAsset(**e) for e in entries if e["season_number"] == season_number]
    remaining = [e for e in entries if e["season_number"] != season_number]
    if consumed:
        _save(remaining, path)
    return consumed
