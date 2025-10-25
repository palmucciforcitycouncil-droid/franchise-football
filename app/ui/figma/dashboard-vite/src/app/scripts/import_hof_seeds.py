# app/scripts/import_hof_seeds.py
from __future__ import annotations
import csv
from pathlib import Path
from sqlmodel import Session
from app.db import get_engine
from app.models.hof import HOFInductee

def import_hof_csv(csv_path: Path, subject_type: str, class_year: int):
    """Import HOF inductees from CSV seed file."""
    engine = get_engine()
    with Session(engine) as sess:
        with open(csv_path, newline='', encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                subj_id = int(row.get("id") or row.get("player_id") or row.get("coach_id") or 0)
                if not subj_id: 
                    continue
                sess.add(HOFInductee(
                    subject_type=subject_type, 
                    subject_id=subj_id, 
                    class_year=class_year, 
                    citation="Seed"
                ))
        sess.commit()

if __name__ == "__main__":
    base = Path("data/seeds")
    import_hof_csv(base/"HOF Players Seed - Sheet1.csv", "PLAYER", 2024)
    import_hof_csv(base/"HOF Coaches Seed - Sheet1.csv", "COACH", 2024)


