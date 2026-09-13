"""
One-off migration: adds R13's new `Coach.focus_area` column to the live
database (docs/R13_COACH_FOCUS_AREA_SPECIFICATION.md).

Same convention as migrate_add_r3d_coach_fields.py: SQLite ALTER TABLE ADD
COLUMN with a real default for every existing row, a timestamped `.bak-*`
snapshot taken first, safe to re-run (skips the ALTER if the column already
exists). Unlike a plain ADD COLUMN migration, this one THEN runs a real
per-row UPDATE pass -- every coach gets a real, role/specialty-aware default
(app.models.coach.default_focus_area_for(), Sec 4 of the spec) instead of one
flat value for every row, using the SAME heuristic scripts/import_coaches.py
uses for a fresh import so both paths agree.
"""
from __future__ import annotations
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.coach import CoachRole, default_focus_area_for

DB_PATH = Path("data/franchise_football.db")


def main() -> None:
    if not DB_PATH.exists():
        print(f"No database at {DB_PATH} -- nothing to migrate.")
        return

    con = sqlite3.connect(DB_PATH)
    try:
        existing = {row[1] for row in con.execute("PRAGMA table_info(coach)")}
        if not existing:
            print("No 'coach' table in this database -- nothing to migrate.")
            return

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = DB_PATH.with_name(f"{DB_PATH.name}.bak-prer13focusarea-{stamp}")
        shutil.copy(DB_PATH, backup)
        print(f"Backed up {DB_PATH} -> {backup}")

        if "focus_area" not in existing:
            con.execute("ALTER TABLE coach ADD COLUMN focus_area TEXT NOT NULL DEFAULT 'Development'")
            print("Added column coach.focus_area TEXT NOT NULL DEFAULT 'Development'")
            con.commit()

        rows = con.execute("SELECT coach_id, role, specialty FROM coach").fetchall()
        updated = 0
        for coach_id, role, specialty in rows:
            focus = default_focus_area_for(CoachRole(role), specialty)
            con.execute("UPDATE coach SET focus_area = ? WHERE coach_id = ?", (focus, coach_id))
            updated += 1
        con.commit()
        print(f"Assigned a real default focus_area to {updated} coach(es).")
    finally:
        con.close()

    print("Migration complete.")


if __name__ == "__main__":
    main()
