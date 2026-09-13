"""
The user's own personal draft board -- a reordered shortlist of
prospect indexes for one season's class (Brian's ask, 2026-09-13: "the
player can move their draft board around during the season"). Purely a
reference/planning tool: confirmed with Brian that this never feeds
into the real, automatically-simulated AI picks anywhere -- it only
ever affects what THIS store itself returns. Keyed by season number,
same convention as draft_store.py/draft_class_store.py.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/draft_board.json")


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_board(season_number: int, path: Path | None = None) -> list[int]:
    return _load(path).get(str(season_number), [])


def add(season_number: int, prospect_index: int, path: Path | None = None) -> list[int]:
    """Appends to the end of the board; a no-op if already on it."""
    data = _load(path)
    key = str(season_number)
    board = data.setdefault(key, [])
    if prospect_index not in board:
        board.append(prospect_index)
        _save(data, path)
    return board


def remove(season_number: int, prospect_index: int, path: Path | None = None) -> list[int]:
    data = _load(path)
    key = str(season_number)
    board = data.get(key, [])
    if prospect_index in board:
        board.remove(prospect_index)
        data[key] = board
        _save(data, path)
    return board


def move(season_number: int, prospect_index: int, direction: str, path: Path | None = None) -> list[int]:
    """direction: "up" or "down" -- swaps with the adjacent entry. A
    no-op at either end of the list (no wraparound), and a no-op if
    prospect_index isn't on the board at all."""
    data = _load(path)
    key = str(season_number)
    board = data.get(key, [])
    if prospect_index not in board:
        return board
    i = board.index(prospect_index)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(board):
        board[i], board[j] = board[j], board[i]
        data[key] = board
        _save(data, path)
    return board


def clear_season(season_number: int, path: Path | None = None) -> None:
    """Called once that season's draft resolves -- the board was scoped
    to prospects that no longer exist as a pending class afterward."""
    data = _load(path)
    data.pop(str(season_number), None)
    _save(data, path)
