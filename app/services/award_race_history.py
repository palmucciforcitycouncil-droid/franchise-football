"""
Persisted weekly Awards Race snapshots (R8: Awards Page).

Same JSON-dict-keyed-by-season_number convention as
app/services/power_rank_history.py, for the same reason: the Awards
page's "Weekly Race Archive" tab needs to show every past week's Top-5
per award side by side, which nothing else in this engine retains --
awards.py's own functions only ever compute the CURRENT state from the
season's games so far, with no memory of what last week's leaderboard
looked like. season_state.simulate_current_week() calls
record_week_awards() once per simulated week (right after its own
Power Ranking snapshot), the same "one real place this is known" timing
power_rank_history.py's own docstring describes.

Persisted as JSON (data/saves/, gitignored) via DEFAULT_PATH resolved at
call time, not baked in at import, so tests can redirect it -- same
test-isolation convention as every other store in this family (see
tests/conftest.py's session-scoped fixture, which redirects this
module's DEFAULT_PATH alongside power_rank_history's/save_service's for
the whole pytest run).
"""
from __future__ import annotations
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

DEFAULT_PATH = Path("data/saves/award_race_history.json")


def _to_plain(value):
    """Dataclass award candidates (AwardCandidate/CoachAwardCandidate/
    ProBowlStarter, app/engine/awards.py) -> plain JSON-safe dicts;
    everything else passes through unchanged. Recurses into lists/dicts
    so a snapshot dict built directly from awards.py's own return values
    (no manual asdict() calls needed at the call site) round-trips."""
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    return value


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_week_awards(season_number: int, week_num: int, awards_snapshot: dict, path: Path | None = None) -> None:
    """awards_snapshot: a plain dict (or one built straight from
    awards.py dataclass instances -- see _to_plain above) with whatever
    keys the caller wants to retain for that week; season_state.py's own
    caller builds:
        {
            "mvp": [...], "opoy": [...], "dpoy": [...],
            "oroy": [...], "droy": [...], "coty": [...],
            "pro_bowl": {"AFC": {...}, "NFC": {...}},
        }
    """
    data = _load(path)
    data.setdefault(str(season_number), {})[str(week_num)] = _to_plain(awards_snapshot)
    _save(data, path)


def get_week_awards(season_number: int, week_num: int, path: Path | None = None) -> dict | None:
    """None if that week was never recorded (before this store existed,
    week 0/negative, or a week later than any simulated so far) -- the
    caller's job to treat that as "no snapshot," not a fabricated empty
    one."""
    return _load(path).get(str(season_number), {}).get(str(week_num))


def get_all_weeks(season_number: int, path: Path | None = None) -> dict[str, dict]:
    """{week_num_str: snapshot} for every week recorded so far this
    season, in whatever order the JSON store happens to hold them --
    callers that need week order (the Weekly Race Archive table) sort
    the keys themselves."""
    return _load(path).get(str(season_number), {})
