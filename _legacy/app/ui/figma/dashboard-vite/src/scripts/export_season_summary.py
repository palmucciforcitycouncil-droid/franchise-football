#!/usr/bin/env python3
"""
Season Export CLI Script.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, create_engine
from app.services.season_export import export_season_summary


if __name__ == "__main__":
    engine = create_engine("sqlite:///:memory:", future=True)
    with Session(engine) as session:
        season = 2025
        payload = export_season_summary(
            session, 
            season, 
            out_json="data/reports/season_2025_summary.json", 
            out_html="data/reports/season_2025_summary.html"
        )
        print("Exported season summary with keys:", list(payload.keys()))
        print("Leaders sections:", [b['title'] for b in payload['leaders']])
