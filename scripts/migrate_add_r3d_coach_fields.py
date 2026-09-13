"""
One-off migration: adds R3d's four new Coach columns to the live
database (app/models/coach.py's `appointment_type`, `tenure_start_season`,
`pool_tier`, `background`).

Same convention as the 2026-09-11 `clock_management`/`challenge_sense`
DROP COLUMN migration (ROADMAP.md Sec 4c-addendum): SQLite ALTER TABLE
ADD COLUMN with a real default for every existing row, a timestamped
`.bak-*` snapshot taken first. Safe to re-run -- skips any column that
already exists.
"""
from __future__ import annotations
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/franchise_football.db")

NEW_COLUMNS = [
    ("appointment_type", "TEXT NOT NULL DEFAULT 'Permanent'"),
    ("tenure_start_season", "INTEGER NOT NULL DEFAULT 0"),
    ("pool_tier", "TEXT"),
    ("background", "TEXT"),
]


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
        todo = [(name, ddl) for name, ddl in NEW_COLUMNS if name not in existing]
        if not todo:
            print("All R3d columns already present -- nothing to do.")
            return

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = DB_PATH.with_name(f"{DB_PATH.name}.bak-prer3dcoachfields-{stamp}")
        shutil.copy(DB_PATH, backup)
        print(f"Backed up {DB_PATH} -> {backup}")

        for name, ddl in todo:
            con.execute(f"ALTER TABLE coach ADD COLUMN {name} {ddl}")
            print(f"Added column coach.{name} {ddl}")
        con.commit()
    finally:
        con.close()

    print("Migration complete.")


if __name__ == "__main__":
    main()
