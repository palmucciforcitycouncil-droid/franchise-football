"""
One-off migration: adds R13's new `Coach.focus_area` column to a database
(docs/R13_COACH_FOCUS_AREA_SPECIFICATION.md).

Same convention as migrate_add_r3d_coach_fields.py: SQLite ALTER TABLE ADD
COLUMN with a real default for every existing row, a timestamped `.bak-*`
snapshot taken first, safe to re-run (skips the ALTER if the column already
exists). Unlike a plain ADD COLUMN migration, this one THEN runs a real
per-row UPDATE pass -- every coach gets a real, role/specialty-aware default
(app.models.coach.default_focus_area_for(), Sec 4 of the spec) instead of one
flat value for every row, using the SAME heuristic scripts/import_coaches.py
uses for a fresh import so both paths agree.

Generalized 2026-09-14 (found via a real incident: the Staff page showed
"no coaching staff imported" for a save whose `coach` table genuinely had
533 rows -- `coach_store._all_coaches_uncached()`'s `except OperationalError:
return []` was silently swallowing "no such column: coach.focus_area" for
every db copied/created before this migration ran against it, which the
save-per-save architecture (app/services/save_manager.py) means is now
MANY files, not the one legacy `data/franchise_football.db` this script
originally assumed). Takes paths as CLI args now; defaults to the legacy
db alone when none are given, unchanged from the original behavior.

Usage:
    .venv/Scripts/python.exe scripts/migrate_add_r13_focus_area.py
    .venv/Scripts/python.exe scripts/migrate_add_r13_focus_area.py path/to/one.db path/to/two.db
"""
from __future__ import annotations
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.coach import CoachRole, default_focus_area_for

DEFAULT_DB_PATH = Path("data/franchise_football.db")


def migrate_one(db_path: Path) -> None:
    if not db_path.exists():
        print(f"No database at {db_path} -- nothing to migrate.")
        return

    con = sqlite3.connect(db_path)
    try:
        existing = {row[1] for row in con.execute("PRAGMA table_info(coach)")}
        if not existing:
            print(f"{db_path}: no 'coach' table in this database -- nothing to migrate.")
            return

        if "focus_area" in existing:
            print(f"{db_path}: already has coach.focus_area -- nothing to do.")
            return

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = db_path.with_name(f"{db_path.name}.bak-prer13focusarea-{stamp}")
        shutil.copy(db_path, backup)
        print(f"{db_path}: backed up -> {backup}")

        con.execute("ALTER TABLE coach ADD COLUMN focus_area TEXT NOT NULL DEFAULT 'Development'")
        print(f"{db_path}: added column coach.focus_area TEXT NOT NULL DEFAULT 'Development'")
        con.commit()

        rows = con.execute("SELECT coach_id, role, specialty FROM coach").fetchall()
        updated = 0
        for coach_id, role, specialty in rows:
            focus = default_focus_area_for(CoachRole(role), specialty)
            con.execute("UPDATE coach SET focus_area = ? WHERE coach_id = ?", (focus, coach_id))
            updated += 1
        con.commit()
        print(f"{db_path}: assigned a real default focus_area to {updated} coach(es).")
    finally:
        con.close()


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:]] or [DEFAULT_DB_PATH]
    for db_path in paths:
        migrate_one(db_path)
    print("Migration complete.")


if __name__ == "__main__":
    main()
