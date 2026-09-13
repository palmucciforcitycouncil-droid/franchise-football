"""
Persisted, full-detail draft PROSPECT CLASSES (Brian's ask, 2026-09-13:
the Draft page should show next season's prospects for browsing/ranking
all season, not just after the draft resolves) -- keyed by the season
number the class will be drafted INTO, same convention as
app/services/draft_store.py's own picks-by-season keying.

Distinct from draft_store.py: that module only ever recorded the
OUTCOME of a completed draft (8 shallow fields per pick, nothing for
undrafted prospects). This module persists the full
app.engine.draft.ProspectDraft list itself -- every attribute, not just
overall_rating -- so a Prospects grid, a personal draft board, and the
live pick-by-pick engine (app/services/draft_progress_store.py) all
read from the SAME real prospect data the draft will actually resolve
against, rather than three different partial views of it.

Persisted as JSON (data/saves/, gitignored), same DEFAULT_PATH-resolved-
at-call-time convention as every other *_store.py in this project --
isolates in tests the same way. READ ROADMAP.md Sec2's incident history
before adding a standalone script that touches this without redirecting
DEFAULT_PATH first.
"""
from __future__ import annotations
import json
from pathlib import Path

from app.engine.draft import ProspectDraft
from app.models.player import Position

DEFAULT_PATH = Path("data/saves/draft_classes.json")


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _prospect_to_dict(p: ProspectDraft) -> dict:
    return {
        "index": p.index, "first_name": p.first_name, "last_name": p.last_name,
        "position": p.position.value, "college": p.college, "age": p.age,
        "height_inches": p.height_inches, "weight_lbs": p.weight_lbs,
        "overall_rating": p.overall_rating, "potential": p.potential,
        "attrs": p.attrs, "draft_grade": p.draft_grade, "group": p.group,
    }


def _prospect_from_dict(d: dict) -> ProspectDraft:
    return ProspectDraft(
        index=d["index"], first_name=d["first_name"], last_name=d["last_name"],
        position=Position(d["position"]), college=d["college"], age=d["age"],
        height_inches=d["height_inches"], weight_lbs=d["weight_lbs"],
        overall_rating=d["overall_rating"], potential=d["potential"],
        attrs=d["attrs"], draft_grade=d["draft_grade"], group=d.get("group", ""),
    )


def save_class(season_number: int, prospects: list[ProspectDraft], path: Path | None = None) -> None:
    data = _load(path)
    data[str(season_number)] = [_prospect_to_dict(p) for p in prospects]
    _save(data, path)


def get_class(season_number: int, path: Path | None = None) -> list[ProspectDraft] | None:
    """None if this season's class was never generated yet (a save from
    before this store existed, or a season further out than has been
    reached) -- the caller's job to fall back to generating it on the
    spot (app.engine.draft.generate_draft_class is deterministic, so a
    late/missing generation still produces the exact same class), not
    to fabricate one."""
    raw = _load(path).get(str(season_number))
    if raw is None:
        return None
    return [_prospect_from_dict(d) for d in raw]


def has_class(season_number: int, path: Path | None = None) -> bool:
    return str(season_number) in _load(path)


def clear_class(season_number: int, path: Path | None = None) -> None:
    """Called once a season's draft actually resolves -- the class has
    become real Player rows by then (drafted) or free agents
    (undrafted), so keeping the raw prospect list around too would be
    stale, unreachable duplicate data."""
    data = _load(path)
    data.pop(str(season_number), None)
    _save(data, path)
