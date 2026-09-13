"""
Builds data/franchise_template_history.json -- the real, pristine
2002-2025 NFL-history-imported League History every NEW save's own
history.json is seeded from (app/services/save_manager.py's
TEMPLATE_HISTORY_PATH), mirroring how TEMPLATE_DB_PATH is itself built
by running scripts/import_players.py + scripts/import_coaches.py, then
copying the result into place.

Source: the real, LIVE data/saves/history.json (history_store.
DEFAULT_PATH) -- which scripts/import_nfl_history.py seeds with the
real 2002-2025 seasons first, then keeps growing forever with every
season a franchise actually plays on top (history_store.py's own
docstring: "one continuous, ever-growing league timeline"). This script
does NOT assume the real-imported run is exactly 24 seasons long -- it
finds the real boundary the same way app/main.py's Team History Power
Rank box already does: every real-imported season shares one flat
placeholder power_rating (1500.0, import_nfl_history.py's own disclosed
docstring -- no real historical Power Rating exists to import), while
any simulated/user-played season has a real spread from actual play.
The first season with a real spread is the cutoff; only the real, flat
-rated seasons before it go into the template.

Read-only against the source file -- never modifies data/saves/history.json.

Usage:
    .venv/Scripts/python.exe scripts/build_franchise_template_history.py
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import history_store
from app.services.save_manager import TEMPLATE_HISTORY_PATH


def _has_real_power_rating_spread(record: history_store.SeasonRecord) -> bool:
    return len({t.power_rating for t in record.team_results}) > 1


def main() -> None:
    records = history_store.get_history()
    if not records:
        print(f"No archived seasons at {history_store.DEFAULT_PATH} -- nothing to build "
              "from. Run scripts/import_nfl_history.py first.")
        return

    boundary = next(
        (i for i, r in enumerate(records) if _has_real_power_rating_spread(r)),
        len(records),
    )
    if boundary == 0:
        print("The first archived season already has a real power-rating spread -- "
              "no flat, real-imported seasons found. Nothing written.")
        return

    template = records[:boundary]
    TEMPLATE_HISTORY_PATH.unlink(missing_ok=True)  # full rebuild, not an incremental append
    for record in template:
        history_store.append_season_record(record, path=TEMPLATE_HISTORY_PATH)

    print(f"Wrote {boundary} real season(s) (season_number {template[0].season_number}.."
          f"{template[-1].season_number}) to {TEMPLATE_HISTORY_PATH}.")
    if boundary < len(records):
        print(f"({len(records) - boundary} later, user-played season(s) in the source "
              "file were correctly excluded.)")


if __name__ == "__main__":
    main()
