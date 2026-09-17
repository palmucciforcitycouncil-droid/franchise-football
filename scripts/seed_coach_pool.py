"""
One-time seed for R3d's Tier 3 coach candidate pool (Sec 8) --
real named college HC/OC/DC and former-NFL HC/OC/DC candidates, from
data/raw/coaches/Top_100_Football_Coaching_Candidates.md (Brian's real
2026 candidate directory -- the file the R3d spec itself named,
Top_100_Football_Coaching_Candidates.xlsx, doesn't exist in this repo;
this .md file is the real substitute Brian supplied instead, same
"provide the real source, this script imports it" shape as
scripts/import_coaches.py's own seed file).

REAL vs. GENERATED, same disclosure discipline as app/models/coach.py's
own module docstring: name, program/last-franchise, and the "Key
Distinction" background blurb are real, copied verbatim from the seed
file below (_CANDIDATES). Every rating (reputation, the six performance
ratings, the ten strategic-tendency sliders, age, experience_years) has
no real source for these candidates and is GENERATED the same
deterministic-seeded-RNG way scripts/import_coaches.py already
generates them for the real 433 current staff -- `is_generated_profile`
is True here for the identical reason it's True there (a real person,
generated numbers).

Rating tiers (Sec 8's own "Rating Assignment" table): each candidate's
`reputation` is drawn inside their tier's documented band, then nudged
by a real, disclosed keyword scan of their OWN background text (Sec
4.2's "Background bonus: real credentials... boost ratings; vague
backgrounds don't fabricate numbers") -- e.g. Bill Belichick's "6x
Super Bowl Champion; widely considered GOAT coach" earns the maximum
credential bonus, landing him at the top of the Former NFL HC band
(55-85), while a background with no such signal stays wherever the
plain seeded draw lands within the band. This is a real, reproducible,
disclosed heuristic keyed off real text -- not 100 hand-tuned numbers.

Idempotent: coach_id is a deterministic slug of the real name, so
re-running this script updates the same 100 rows rather than
duplicating them (same contract as import_coaches.py's own re-import).
Never touches team_abbr on an existing row that already has one
(a seeded pool candidate who gets hired in-game should stay hired,
not get silently reset back to free agency by a re-run of this script).
"""
from __future__ import annotations
import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import get_league_seed
from app.core.db import get_session, init_db
from app.engine.rng import RNG, stable_seed
from app.models.coach import (
    Coach, CoachRole, OFFENSIVE_PROFILES, DEFENSIVE_PROFILES,
    POOL_TIER_COLLEGE, POOL_TIER_FORMER_NFL, default_focus_area_for,
)
from sqlmodel import select

DEFAULT_SOURCE = Path("data/raw/coaches/Top_100_Football_Coaching_Candidates.md")

# Sec 8's Rating Assignment bands (min, max), by (pool_tier, role).
_TIER_BANDS: dict[tuple[str, CoachRole], tuple[int, int]] = {
    (POOL_TIER_COLLEGE, CoachRole.HC): (50, 80),
    (POOL_TIER_COLLEGE, CoachRole.OC): (45, 75),
    (POOL_TIER_COLLEGE, CoachRole.DC): (45, 75),
    (POOL_TIER_FORMER_NFL, CoachRole.HC): (55, 85),
    (POOL_TIER_FORMER_NFL, CoachRole.OC): (50, 80),
    (POOL_TIER_FORMER_NFL, CoachRole.DC): (50, 80),
}

_AGE_WINDOW: dict[str, tuple[int, int]] = {
    POOL_TIER_COLLEGE: (38, 66),
    POOL_TIER_FORMER_NFL: (46, 75),
}

# Real, disclosed keyword-credential scan (Sec 4.2's "Background bonus").
# Each hit adds its points, summed and capped at _MAX_BONUS.
_CREDENTIAL_KEYWORDS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"goat|6x super bowl|super bowl champion", re.I), 14),
    (re.compile(r"national champion", re.I), 10),
    (re.compile(r"back-to-back|2x|multi-division champion|multi-cfp", re.I), 5),
    (re.compile(r"coach of the year", re.I), 7),
    (re.compile(r"heisman", re.I), 5),
    (re.compile(r"award winner|broyles award", re.I), 5),
    (re.compile(r"legendary|elite|premier|master|architect|pioneer|mastermind", re.I), 3),
    (re.compile(r"championship game|division champion", re.I), 3),
]
_MAX_BONUS = 18


def _credential_bonus(background: str) -> int:
    total = 0
    for pattern, points in _CREDENTIAL_KEYWORDS:
        if pattern.search(background):
            total += points
    return min(_MAX_BONUS, total)


@dataclass
class Candidate:
    name: str
    background: str
    role: CoachRole
    pool_tier: str


# The real 100 candidates, transcribed from
# data/raw/coaches/Top_100_Football_Coaching_Candidates.md. Program/
# franchise columns are folded into the background string (not stored
# separately -- Coach has no "program" field, and the distinction
# doesn't matter once this person is being evaluated for an NFL job).
_CANDIDATES: list[Candidate] = [
    # College Football Head Coaches (35) -- role=HC, tier=college
    Candidate("Kirby Smart", "Georgia HC -- 2x National Champion; premier defensive strategist", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Ryan Day", "Ohio State HC -- elite offensive play-caller; multi-CFP appearance", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Dan Lanning", "Oregon HC -- high-energy recruiter; premier defensive scheme background", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Steve Sarkisian", "Texas HC -- master offensive designer; QB development specialist", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Curt Cignetti", "Indiana HC -- rapid turnaround architect; proven winner across levels", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Kalen DeBoer", "Alabama HC -- offensive genius; national finalist at Washington", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Marcus Freeman", "Notre Dame HC -- elite defensive recruiter and program builder", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Lane Kiffin", "Ole Miss HC -- modern tempo offensive innovator & portal master", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Mike Elko", "Texas A&M HC -- defensive mastermind; rapid turnarounds at Duke/A&M", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Mario Cristobal", "Miami (FL) HC -- elite recruiter and offensive line specialist", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Kyle Whittingham", "Utah HC -- decades of consistency, toughness, and physical defense", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Lincoln Riley", "USC HC -- Heisman QB developer; high-powered passing attack", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Josh Heupel", "Tennessee HC -- ultra-fast spread offense specialist", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("James Franklin", "Penn State HC -- consistently top-10 recruiter and big-program leader", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Jon Sumrall", "Tulane HC -- back-to-back championship builder at Troy/Tulane", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Mike Norvell", "Florida State HC -- ACC Champion; roster management & portal expert", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Brent Venables", "Oklahoma HC -- legendary defensive coordinator; elite front-seven schemer", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Shane Beamer", "South Carolina HC -- culture architect & special teams mastermind", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Eli Drinkwitz", "Missouri HC -- Cotton Bowl champion; innovative offensive mind", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Matt Rhule", "Nebraska HC -- proven program rebuild pioneer (Temple, Baylor)", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Jedd Fisch", "Washington HC -- pro-style offensive background; rapid program turnaround", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Hugh Freeze", "Auburn HC -- dynamic SEC offensive caller & top-tier recruiter", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Deion Sanders", "Colorado HC -- transformational program figure & media catalyst", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Lance Leipold", "Kansas HC -- multi-division champion; fundamental offense builder", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Chris Klieman", "Kansas State HC -- 4x FCS Champion; Big 12 title-winning head coach", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Dave Doeren", "NC State HC -- maximum consistency and hard-nosed defense specialist", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Jeff Brohm", "Louisville HC -- aggressive passing game innovator & upset specialist", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Mack Brown", "North Carolina HC -- National Champion; CEO-style legendary leader", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Joey McGuire", "Texas Tech HC -- high school Texas recruiting legend & culture builder", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Jonathan Smith", "Michigan State HC -- pro-style QB developer; former Oregon State HC", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Luke Fickell", "Wisconsin HC -- led Cincinnati to CFP; tough, physical program identity", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Rhett Lashlee", "SMU HC -- high-tempo offensive mind; AAC Champion transitioner", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Jamey Chadwell", "Liberty HC -- unique spread-option offensive architect", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("Brent Key", "Georgia Tech HC -- physical, trench-focused culture builder", CoachRole.HC, POOL_TIER_COLLEGE),
    Candidate("G.J. Kinne", "Texas State HC -- rising star spread offensive mastermind", CoachRole.HC, POOL_TIER_COLLEGE),

    # College Football Offensive Coordinators (20) -- role=OC, tier=college
    Candidate("Andy Kotelnicki", "Penn State OC -- creative motion & heavy-personnel play-action creator", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Will Stein", "Oregon OC -- dynamic multi-tier spread passing attack", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Mike Denbrock", "Notre Dame OC -- architect of Jayden Daniels' Heisman season at LSU", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Garrett Riley", "Clemson OC -- Air Raid variation specialist; Broyles Award winner", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Shannon Dawson", "Miami (FL) OC -- aggressive downfield passing system designer", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Charlie Weis Jr.", "Ole Miss OC -- high-speed, efficient play-calling partner with Kiffin", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Buster Faulkner", "Georgia Tech OC -- balanced, explosive run-pass option coordinator", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Kendal Briles", "TCU OC -- ultra-tempo, power spread offensive designer", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Collin Klein", "Texas A&M OC -- QB-run heavy, physical spread strategist", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Kirby Moore", "Missouri OC -- innovative pro-spread play-caller", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Ben Arbuckle", "Washington State OC -- young, aggressive Air-Raid system architect", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Brennan Marion", "UNLV OC -- creator of the famous 'Go-Go' offense system", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Mack Leftwich", "Texas State OC -- ultra-fast tempo & explosive play generator", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Chip Kelly", "Ohio State OC -- pioneer of modern uptempo & elite run scheme designer", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Seth Littrell", "Oklahoma OC -- former North Texas HC; veteran offensive play-caller", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Phil Longo", "Wisconsin OC -- Air Raid philosophy adapter to power personnel", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Jason Beck", "Syracuse OC -- QB whisperer and versatile offensive schemer", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Arthur Smith", "Pittsburgh OC (College/NFL past) -- heavy zone-run & play-action specialist", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Sean Lewis", "San Diego State HC/OC -- 'Fastball' hyper-tempo offensive pioneer", CoachRole.OC, POOL_TIER_COLLEGE),
    Candidate("Nick Sheridan", "Alabama OC -- co-OC alongside DeBoer passing game system", CoachRole.OC, POOL_TIER_COLLEGE),

    # College Football Defensive Coordinators (20) -- role=DC, tier=college
    Candidate("Phil Parker", "Iowa DC -- Broyles Award winner; perennial nation-leading secondary/defense", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Glenn Schumann", "Georgia DC -- co-architect of college football's elite defense; LB expert", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Kane Wommack", "Alabama DC -- creator of the 4-2-5 Swarm defense; former South Alabama HC", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Bryant Haines", "Indiana DC -- aggressive front-7 pressure specialist with Cignetti", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Jim Knowles", "Ohio State DC -- master of the 4-2-5 safety-driven pressure scheme", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("D'Anton Lynn", "USC DC -- transformed UCLA defense; NFL pedigree secondary coach", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Blake Baker", "LSU DC -- high-blitz frequency & turnover creation expert", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Tony White", "Nebraska DC -- master of the unique 3-3-3 stack defense system", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Pete Golding", "Ole Miss DC -- top SEC defensive recruiter and pressure coordinator", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Tosh Lupoi", "Oregon DC -- elite defensive line specialist and recruiter", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Will Muschamp", "Georgia Co-DC/Analyst -- former Florida/South Carolina HC; legendary SEC DC", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Brad White", "Kentucky DC -- consistently builds disciplined, NFL-caliber front sevens", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Shiel Wood", "Houston DC -- turnaround specialist with multiple turnover-heavy defenses", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Joe Rossi", "Michigan State DC -- bend-don't-break, highly disciplined Big Ten strategist", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Ron English", "Louisville DC -- aggressive secondary coverage & blitz schemer", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Brian Ward", "Arizona State DC -- tackling efficiency and disruptive tackle-for-loss design", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Corey Hetherman", "Minnesota DC -- physical, gap-sound defensive front specialist", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Jay Hill", "BYU DC -- former Weber State HC; secondary and special teams expert", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Zach Arnett", "Ole Miss/Miss State former DC -- 3-3-5 defense specialist; former Miss State HC", CoachRole.DC, POOL_TIER_COLLEGE),
    Candidate("Tyson Veidt", "Cincinnati DC -- linebacker development and disguised coverage expert", CoachRole.DC, POOL_TIER_COLLEGE),

    # Former NFL Head Coaches (15) -- role=HC, tier=former_nfl
    Candidate("Bill Belichick", "Former New England Patriots HC -- 6x Super Bowl Champion; widely considered GOAT coach", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Pete Carroll", "Former Seattle Seahawks HC -- Super Bowl Champion & National Champion (USC)", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Mike Vrabel", "Former Tennessee Titans HC -- 2021 NFL Coach of the Year; physical culture leader", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Jon Gruden", "Former Las Vegas Raiders HC -- Super Bowl XXXVII Champion; West Coast offense expert", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Ron Rivera", "Former Washington Commanders HC -- 2x NFL Coach of the Year; led Panthers to Super Bowl 50", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Frank Reich", "Former Carolina Panthers HC -- veteran offensive mind & QB designer (Eagles SB LII)", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Mike Zimmer", "Former Minnesota Vikings HC -- A-gap pressure defensive innovator (currently Dallas DC)", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Chuck Pagano", "Former Indianapolis Colts HC -- defensive secondary background; 33-31 NFL HC record", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Marvin Lewis", "Former Cincinnati Bengals HC -- 16 seasons as Bengals HC; 2000 Ravens DC legend", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Jack Del Rio", "Former Oakland Raiders HC -- 12 years NFL HC experience (Jaguars, Raiders)", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Doug Marrone", "Former Jacksonville Jaguars HC -- led Jaguars to 2017 AFC Championship Game; OL expert", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Jim Caldwell", "Former Detroit Lions HC -- led Colts to Super Bowl XLIV; two winning stints as HC", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Lovie Smith", "Former Houston Texans HC -- led Bears to Super Bowl XLI; Tampa 2 defense master", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Rex Ryan", "Former Buffalo Bills HC -- back-to-back AFC Championship games with NY Jets", CoachRole.HC, POOL_TIER_FORMER_NFL),
    Candidate("Dirk Koetter", "Former Tampa Bay Buccaneers HC -- veteran NFL/College offensive coordinator & HC", CoachRole.HC, POOL_TIER_FORMER_NFL),

    # Former NFL Coordinators (10) -- role=OC/DC, tier=former_nfl
    Candidate("Greg Roman", "Former Baltimore Ravens OC -- heavy run-game, QB-run & gap-scheme innovator", CoachRole.OC, POOL_TIER_FORMER_NFL),
    Candidate("Byron Leftwich", "Former Tampa Bay Buccaneers OC -- Super Bowl LV winning OC with Tom Brady", CoachRole.OC, POOL_TIER_FORMER_NFL),
    Candidate("Todd Haley", "Former Pittsburgh Steelers OC -- high-volume passing game designer; former Chiefs HC", CoachRole.OC, POOL_TIER_FORMER_NFL),
    Candidate("Pep Hamilton", "Former Houston Texans OC -- West coast passing game & QB development specialist", CoachRole.OC, POOL_TIER_FORMER_NFL),
    Candidate("Jim Bob Cooter", "Former Detroit Lions OC -- up-tempo, quick-release passing game coordinator", CoachRole.OC, POOL_TIER_FORMER_NFL),
    Candidate("Wade Phillips", "Former LA Rams/UFL DC -- legendary 3-4 defense master; Super Bowl 50 Champion", CoachRole.DC, POOL_TIER_FORMER_NFL),
    Candidate("Gregg Williams", "Former NY Jets/XFL DC -- ultra-aggressive blitz & high-turnover defense scheme", CoachRole.DC, POOL_TIER_FORMER_NFL),
    Candidate("Paul Guenther", "Former Las Vegas Raiders DC -- double-A-gap pressure scheme specialist", CoachRole.DC, POOL_TIER_FORMER_NFL),
    Candidate("Ray Horton", "Former Cleveland Browns DC -- 3-4 zone-blitz secondary specialist", CoachRole.DC, POOL_TIER_FORMER_NFL),
    Candidate("Mike Nolan", "Former Dallas Cowboys/USFL DC -- veteran 3-4 defense architect & former 49ers HC", CoachRole.DC, POOL_TIER_FORMER_NFL),
]


def _slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_").replace("'", "").replace(".", ""))
    return f"pool_{base}"


def _draw(rng: RNG, center: float, spread: float, lo: int, hi: int) -> int:
    return int(round(max(lo, min(hi, rng.gauss(center, spread)))))


def build_candidate_coach(candidate: Candidate, league_seed: int) -> Coach:
    coach_id = _slug(candidate.name)
    first, *rest = candidate.name.split(" ")
    last = " ".join(rest) if rest else first

    lo, hi = _TIER_BANDS[(candidate.pool_tier, candidate.role)]
    rng = RNG.with_seed(stable_seed("coach_pool_profile", league_seed, coach_id))
    base_reputation = _draw(rng, (lo + hi) / 2, (hi - lo) / 4, lo, hi)
    reputation = min(hi, base_reputation + _credential_bonus(candidate.background))

    age_lo, age_hi = _AGE_WINDOW[candidate.pool_tier]
    age = _draw(rng, (age_lo + age_hi) / 2, (age_hi - age_lo) / 5, age_lo, age_hi)
    experience_years = max(1, min(age - 24, _draw(rng, age - 32, 6, 1, 45)))

    coach = Coach(
        coach_id=coach_id, first_name=first, last_name=last, role=candidate.role,
        specialty=None, team_abbr=None, salary_aav=0, age=age, experience_years=experience_years,
        contract_years=0, reputation=reputation, is_generated_profile=True,
        pool_tier=candidate.pool_tier, background=candidate.background,
        focus_area=default_focus_area_for(candidate.role, None),
    )
    for attr in ("run_pass_tendency", "offensive_aggression", "pace", "red_zone_offense_bias",
                 "two_point_tendency", "blitz_rate", "coverage_mix", "fourth_down_defense",
                 "red_zone_defense_bias", "special_teams_focus"):
        setattr(coach, attr, _draw(rng, 50, 20, 5, 95))
    for attr in ("discipline", "motivation_chemistry", "red_zone_offense", "red_zone_defense"):
        setattr(coach, attr, _draw(rng, reputation, 8, 20, 99))
    # R16: a real OC/DC candidate leans toward their own side's granular
    # ratings via a PENALTY on the off-side ones (not a bonus on-side --
    # see scripts/import_coaches.py's _rating_penalty_for() docstring for
    # why a bonus silently washes out at the 99 ceiling for high-
    # reputation candidates). This pool has no AC candidates, so only the
    # coordinator off-side penalty applies here.
    offense_ratings = ("qb_coaching", "rb_coaching", "wr_coaching", "ol_coaching")
    off_side_penalty = 8.0
    for attr in (*offense_ratings, "dl_coaching", "lb_coaching", "secondary_coaching", "st_coaching"):
        off_side = (candidate.role is CoachRole.OC and attr not in offense_ratings) \
            or (candidate.role is CoachRole.DC and (attr in offense_ratings or attr == "st_coaching"))
        setattr(coach, attr, _draw(rng, reputation - (off_side_penalty if off_side else 0.0), 8, 20, 99))
    coach.offensive_profile = rng.choice(OFFENSIVE_PROFILES) if candidate.role in (CoachRole.HC, CoachRole.OC) else "Balanced"
    coach.defensive_profile = rng.choice(DEFENSIVE_PROFILES) if candidate.role in (CoachRole.HC, CoachRole.DC) else "Balanced"
    return coach


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Build and report, write nothing.")
    args = parser.parse_args()

    if not DEFAULT_SOURCE.exists():
        raise SystemExit(f"Missing seed file: {DEFAULT_SOURCE}")

    league_seed = get_league_seed()
    coaches = [build_candidate_coach(c, league_seed) for c in _CANDIDATES]
    by_role: dict[str, int] = {}
    for c in coaches:
        by_role[c.role.value] = by_role.get(c.role.value, 0) + 1
    print(f"candidates built: {len(coaches)}  by role: {by_role}")
    assert len({c.coach_id for c in coaches}) == len(coaches), "duplicate candidate slug -- check for a repeated name"

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
            if prior.team_abbr is not None:
                # Already hired in-game by a prior run of the sim --
                # never silently reset them back to free agency.
                continue
            for attr in ("first_name", "last_name", "role", "reputation", "age", "experience_years",
                         "contract_years", "is_generated_profile", "pool_tier", "background",
                         "offensive_profile", "defensive_profile",
                         "run_pass_tendency", "offensive_aggression", "pace", "red_zone_offense_bias",
                         "two_point_tendency", "blitz_rate", "coverage_mix", "fourth_down_defense",
                         "red_zone_defense_bias", "special_teams_focus", "player_dev_offense",
                         "player_dev_defense", "discipline", "motivation_chemistry",
                         "red_zone_offense", "red_zone_defense"):
                setattr(prior, attr, getattr(coach, attr))
            session.add(prior)
            updated += 1
        session.commit()

    print(f"Seed complete. inserted={inserted} updated={updated}")


if __name__ == "__main__":
    main()
