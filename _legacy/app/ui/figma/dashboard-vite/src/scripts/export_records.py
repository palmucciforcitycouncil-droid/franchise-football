# scripts/export_records.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse, csv
from sqlmodel import Session, select
from app.db import get_engine
from app.models.records import SingleSeasonRecord, CareerRecord

def main():
    ap = argparse.ArgumentParser(description="Export records to CSV")
    ap.add_argument("--outdir", default="data/reports")
    args = ap.parse_args()

    from pathlib import Path
    d = Path(args.outdir); d.mkdir(parents=True, exist_ok=True)
    with Session(get_engine()) as s:
        ss = s.exec(select(SingleSeasonRecord).order_by(SingleSeasonRecord.stat, SingleSeasonRecord.season, SingleSeasonRecord.rank)).all()
        cr = s.exec(select(CareerRecord).order_by(CareerRecord.stat, CareerRecord.rank)).all()
        with (d/"single_season_records.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["season","stat","rank","player_id","player_name","team_id","value"])
            for r in ss: w.writerow([r.season,r.stat,r.rank,r.player_id,r.player_name,r.team_id,r.value])
        with (d/"career_records.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["stat","rank","player_id","player_name","value"])
            for r in cr: w.writerow([r.stat,r.rank,r.player_id,r.player_name,r.value])
        print("Exported:", d/"single_season_records.csv", d/"career_records.csv")

if __name__ == "__main__":
    main()
