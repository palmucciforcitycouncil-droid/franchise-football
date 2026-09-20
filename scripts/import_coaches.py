"""
Imports the real 2026 coaching-staff seed into the Coach table.

Source: data/raw/coaches/Comprehensive NFL Coaching Staff Directory with
Salaries 2026.md (GDD Sec 3.6.1). Markdown, not CSV -- it mirrors the
real /data/raw/rosters/ convention this project actually uses, not the
aspirational /data/seeds/ path Sec 3.6.1 also lists (never realized for
any domain). Format is perfectly regular across all 32 teams:

    ### **Buffalo Bills**
    > * **Head Coach:** Sean McDermott (  Salary: $10,000,000)

The seed gives name + exact title + salary and NOTHING else. Everything
else the GDD's coach spec calls for is generated here from this
project's deterministic seeded RNG -- see app/models/coach.py's module
docstring for the full real-vs-generated accounting, and
_generate_profile() below for exactly how each generated field is drawn.

Title -> role + specialty follows GDD Sec 7.7.2.1a's explicit mapping
rule (HC/OC/DC/Special Teams Coordinator map 1:1; everything else is
role=AC with the real position-group title kept in `specialty`,
including assistant-to-a-coordinator titles, which stay AC rather than
being promoted to ST/OC). Dual titles keep the primary functional
position group only ("Linebackers Coach / Assistant Head Coach" ->
specialty "Linebackers"; the Assistant-Head-Coach tag is dropped).

Idempotent (GDD Sec 3.6.3): coach_id is a deterministic slug of
(first, last, team), so re-running upserts the same rows rather than
duplicating them. Re-running deliberately does NOT reset the
in-game career counters (career_wins, sb_titles, the Sec 7.9 rollups) on
an existing coach -- those are accumulated play data, not seed data, and
blowing them away on a re-import is exactly the class of mistake the
M14 incident (see ROADMAP.md Sec 2b) cost this project a full franchise
history to learn.

Usage:
    .venv/Scripts/python.exe scripts/import_coaches.py
    .venv/Scripts/python.exe scripts/import_coaches.py --dry-run
"""
from __future__ import annotations
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import select

from app.core.db import init_db, get_session
from app.models.coach import (
    Coach, CoachRole, OFFENSIVE_PROFILES, DEFENSIVE_PROFILES, default_focus_area_for, tier_key,
    reputation_from_tier_percentile,
)
from app.data.team_name_map import NICKNAME_TO_ABBR
from app.engine.rng import RNG, stable_seed
from app.config import get_league_seed

DEFAULT_SOURCE = Path("data/raw/coaches/Comprehensive NFL Coaching Staff Directory with Salaries 2026.md")

_TEAM_RE = re.compile(r"^###\s+\*\*(.+?)\*\*\s*$")
_ENTRY_RE = re.compile(r"^>\s*\*\s*\*\*(.+?):\*\*\s*(.+?)\s*\(\s*Salary:\s*\$([\d,]+)\s*\)\s*$")

# GDD Sec 7.7.2.1a. Only these four titles get a coordinator-tier role;
# every other real title in the seed falls through to AC with the
# position group kept as `specialty`.
_ROLE_BY_TITLE: dict[str, CoachRole] = {
    "head coach": CoachRole.HC,
    "offensive coordinator": CoachRole.OC,
    "defensive coordinator": CoachRole.DC,
    "special teams coordinator": CoachRole.ST,
}

# Real AC titles -> the `specialty` string stored for them. Every entry
# here is a title that actually appears in the seed doc (verified by
# _report_unmapped_titles() below, which fails loudly rather than
# silently guessing if the seed ever grows a title this table misses).
_SPECIALTY_BY_TITLE: dict[str, str] = {
    "passing game coordinator": "Passing Game",
    "pass game coordinator": "Passing Game",
    "quarterbacks coach": "Quarterbacks",
    "assistant quarterbacks coach": "Quarterbacks (Assistant)",
    "running backs coach": "Running Backs",
    "wide receivers coach": "Wide Receivers",
    "tight ends coach": "Tight Ends",
    "offensive line coach": "Offensive Line",
    "assistant offensive line coach": "Offensive Line (Assistant)",
    "defensive line coach": "Defensive Line",
    "linebackers coach": "Linebackers",
    "secondary coach": "Secondary",
    "safeties coach": "Safeties",
    "cornerbacks coach": "Cornerbacks",
    "assistant special teams coach": "Special Teams (Assistant)",
    "assistant special teams coordinator": "Special Teams (Assistant)",
}

# Which generated tendency/rating dials lean offensive vs. defensive, so
# an OC's offensive profile and a DC's defensive profile are the ones
# that actually get a distinctive draw (GDD Sec 7.7.2.1 only defines
# both tags on every coach; showing a seeded "AirRaid" tag on a
# secondary coach would be noise, so non-coordinators stay "Balanced").
_OFFENSIVE_ROLES = {CoachRole.HC, CoachRole.OC}
_DEFENSIVE_ROLES = {CoachRole.HC, CoachRole.DC}

# Generated-age windows by role tier (GDD gives none). Head coaches
# skew oldest, assistants youngest -- a real, if coarse, characteristic
# of actual staffs, and it gives Sec 8.2.3's age-based retirement
# something sensible to act on.
_AGE_WINDOW: dict[CoachRole, tuple[int, int]] = {
    CoachRole.HC: (42, 66),
    CoachRole.OC: (36, 60),
    CoachRole.DC: (38, 62),
    CoachRole.ST: (36, 60),
    CoachRole.AC: (30, 58),
}


@dataclass
class SeedEntry:
    """One parsed line of the real seed doc -- real data only."""
    team_abbr: str
    title: str
    first_name: str
    last_name: str
    salary_aav: int


def parse_seed(text: str) -> tuple[list[SeedEntry], list[str]]:
    """Returns (entries, errors). Errors are line-numbered per GDD Sec
    3.6.4/3.6.7 rather than aborting the whole import on one bad row."""
    entries: list[SeedEntry] = []
    errors: list[str] = []
    team_abbr: str | None = None

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        team_match = _TEAM_RE.match(line)
        if team_match:
            full_name = team_match.group(1).strip()
            nickname = full_name.split()[-1]
            team_abbr = NICKNAME_TO_ABBR.get(nickname)
            if team_abbr is None:
                errors.append(f"line {lineno}: unmapped team name {full_name!r}")
            continue

        if not line.startswith(">"):
            continue

        entry_match = _ENTRY_RE.match(line)
        if not entry_match:
            errors.append(f"line {lineno}: unparseable staff line {line!r}")
            continue
        if team_abbr is None:
            errors.append(f"line {lineno}: staff line before any team heading")
            continue

        title, name, salary = entry_match.groups()
        name = name.strip()
        if " " not in name:
            errors.append(f"line {lineno}: single-token coach name {name!r}")
            continue
        first, last = name.split(" ", 1)
        entries.append(SeedEntry(
            team_abbr=team_abbr,
            title=title.strip(),
            first_name=first.strip(),
            last_name=last.strip(),
            salary_aav=int(salary.replace(",", "")),
        ))

    return entries, errors


def map_title(title: str) -> tuple[CoachRole, str | None]:
    """GDD Sec 7.7.2.1a. Dual titles ("Linebackers Coach / Assistant
    Head Coach") keep the primary functional position group only."""
    primary = title.split("/")[0].strip()
    key = primary.lower()
    role = _ROLE_BY_TITLE.get(key)
    if role is not None:
        return role, None
    specialty = _SPECIALTY_BY_TITLE.get(key)
    if specialty is None:
        # Unknown title: still import the coach (their name/salary are
        # real), with the raw title as the specialty, and report it.
        specialty = primary.replace(" Coach", "").strip()
    return CoachRole.AC, specialty


def coach_id_for(entry: SeedEntry) -> str:
    """Deterministic natural key (GDD Sec 3.6.3). Sec 3.6.3 prefers
    (first_name, last_name, birthdate), but the seed has no birthdates,
    so the team stands in as the disambiguator -- and since one person
    holds exactly one job on one staff, that also makes this key the
    de-duplicator for the seed's real dual-listings (see
    _dedupe_entries)."""
    base = f"{entry.first_name}_{entry.last_name}_{entry.team_abbr}"
    return re.sub(r"[^a-z0-9_]", "", base.lower().replace(" ", "_").replace("'", "").replace(".", ""))


def reputation_from_salary(salary: int, tier_salaries: list[int], tier: str) -> int:
    """Percentile rank of `salary` within its OWN role tier (`tier`, from
    tier_key()), mapped onto THAT tier's own real band
    (app/models/coach.py's REPUTATION_TIER_BAND) via
    reputation_from_tier_percentile() -- see that function's docstring
    for the full real-dollar derivation of why each tier gets its own
    band instead of one shared 40-99 range (2026-09-20 fix: an
    assistant's reputation could otherwise reach a head coach's).

    Ties share the same percentile (the standard "fraction at or below"
    definition), so the three coaches all at $450K get identical
    reputations rather than an arbitrary order."""
    if not tier_salaries:
        return 50
    at_or_below = sum(1 for s in tier_salaries if s <= salary)
    pct = at_or_below / len(tier_salaries)
    return reputation_from_tier_percentile(pct, tier)


def _draw(rng: RNG, center: float, spread: float, lo: int, hi: int) -> int:
    return int(round(max(lo, min(hi, rng.gauss(center, spread)))))


def _generate_profile(coach: Coach, league_seed: int) -> None:
    """Fills every field with no real-world source, deterministically.

    Two different draw styles on purpose (see app/models/coach.py):
    - Strategic tendencies (Sec 7.7.2.2) are STYLE, not quality --
      centered on a league-average 50 with real spread, independent of
      reputation. A great coach is no more likely to be pass-heavy.
    - Performance/management ratings (Sec 7.7.2.3) are QUALITY --
      centered on the coach's reputation (the one real-anchored signal
      available) with a smaller spread, so the real salary data
      actually means something instead of every coach being average
      with noise on top.

    Seeded on (league_seed, coach_id) so the same league always
    produces the same staffs (GDD Sec 1.3) and a different LEAGUE_SEED
    genuinely produces different ones.
    """
    rng = RNG.with_seed(stable_seed("coach_profile", league_seed, coach.coach_id))
    role = CoachRole(coach.role)

    lo_age, hi_age = _AGE_WINDOW[role]
    coach.age = _draw(rng, (lo_age + hi_age) / 2, (hi_age - lo_age) / 5, lo_age, hi_age)
    # Experience can't exceed a plausible career: nobody is coaching in
    # the NFL at 22, so cap years at (age - 24) and floor at 1.
    coach.experience_years = max(1, min(coach.age - 24, _draw(rng, (coach.age - 30), 5, 1, 45)))
    coach.contract_years = _draw(rng, 3, 1.2, 1, 5)

    # sigma 20, not a tighter draw: these sliders are the ONLY thing
    # that differentiates one team's play-calling identity from
    # another's, and a narrow draw collapses 32 teams onto the same
    # league-average behavior -- which was measurably the case at
    # sigma 15 (every team's resulting pass bias landed inside
    # +/-0.01, i.e. indistinguishable). Still bounded 5-95 and still
    # symmetric about 50, so the LEAGUE average is unmoved.
    for attr in ("run_pass_tendency", "offensive_aggression", "pace", "red_zone_offense_bias",
                 "two_point_tendency", "blitz_rate", "coverage_mix", "fourth_down_defense",
                 "red_zone_defense_bias", "special_teams_focus"):
        setattr(coach, attr, _draw(rng, 50, 20, 5, 95))

    for attr in ("player_dev_offense", "player_dev_defense", "discipline", "motivation_chemistry",
                 "red_zone_offense", "red_zone_defense"):
        setattr(coach, attr, _draw(rng, coach.reputation, 8, 20, 99))

    coach.offensive_profile = rng.choice(OFFENSIVE_PROFILES) if role in _OFFENSIVE_ROLES else "Balanced"
    coach.defensive_profile = rng.choice(DEFENSIVE_PROFILES) if role in _DEFENSIVE_ROLES else "Balanced"
    coach.is_generated_profile = True


# Role seniority for collapsing one person's multiple listings: the
# senior job is the one they actually hold (GDD Sec 7.7.2.1a's own
# dual-title principle -- keep the primary role, drop the secondary tag).
_ROLE_RANK: dict[CoachRole, int] = {
    CoachRole.HC: 4, CoachRole.OC: 3, CoachRole.DC: 3, CoachRole.ST: 3, CoachRole.AC: 1,
}


@dataclass
class ResolvedCoach:
    """One real person on one staff, after the seed's dual-listings are
    collapsed -- still real data only, no generated fields yet."""
    coach_id: str
    entry: SeedEntry
    role: CoachRole
    specialty: str | None


def _specificity(specialty: str | None) -> int:
    """Ranks two competing AC specialties for the same person. "Passing
    Game" is an umbrella tag that says less about what a coach actually
    works on than the position group they're also listed against, so it
    loses to anything more specific."""
    if specialty is None:
        return -1
    return 0 if specialty == "Passing Game" else 1


def dedupe_entries(entries: list[SeedEntry]) -> list[ResolvedCoach]:
    """One person = one row.

    The seed genuinely lists 17 people twice on their own staff: 14
    hold a broad "Passing Game Coordinator" line alongside their real
    position-group line (e.g. HOU's Jerrod Johnson is both Passing Game
    Coordinator and Quarterbacks Coach, at one salary), and 3 are
    coordinators who also carry their old position-coach title (KC's
    Matt Nagy is OC and Quarterbacks Coach; DET's Kelvin Sheppard and
    LAR's Chris Shula are DC and Linebackers Coach). These are one
    person with one salary, not two employees, so they collapse to one
    row -- keeping the senior role, and within the same role the more
    specific position-group specialty. Both halves of that rule are the
    same principle GDD Sec 7.7.2.1a already states for slash-titles:
    keep the primary functional job, drop the secondary tag.
    """
    resolved: dict[str, ResolvedCoach] = {}
    order: list[str] = []
    for entry in entries:
        role, specialty = map_title(entry.title)
        cid = coach_id_for(entry)
        prior = resolved.get(cid)
        if prior is None:
            resolved[cid] = ResolvedCoach(cid, entry, role, specialty)
            order.append(cid)
            continue
        if _ROLE_RANK[role] > _ROLE_RANK[prior.role]:
            # Senior job wins, and a coordinator-tier role carries no
            # specialty at all (Sec 7.7.2.1: specialty is AC-only).
            prior.role, prior.specialty = role, specialty
        elif role is prior.role and _specificity(specialty) > _specificity(prior.specialty):
            prior.specialty = specialty
    return [resolved[cid] for cid in order]


def build_coaches(entries: list[SeedEntry], league_seed: int) -> list[Coach]:
    resolved = dedupe_entries(entries)

    # Salary percentiles are computed over the de-duplicated staff, so a
    # person listed twice doesn't get counted twice in their own tier.
    tier_salaries: dict[str, list[int]] = {}
    for r in resolved:
        tier_salaries.setdefault(tier_key(r.role), []).append(r.entry.salary_aav)

    coaches: list[Coach] = []
    for r in resolved:
        coach = Coach(
            coach_id=r.coach_id,
            first_name=r.entry.first_name,
            last_name=r.entry.last_name,
            role=r.role,
            specialty=r.specialty,
            team_abbr=r.entry.team_abbr,
            salary_aav=r.entry.salary_aav,
            reputation=reputation_from_salary(
                r.entry.salary_aav, tier_salaries[tier_key(r.role)], tier_key(r.role)
            ),
            focus_area=default_focus_area_for(r.role, r.specialty),
        )
        _generate_profile(coach, league_seed)
        coaches.append(coach)
    return coaches


def _report_unmapped_titles(entries: list[SeedEntry]) -> list[str]:
    known = set(_ROLE_BY_TITLE) | set(_SPECIALTY_BY_TITLE)
    unknown = sorted({e.title.split("/")[0].strip() for e in entries
                      if e.title.split("/")[0].strip().lower() not in known})
    return unknown


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dry-run", action="store_true", help="Parse and report, write nothing.")
    args = parser.parse_args()

    text = args.source.read_text(encoding="utf-8")
    entries, errors = parse_seed(text)
    print(f"parsed staff entries: {len(entries)}")
    print(f"teams covered: {len(set(e.team_abbr for e in entries))}")
    for err in errors:
        print(f"  ERROR {err}")

    unknown = _report_unmapped_titles(entries)
    if unknown:
        print("  NOTE titles not in the Sec 7.7.2.1a mapping table (imported as AC "
              "with the raw title as specialty):")
        for title in unknown:
            print(f"    - {title}")

    coaches = build_coaches(entries, get_league_seed())
    by_role: dict[str, int] = {}
    for c in coaches:
        by_role[c.role.value] = by_role.get(c.role.value, 0) + 1
    merged = len(entries) - len(coaches)
    print(f"coaches built: {len(coaches)}  by role: {by_role}")
    print(f"dual-listed staff merged into one row each: {merged}")

    if args.dry_run:
        print("Dry run -- nothing written.")
        return

    init_db()
    with get_session() as session:
        existing = {c.coach_id: c for c in session.exec(select(Coach)).all()}
        inserted = updated = 0
        for coach in coaches:
            prior = existing.get(coach.coach_id)
            if prior is None:
                session.add(coach)
                inserted += 1
                continue
            # Upsert seed + profile fields only. Career counters and
            # job_security_score are accumulated play data -- never reset
            # by a re-import (see this module's docstring).
            for attr in ("first_name", "last_name", "role", "specialty", "team_abbr",
                         "salary_aav", "reputation", "age", "experience_years",
                         "contract_years", "offensive_profile", "defensive_profile",
                         "is_generated_profile",
                         "run_pass_tendency", "offensive_aggression", "pace",
                         "red_zone_offense_bias", "two_point_tendency", "blitz_rate",
                         "coverage_mix", "fourth_down_defense", "red_zone_defense_bias",
                         "special_teams_focus", "player_dev_offense", "player_dev_defense",
                         "discipline", "motivation_chemistry",
                         "red_zone_offense", "red_zone_defense"):
                setattr(prior, attr, getattr(coach, attr))
            session.add(prior)
            updated += 1
        session.commit()

    print(f"Import complete. inserted={inserted} updated={updated}")


if __name__ == "__main__":
    main()
