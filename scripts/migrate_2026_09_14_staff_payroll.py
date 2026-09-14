"""
One-time staff payroll migration (Brian's 2026-09-14 fixes doc).

1. Each team keeps only its 4 highest-rated assistant coaches (Coach.overall);
   the rest are released to the unemployed coach pool (team_abbr=None).
2. Every coach salary is re-scaled onto Brian's real-world ranges while
   keeping each coach's rank within his role:
       HC  $4.0M - $10.0M (median $7.0M)
       OC  $1.0M - $2.5M  (median $1.5M)
       DC  $1.0M - $2.5M  (median $1.5M)
       ST  $0.7M - $1.5M  (median $1.0M)
       AC  $0.2M - $0.8M  (median $0.5M)
   A coach's percentile within his role maps piecewise-linearly through
   (0 -> min, 0.5 -> median, 1 -> max).
3. Any team whose 9-coach payroll still exceeds the 2026 staff cap ($15M,
   app/engine/contracts.py COACH_SALARY_CAP_2026) has its whole staff scaled
   down proportionally to land just under it.

Idempotent in effect: a DB that already has <=4 ACs per team and every
salary inside its role range is re-mapped onto the same ranks, so running it
twice gives the same result. Pass DB paths as arguments; defaults to the
template and the legacy/test database.

    python scripts/migrate_2026_09_14_staff_payroll.py [db ...]
"""
from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

MAX_ASSISTANTS = 4
STAFF_CAP_2026 = 15_000_000
CAP_HEADROOM = 0.995  # land just under, not exactly on, the cap

RANGES: dict[str, tuple[int, int, int]] = {
    "HC": (4_000_000, 7_000_000, 10_000_000),
    "OC": (1_000_000, 1_500_000, 2_500_000),
    "DC": (1_000_000, 1_500_000, 2_500_000),
    "ST": (700_000, 1_000_000, 1_500_000),
    "AC": (200_000, 500_000, 800_000),
}

PERF_COLS = ("player_dev_offense", "player_dev_defense", "discipline",
             "motivation_chemistry", "red_zone_offense", "red_zone_defense")


def _overall(row: sqlite3.Row) -> float:
    perf = sum(row[c] for c in PERF_COLS) / 6.0
    return 0.5 * perf + 0.5 * row["reputation"]


def _map_salary(pct: float, role: str) -> int:
    lo, mid, hi = RANGES[role]
    if pct <= 0.5:
        value = lo + (mid - lo) * (pct / 0.5)
    else:
        value = mid + (hi - mid) * ((pct - 0.5) / 0.5)
    return int(round(value / 10_000) * 10_000)


def migrate(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = list(conn.execute("SELECT * FROM coach WHERE retired = 0"))
    if not rows:
        print(f"{db_path}: no coaches, skipped")
        return

    # 1. Trim assistants to 4 per team.
    acs_by_team: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        if r["role"] == "AC" and r["team_abbr"]:
            acs_by_team[r["team_abbr"]].append(r)
    released = 0
    for team, acs in acs_by_team.items():
        keep = sorted(acs, key=lambda r: (-_overall(r), r["coach_id"]))[:MAX_ASSISTANTS]
        keep_ids = {r["coach_id"] for r in keep}
        for r in acs:
            if r["coach_id"] not in keep_ids:
                conn.execute(
                    "UPDATE coach SET team_abbr = NULL, contract_years = 0 WHERE coach_id = ?",
                    (r["coach_id"],),
                )
                released += 1

    # 2. Re-map salaries by rank within role (every non-retired coach with a
    #    real salary, employed or not, so the unemployed pool stays on scale).
    rows = list(conn.execute("SELECT * FROM coach WHERE retired = 0"))
    by_role: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        if r["salary_aav"] > 0 and r["role"] in RANGES:
            by_role[r["role"]].append(r)
    new_salary: dict[str, int] = {}
    for role, members in by_role.items():
        members.sort(key=lambda r: (r["salary_aav"], r["coach_id"]))
        n = len(members)
        for i, r in enumerate(members):
            pct = i / (n - 1) if n > 1 else 0.5
            new_salary[r["coach_id"]] = _map_salary(pct, role)

    # 3. Fit each team under the staff cap.
    team_members: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if r["team_abbr"] and r["coach_id"] in new_salary:
            team_members[r["team_abbr"]].append(r["coach_id"])
    scaled_teams = 0
    for team, ids in team_members.items():
        total = sum(new_salary[c] for c in ids)
        if total > STAFF_CAP_2026:
            factor = STAFF_CAP_2026 * CAP_HEADROOM / total
            for c in ids:
                new_salary[c] = int(new_salary[c] * factor // 10_000 * 10_000)
            scaled_teams += 1

    for coach_id, salary in new_salary.items():
        conn.execute("UPDATE coach SET salary_aav = ? WHERE coach_id = ?", (salary, coach_id))
    conn.commit()

    totals = (
        conn.execute("SELECT SUM(salary_aav) FROM coach WHERE team_abbr IS NOT NULL AND retired = 0 GROUP BY team_abbr")
    )
    t = sorted(x[0] for x in totals)
    print(f"{db_path}: released {released} assistants; {scaled_teams} teams scaled to fit; "
          f"payroll min ${t[0]:,} median ${t[len(t)//2]:,} max ${t[-1]:,}")
    conn.close()


def main() -> None:
    paths = [Path(a) for a in sys.argv[1:]] or [
        Path("data/franchise_template.db"), Path("data/franchise_football.db"),
    ]
    for p in paths:
        if p.exists():
            migrate(p)
        else:
            print(f"{p}: not found, skipped")


if __name__ == "__main__":
    main()
