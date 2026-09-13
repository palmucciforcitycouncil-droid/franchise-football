"""
One-off data cleanup: removes stale, never-real championship credit that
leaked into the live `data/franchise_football.db` from an old test-
isolation gap in `tests/conftest.py`'s `_isolate_db_path` fixture
(fixed 2026-09-12 -- see that fixture's own docstring for the full
account, and ROADMAP.md's R3d entry).

**How this was found:** `test_coaching.py`'s `completed_season` fixture
fully simulates a real season + playoffs against its own throwaway DB
copy and calls `coach_records.credit_championship_round()` directly
against it -- entirely safe IF that throwaway redirect is what
`get_session()` actually uses. Before the 2026-09-12 fix, an earlier
version of this isolation had (at least twice, over this project's
history) let that write land on the REAL `franchise_football.db`
instead, crediting a fully fictional Super Bowl outcome as if it were
real.

**How this is detected, precisely:** a coach's `career_wins`/
`career_losses` are ONLY ever written by `coach_records.
record_season_results()`, which runs exactly once per REAL season
rollover and ALWAYS accompanies any real championship credit (a team
can't win a Super Bowl without a real 17-game regular season on the
books first). A coach showing a Super Bowl/conference title credit
with career_wins == 0 AND career_losses == 0 is therefore, by
construction, impossible to have earned for real -- exactly the
signature every one of the 40 polluted rows found on 2026-09-12 has
(2 phantom playoff runs: CIN over MIN in one, an ATL run in another --
matched against real history_store.get_history()[0], which shows CIN
actually went 2-14 in real season 0, not a championship season).

Resets every affected Coach's 15 championship-rollup fields + sb_titles
to zero, and deletes their now-orphaned CoachSeasonStats rows entirely
(those rows only exist because of this same bad credit -- a coach with
0 real career games never had a legitimate season recorded).

Safe to re-run (finds nothing once already clean). Takes a timestamped
`.bak-*` backup first, same convention as every other one-off DB
migration in this project (see scripts/migrate_add_r3d_coach_fields.py).
"""
from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path

from sqlmodel import select

from app.core.db import get_session, DB_PATH
from app.models.coach import Coach, CoachSeasonStats

CHAMPIONSHIP_FIELDS = [
    "hc_afc_championships", "hc_nfc_championships", "hc_super_bowl_wins",
    "oc_afc_championships", "oc_nfc_championships", "oc_super_bowl_wins",
    "dc_afc_championships", "dc_nfc_championships", "dc_super_bowl_wins",
    "st_afc_championships", "st_nfc_championships", "st_super_bowl_wins",
    "ac_afc_championships", "ac_nfc_championships", "ac_super_bowl_wins",
]


def find_polluted(session) -> list[Coach]:
    coaches = list(session.exec(select(Coach)))
    return [
        c for c in coaches
        if (c.super_bowl_wins or c.conference_titles or c.sb_titles)
        and c.career_wins == 0 and c.career_losses == 0
    ]


def main() -> None:
    with get_session() as session:
        polluted = find_polluted(session)
        print(f"Polluted coaches found: {len(polluted)}")
        for c in polluted:
            print(f"  {c.coach_id} ({c.team_abbr}) sb_wins={c.super_bowl_wins} "
                  f"conf_titles={c.conference_titles} career={c.career_wins}-{c.career_losses}")

        if not polluted:
            print("Nothing to clean.")
            return

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = Path(str(DB_PATH) + f".bak-precoachpollutioncleanup-{stamp}")
        shutil.copy(DB_PATH, backup)
        print(f"Backed up {DB_PATH} -> {backup}")

        polluted_ids = {c.coach_id for c in polluted}
        for c in polluted:
            for field in CHAMPIONSHIP_FIELDS:
                setattr(c, field, 0)
            c.sb_titles = 0
            session.add(c)

        stale_rows = [
            r for r in session.exec(select(CoachSeasonStats))
            if r.coach_id in polluted_ids
        ]
        print(f"Deleting {len(stale_rows)} orphaned CoachSeasonStats rows")
        for row in stale_rows:
            session.delete(row)

        session.commit()

    with get_session() as session:
        remaining = find_polluted(session)
        print(f"Remaining polluted coaches after cleanup: {len(remaining)}")


if __name__ == "__main__":
    main()
