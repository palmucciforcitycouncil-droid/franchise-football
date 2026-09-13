"""
Coach entity (GDD Part 1 Sec 7.7.2; ROADMAP.md R3 "Coaching Staff").

REAL vs. GENERATED -- read this before trusting any field here.

The real seed (`data/raw/coaches/Comprehensive NFL Coaching Staff
Directory with Salaries 2026.md`, GDD Sec 3.6.1) gives exactly three
things per coach: **name, exact title, and salary**. That's where real
data ends. Every other field the GDD's coach spec calls for -- the
0-100 strategic-tendency sliders (Sec 7.7.2.2), the 0-99 performance/
management ratings (Sec 7.7.2.3), scheme-profile tags, age, and
experience -- has no real-world source to import, so it is *generated*
by scripts/import_coaches.py from this project's own deterministic
seeded-RNG (`app.engine.rng.stable_seed`, GDD Sec 1.3's Determinism &
Seeding Policy), never hand-authored to "look real."

`is_generated_profile` below is a real, queryable flag carrying that
distinction into the data model itself rather than leaving it in a
comment, and the Staff page/Coach Card surface it on-screen -- the same
disclosed-gap discipline M8 (real salary, disclosed-missing contract
term) and M13 (real stats only, no fabricated columns) already set.

The one generated field with a real anchor is `reputation`: it is the
coach's `salary_aav` percentile **within their own role tier** (HC pool
vs. OC/DC/ST pool vs. AC pool -- comparing an assistant's salary against
a head coach's would be meaningless), mapped onto 40-99. Real
compensation genuinely does encode relative standing (Andy Reid at $20M
vs. a $450K assistant), so this is the single seeded attribute that
traces back to something real, and it anchors the performance ratings
rather than those being drawn blind.

Career accounting (the `*_afc_championships`/`*_nfc_championships`/
`*_super_bowl_wins` counters and CoachSeasonStats) implements GDD Sec
7.9 -- credit by the role held at kickoff of the championship game. All
of those start at zero at league seed: this project has no real source
for these coaches' actual NFL career histories, and inventing one would
be exactly the fabrication the rest of this module avoids.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class CoachRole(str, Enum):
    """GDD Sec 7.7.2.1. ST (Special Teams Coordinator) was split out of
    the original AC catch-all on 2026-09-11 -- the real seed lists a
    distinct Special Teams Coordinator on every one of the 32 teams, at
    the same organizational tier as OC/DC. See Sec 7.7.2.1a for how
    every other real title collapses into AC + a `specialty` tag."""
    HC = "HC"
    OC = "OC"
    DC = "DC"
    ST = "ST"
    AC = "AC"


ROLE_TITLES: dict[CoachRole, str] = {
    CoachRole.HC: "Head Coach",
    CoachRole.OC: "Offensive Coordinator",
    CoachRole.DC: "Defensive Coordinator",
    CoachRole.ST: "Special Teams Coordinator",
    CoachRole.AC: "Assistant Coach",
}

# GDD Sec 7.7.2.1's two scheme-tag enums. Stored as plain strings on the
# table (SQLModel/SQLite has no native enum) but constrained to these
# values by the importer.
OFFENSIVE_PROFILES = ["WestCoast", "AirRaid", "Vertical", "GroundNPound", "RPO", "Balanced"]
DEFENSIVE_PROFILES = ["Man", "Zone", "BlitzHeavy", "TwoHigh", "StopRun", "Balanced"]

CONFERENCE_TITLE_NONE = "NONE"
SUPER_BOWL_NONE = "NONE"
SUPER_BOWL_LOSS = "LOSS"
SUPER_BOWL_WIN = "WIN"

def tier_key(role: CoachRole) -> str:
    """Which organizational tier `role` belongs to for anything that
    compares coaches' pay/quality against their real peers -- comparing
    an assistant's $450K to a head coach's $20M would be meaningless.
    OC/DC/ST share one tier (the same organizational level; GDD Sec
    7.9.5's HOF weighting already treats ST as OC/DC's peer). Originally
    scripts/import_coaches.py's own private `_tier_key` (reputation
    percentile at import time); promoted here so app/engine/coach_
    contracts.py's coach_market_value() can share the identical grouping
    at negotiation time instead of a second, potentially-drifting copy."""
    if role is CoachRole.HC:
        return "HC"
    if role in (CoachRole.OC, CoachRole.DC, CoachRole.ST):
        return "COORD"
    return "AC"


# R3d (Coach Hiring/Firing/Promotion Market) appointment designations --
# Sec 5 of docs/R3d_COACHING_SYSTEM_SPECIFICATION.md.
APPOINTMENT_PERMANENT = "Permanent"
APPOINTMENT_INTERIM = "Interim"
APPOINTMENT_ACTING = "Acting"
APPOINTMENT_TEMPORARY_PROMOTION = "TemporaryPromotion"
APPOINTMENT_TYPES = [
    APPOINTMENT_PERMANENT, APPOINTMENT_INTERIM, APPOINTMENT_ACTING, APPOINTMENT_TEMPORARY_PROMOTION,
]

# R13 (Coach Focus Areas, docs/R13_COACH_FOCUS_AREA_SPECIFICATION.md) --
# turns the Figma source's per-coach "Focus Area" dropdown (a real, disclosed
# no-op through R3c: "nothing in the engine reads a focus area") into a real,
# consumed choice. `app/engine/coaching.py`'s `build_staff_effect()` groups a
# staff's ratings by each coach's OWN focus_area instead of hardcoding by
# role -- Focus Area REALLOCATES an existing coach's influence, it never adds
# power (keeps the module's own LeagueBaseline calibration guarantee intact).
# `2 Min Offense` (a real Figma source option) is deliberately NOT included --
# this engine has no clock/2-minute-drill model anywhere, same reason
# `clock_management`/`challenge_sense` were deleted from this model outright.
FOCUS_OF_GAMEPLAN = "OF Gameplan"
FOCUS_DF_GAMEPLAN = "DF Gameplan"
# A coach here contributes to BOTH OF Gameplan and DF Gameplan simultaneously,
# at a reduced weight on each (app/engine/coaching.py's BALANCE_SPLIT_FACTOR)
# -- real influence on both sides, smaller than fully focusing on just one.
# The Head Coach's own default (see default_focus_area_for() below).
FOCUS_BALANCED_GAMEPLAN = "Balanced Gameplan"
FOCUS_DEVELOPMENT = "Development"
FOCUS_SPECIAL_TEAMS = "Special Teams Work"
FOCUS_TRAINING = "Training"
FOCUS_SCOUTING = "Scouting"
FOCUS_AREAS = [
    FOCUS_OF_GAMEPLAN, FOCUS_DF_GAMEPLAN, FOCUS_BALANCED_GAMEPLAN, FOCUS_DEVELOPMENT,
    FOCUS_SPECIAL_TEAMS, FOCUS_TRAINING, FOCUS_SCOUTING,
]


def default_focus_area_for(role: CoachRole, specialty: Optional[str]) -> str:
    """The sensible starting focus_area for a freshly-imported or freshly-
    migrated coach (docs/R13_COACH_FOCUS_AREA_SPECIFICATION.md Sec 4).
    Shared by scripts/import_coaches.py (fresh imports/template rebuilds) and
    scripts/migrate_add_r13_focus_area.py (the existing live DB) so both
    paths produce identical defaults -- one heuristic, not two that could
    drift apart.

    HC defaults to Balanced Gameplan (not a single side) -- an earlier draft
    of this spec defaulted HC to one side, which silently zeroed their
    contribution to the OTHER side; Balanced Gameplan is the real design fix,
    not a compatibility patch. AC defaults key off the real seed's own
    specialty text where it plausibly says something ("special teams",
    "strength"/"conditioning"); every other AC (the real position coaches --
    QB/WR/OL/DL/LB/DB/etc.) defaults to Development, matching how every
    assistant was already pooled into player development before this system
    existed."""
    if role is CoachRole.OC:
        return FOCUS_OF_GAMEPLAN
    if role is CoachRole.DC:
        return FOCUS_DF_GAMEPLAN
    if role is CoachRole.ST:
        return FOCUS_SPECIAL_TEAMS
    if role is CoachRole.HC:
        return FOCUS_BALANCED_GAMEPLAN
    text = (specialty or "").lower()
    if "special team" in text:
        return FOCUS_SPECIAL_TEAMS
    if "strength" in text or "conditioning" in text:
        return FOCUS_TRAINING
    return FOCUS_DEVELOPMENT


# R3d's Tier 3 candidate pool (app/services/coach_pool.py) -- real named
# college/former-NFL candidates seeded from data/raw/coaches/
# Top_100_Football_Coaching_Candidates.md, who never held one of the
# real 433 seeded staff jobs. `None` means "not a pool-seeded
# candidate" (every real current/former NFL coach already in this
# table, including one who gets fired in-game and becomes a free
# agent, carries no tier tag -- only scripts/seed_coach_pool.py's
# candidates do).
POOL_TIER_COLLEGE = "college"
POOL_TIER_FORMER_NFL = "former_nfl_candidate"


class Coach(SQLModel, table=True):
    coach_id: str = Field(primary_key=True)

    # --- Identity & contract (GDD Sec 7.7.2.1) ---
    first_name: str
    last_name: str
    role: CoachRole
    # AC-only free-text position-group tag ("Quarterbacks", "Offensive
    # Line", "Special Teams (Assistant)"). Null for HC/OC/DC/ST, whose
    # role already says what they do -- GDD Sec 7.7.2.1a.
    specialty: Optional[str] = None
    team_abbr: Optional[str] = Field(default=None, index=True)  # None = free agent
    # Real, from the seed doc. The only imported number that isn't generated.
    salary_aav: int = 0

    # Generated (no real source) -- see module docstring.
    age: int = 45
    experience_years: int = 10
    # Same disclosed-synthetic treatment Player.contract_years_remaining
    # already gets: a real negotiated term arrives with R4a (Contracts).
    contract_years: int = 2
    reputation: int = 50  # salary percentile within role tier -- the one real-anchored generated field
    offensive_profile: str = "Balanced"
    defensive_profile: str = "Balanced"
    is_generated_profile: bool = True

    # --- Strategic tendencies, 0-100 (GDD Sec 7.7.2.2) ---
    # Style, not quality: deliberately NOT anchored to reputation (a
    # great coach isn't more likely to be pass-heavy), so these are
    # centered on a league-average 50 with bounded seeded variance.
    run_pass_tendency: int = 50       # higher = more pass
    offensive_aggression: int = 50    # 4th downs, shot plays
    pace: int = 50
    red_zone_offense_bias: int = 50   # higher = more pass inside the 20
    two_point_tendency: int = 50
    blitz_rate: int = 50
    coverage_mix: int = 50            # 0 = man heavy, 100 = zone heavy
    fourth_down_defense: int = 50     # short-yardage aggressiveness
    red_zone_defense_bias: int = 50
    special_teams_focus: int = 50

    # --- Performance & management ratings, 0-99 (GDD Sec 7.7.2.3) ---
    # Quality: these ARE anchored to `reputation` (plus bounded seeded
    # variance), so the real salary signal actually means something.
    player_dev_offense: int = 50
    player_dev_defense: int = 50
    discipline: int = 50
    motivation_chemistry: int = 50
    red_zone_offense: int = 50
    red_zone_defense: int = 50

    # --- Lifecycle & outcome counters (GDD Sec 7.7.2.4) ---
    # All start at zero at league seed -- no real career-history source.
    career_wins: int = 0
    career_losses: int = 0
    playoff_wins: int = 0
    sb_titles: int = 0
    coach_awards: int = 0
    seasons_coached: int = 0
    # Computed each offseason (GDD Sec 8.2.3's JSS), stored so the Staff
    # page can show the same number the firing logic used.
    job_security_score: float = 50.0
    retired: bool = False

    # --- R3d: Hiring/Firing/Promotion Market lifecycle fields ---
    # Sec 5: what kind of appointment this coach currently holds. Every
    # real-seeded coach starts Permanent (they were already the real
    # incumbent); only R3d's hiring logic ever sets the other three.
    appointment_type: str = APPOINTMENT_PERMANENT
    # The season_number this coach started in their CURRENT role on
    # their CURRENT team -- Sec 3.4's Tenure Modifier needs tenure WITH
    # THIS TEAM, not total career seasons_coached (which keeps
    # accumulating across a firing-and-rehire-elsewhere). Real-seeded
    # coaches start at season 0 (an assumed, not literally-tracked,
    # start -- see coach_hiring.py's tenure_years()).
    tenure_start_season: int = 0
    # Sec 8's Tier 3 pool tag -- None for every real 433-seed coach
    # (including ones later fired into free agency). See POOL_TIER_*
    # above.
    pool_tier: Optional[str] = None
    # Short real background blurb, only ever populated for pool_tier
    # candidates (their real "Key Distinction" column from the seed
    # file) -- None for the 433 real staff, which has no such text to
    # import and none is fabricated for them.
    background: Optional[str] = None

    # R13: which bucket this coach's ratings feed into (see FOCUS_AREAS
    # above). Real, changeable via the Staff page for the user's own team;
    # AI teams' assistants get reassigned autonomously every offseason
    # (app/services/coach_ai.py's run_focus_autonomy()).
    focus_area: str = FOCUS_DEVELOPMENT

    # --- Career championship rollups by role held (GDD Sec 7.9.1) ---
    hc_afc_championships: int = 0
    hc_nfc_championships: int = 0
    hc_super_bowl_wins: int = 0
    oc_afc_championships: int = 0
    oc_nfc_championships: int = 0
    oc_super_bowl_wins: int = 0
    dc_afc_championships: int = 0
    dc_nfc_championships: int = 0
    dc_super_bowl_wins: int = 0
    st_afc_championships: int = 0
    st_nfc_championships: int = 0
    st_super_bowl_wins: int = 0
    ac_afc_championships: int = 0
    ac_nfc_championships: int = 0
    ac_super_bowl_wins: int = 0

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_free_agent(self) -> bool:
        return self.team_abbr is None

    @property
    def title(self) -> str:
        """The display title. For an AC this is the real seed title
        rebuilt from `specialty` (e.g. "Quarterbacks Coach"), not the
        generic "Assistant Coach" -- the specialty IS the real data, and
        collapsing it on screen would throw away the only thing that
        distinguishes 14 assistants from each other."""
        if self.role is CoachRole.AC and self.specialty:
            return f"{self.specialty} Coach"
        return ROLE_TITLES[CoachRole(self.role)]

    @property
    def conference_titles(self) -> int:
        return (
            self.hc_afc_championships + self.hc_nfc_championships
            + self.oc_afc_championships + self.oc_nfc_championships
            + self.dc_afc_championships + self.dc_nfc_championships
            + self.st_afc_championships + self.st_nfc_championships
            + self.ac_afc_championships + self.ac_nfc_championships
        )

    @property
    def super_bowl_wins(self) -> int:
        return (
            self.hc_super_bowl_wins + self.oc_super_bowl_wins
            + self.dc_super_bowl_wins + self.st_super_bowl_wins
            + self.ac_super_bowl_wins
        )

    @property
    def win_pct(self) -> float:
        total = self.career_wins + self.career_losses
        return self.career_wins / total if total else 0.0

    @property
    def overall(self) -> int:
        """A single 0-99 composite for list sorting and the Staff page's
        Overall Rating dial. Deliberately a plain average of the six
        Sec 7.7.2.3 performance ratings blended with reputation -- there
        is no GDD formula for a coach OVR (unlike a player's, Sec 7.1),
        so this is this module's own documented choice, not a GDD value.
        Reputation carries half the weight because it's the only piece
        anchored to real data. (`clock_management`/`challenge_sense` were
        dropped from this average 2026-09-11 -- no clock model and no
        challenge system exist anywhere in this engine, so neither rating
        ever had a signal to move on; see ROADMAP.md Sec 4c.)"""
        perf = (
            self.player_dev_offense + self.player_dev_defense + self.discipline
            + self.motivation_chemistry + self.red_zone_offense + self.red_zone_defense
        ) / 6.0
        return int(round(0.5 * perf + 0.5 * self.reputation))


class CoachSeasonStats(SQLModel, table=True):
    """One row per (coach, season, role held) -- GDD Sec 7.9.1.

    Written on championship-game finalize by app/engine/coach_awards.py's
    credit pass, which is idempotent per Sec 7.9.2: re-finalizing the
    same game must never double-count, so the primary key is the
    (coach_id, season, role) triple itself rather than an autoincrement.
    """
    coach_id: str = Field(primary_key=True)
    season: int = Field(primary_key=True)
    role: CoachRole = Field(primary_key=True)
    team_abbr: str = ""
    wins: int = 0
    losses: int = 0
    made_playoffs: bool = False
    conference_title: str = CONFERENCE_TITLE_NONE   # NONE | AFC | NFC
    super_bowl_result: str = SUPER_BOWL_NONE        # NONE | LOSS | WIN
