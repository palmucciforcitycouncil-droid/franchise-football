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

The one generated field with a real anchor is `reputation`: it STARTS as
the coach's `salary_aav` percentile **within their own role tier** (HC
pool vs. OC/DC pool vs. AC pool -- comparing an assistant's salary
against a head coach's would be meaningless), mapped onto 40-99, and it
anchors the OTHER generated ratings rather than those being drawn blind.
As of R16 (docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md), reputation
no longer freezes at that import-time snapshot -- it's real and EARNED
from then on: `coach_progression.py` moves it every offseason based on
real win_pct and a discrete bonus for a conference title/Super Bowl won
that season, so a coach's market value (which reads `overall`, itself
half-weighted on `reputation`) genuinely rises with real success.

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
    """GDD Sec 7.7.2.1. ST (Special Teams Coordinator) existed as its own
    coordinator-tier role from 2026-09-11 through R16, when it was
    removed outright (docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md):
    every real Special Teams Coordinator becomes an AC with specialty
    "Special Teams" instead -- a real org-chart demotion, not a firing.
    See Sec 7.7.2.1a for how every other real AC title collapses into
    AC + a `specialty` tag."""
    HC = "HC"
    OC = "OC"
    DC = "DC"
    AC = "AC"


ROLE_TITLES: dict[CoachRole, str] = {
    CoachRole.HC: "Head Coach",
    CoachRole.OC: "Offensive Coordinator",
    CoachRole.DC: "Defensive Coordinator",
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
    OC/DC share one tier (the same organizational level). Originally
    scripts/import_coaches.py's own private `_tier_key` (reputation
    percentile at import time); promoted here so app/engine/coach_
    contracts.py's coach_market_value() can share the identical grouping
    at negotiation time instead of a second, potentially-drifting copy."""
    if role is CoachRole.HC:
        return "HC"
    if role in (CoachRole.OC, CoachRole.DC):
        return "COORD"
    return "AC"


# GDD Appendix S.2's real 2026 coach salary ranges (HC $4-10M, OC/DC
# $1-2.5M, ST $0.7-1.5M, AC $0.2-0.8M) already encode a real tiering
# signal that the ORIGINAL reputation_from_salary() threw away by
# mapping each role tier's percentile onto the SAME shared 40-99 band
# independently -- 2026-09-20 playtest (Brian): "assistant coaches have
# 90 OVR ratings while HC have 60... 24 yo assistants with no coaching
# experience will end up hired as HCs." Confirmed on the real 433-coach
# seed: AC median overall (78) was HIGHER than HC median (73), and AC's
# max (99) matched HC's max, because the highest-paid assistant and the
# highest-paid head coach both land near the 99th percentile of their
# own tier regardless of the fact that an assistant's $800K salary
# ceiling is a fraction of a head coach's $4M salary FLOOR.
#
# These bands are each tier's real floor/ceiling salary evaluated on a
# LOG scale (compensation is log-normal, not linear -- anchoring
# linearly collapses HC's $4-10M range to the top ~6 points of a 0-100
# scale and crowds COORD/AC into the bottom ~15), against the full real
# 2026 range ($200K AC floor -> $10M HC ceiling) mapped onto [35, 99]:
#   HC    log([$4M,$10M])       -> rep [84, 99]
#   COORD log([$0.7M,$2.5M])    -> rep [55, 76]   (ST's floor to OC/DC's ceiling)
#   AC    log([$0.2M,$0.8M])    -> rep [35, 58]
# HC and COORD never overlap (their real dollar ranges don't either).
# COORD and AC overlap by 3 points (55-58) -- a real top-paid assistant
# can plausibly out-earn a real bottom-tier ST coordinator, so a LITTLE
# overlap there is the historically accurate outcome, not a bug (a
# LITTLE overlap at a tier boundary is realistic; total separation
# across the board would not be).
REPUTATION_TIER_BAND: dict[str, tuple[int, int]] = {
    "HC": (84, 99),
    "COORD": (55, 76),
    "AC": (35, 58),
}


def reputation_from_tier_percentile(pct: float, tier: str) -> int:
    """`pct` (0.0-1.0): a coach's percentile rank of real salary within
    their OWN role tier's real population (see tier_key()). Maps that
    rank onto the TIER's own real band (REPUTATION_TIER_BAND) instead of
    a single band shared across all tiers, so an AC's reputation can
    never reach an HC's. Shared by scripts/import_coaches.py (fresh
    generation, every new save/template rebuild) and app/core/db.py's
    _migrate_schema() (the one-time rescale of coaches imported before
    this fix existed) so both paths use the exact same formula rather
    than two that could drift apart -- the same reason tier_key() itself
    was promoted to this module."""
    lo, hi = REPUTATION_TIER_BAND[tier]
    pct = max(0.0, min(1.0, pct))
    return int(round(lo + pct * (hi - lo)))


# R3d (Coach Hiring/Firing/Promotion Market) appointment designations --
# Sec 5 of docs/R3d_COACHING_SYSTEM_SPECIFICATION.md.
APPOINTMENT_PERMANENT = "Permanent"
APPOINTMENT_INTERIM = "Interim"
APPOINTMENT_ACTING = "Acting"
APPOINTMENT_TEMPORARY_PROMOTION = "TemporaryPromotion"
APPOINTMENT_TYPES = [
    APPOINTMENT_PERMANENT, APPOINTMENT_INTERIM, APPOINTMENT_ACTING, APPOINTMENT_TEMPORARY_PROMOTION,
]

# R16 (Coach Position-Group Impact, docs/R16_COACH_POSITION_IMPACT_
# SPECIFICATION.md) -- supersedes R13's mechanism entirely. Focus Area no
# longer touches play-calling at all (app/engine/coaching.py's tendency
# sliders now drive AI play-calling directly by ROLE again, decoupled from
# focus_area -- see that module's own docstring). A coach's chosen focus
# instead drives two things, both keyed off the SAME position-group
# taxonomy (app/engine/draft.py's GROUP_POSITIONS): a this-game player
# boost to the targeted group (app/engine/coaching.py) and a running
# seasonal development total (app/services/coach_focus_accumulator.py).
#
# Every role gets its OWN menu (Sec 3) -- narrower options target one
# group at higher magnitude, broader ones spread across more groups at
# lower magnitude (Sec 5's mapping table). `2 Min Offense` (a real Figma
# source option, R13-era) stays excluded -- no clock/2-minute-drill model
# exists anywhere in this engine.
FOCUS_BALANCED_GAMEPLAN = "Balanced Gameplan"          # HC only
FOCUS_OFFENSIVE_GAMEPLAN = "Offensive Gameplan"        # HC, OC
FOCUS_DEFENSIVE_GAMEPLAN = "Defensive Gameplan"        # HC, DC
FOCUS_RUNNING_GAME = "Running Game"                    # OC, AC
FOCUS_PASSING_GAME = "Passing Game"                    # OC, AC
FOCUS_RUN_DEFENSE = "Run Defense"                      # DC, AC
FOCUS_PASS_DEFENSE = "Pass Defense"                    # DC, AC
FOCUS_QB_PRESSURE = "QB Pressure"                      # DC, AC
FOCUS_QB = "QB"                                        # OC, AC
FOCUS_RECEIVERS = "Receivers"                          # OC, AC
FOCUS_OL = "OL"                                        # OC, AC
FOCUS_DL = "DL"                                        # AC only
FOCUS_SECONDARY = "Secondary"                          # AC only
FOCUS_SPECIAL_TEAMS = "Special Teams"                  # HC, AC (was "Special Teams Work")
FOCUS_DEVELOPMENT = "Development"                      # every role
FOCUS_SCOUTING = "Scouting"                            # every role
FOCUS_TRAINING = "Strength & Conditioning"             # every role (was "Training")

# Per-role menus, ordered widest -> narrowest (Sec 4). One stored string
# per concept -- OC's and AC's "Running Game"/"Passing Game"/etc. are the
# exact same bucket, not two spellings of it.
FOCUS_OPTIONS_BY_ROLE: dict[CoachRole, list[str]] = {
    CoachRole.HC: [
        FOCUS_BALANCED_GAMEPLAN, FOCUS_OFFENSIVE_GAMEPLAN, FOCUS_DEFENSIVE_GAMEPLAN,
        FOCUS_SPECIAL_TEAMS, FOCUS_DEVELOPMENT, FOCUS_SCOUTING, FOCUS_TRAINING,
    ],
    CoachRole.DC: [
        FOCUS_DEFENSIVE_GAMEPLAN, FOCUS_RUN_DEFENSE, FOCUS_PASS_DEFENSE, FOCUS_QB_PRESSURE,
        FOCUS_DEVELOPMENT, FOCUS_SCOUTING, FOCUS_TRAINING,
    ],
    CoachRole.OC: [
        FOCUS_OFFENSIVE_GAMEPLAN, FOCUS_RUNNING_GAME, FOCUS_PASSING_GAME,
        FOCUS_QB, FOCUS_RECEIVERS, FOCUS_OL,
        FOCUS_DEVELOPMENT, FOCUS_SCOUTING, FOCUS_TRAINING,
    ],
    CoachRole.AC: [
        FOCUS_RUN_DEFENSE, FOCUS_PASS_DEFENSE, FOCUS_QB_PRESSURE,
        FOCUS_RUNNING_GAME, FOCUS_PASSING_GAME,
        FOCUS_QB, FOCUS_RECEIVERS, FOCUS_OL, FOCUS_DL, FOCUS_SECONDARY, FOCUS_SPECIAL_TEAMS,
        FOCUS_DEVELOPMENT, FOCUS_SCOUTING, FOCUS_TRAINING,
    ],
}

# Every focus bucket's own driving rating(s) -- Sec 5's mapping table.
# Narrow buckets read one rating directly; medium ones are a weighted
# blend of two; the broad Gameplan buckets are an unweighted average of
# every rating on that side. Weights marked [tune] in the spec -- real
# structure, not yet playtested magnitudes.
_OFFENSE_RATINGS = ("qb_coaching", "rb_coaching", "wr_coaching", "ol_coaching")
_DEFENSE_RATINGS = ("dl_coaching", "lb_coaching", "secondary_coaching")

# focus -> (position groups touched, [(rating, weight), ...])
FOCUS_RATING_WEIGHTS: dict[str, list[tuple[str, float]]] = {
    FOCUS_OFFENSIVE_GAMEPLAN: [(r, 1.0) for r in _OFFENSE_RATINGS],
    FOCUS_DEFENSIVE_GAMEPLAN: [(r, 1.0) for r in _DEFENSE_RATINGS],
    FOCUS_RUNNING_GAME: [("rb_coaching", 0.6), ("ol_coaching", 0.4)],
    FOCUS_PASSING_GAME: [("qb_coaching", 0.5), ("wr_coaching", 0.5)],
    FOCUS_RUN_DEFENSE: [("dl_coaching", 0.6), ("lb_coaching", 0.4)],
    FOCUS_PASS_DEFENSE: [("lb_coaching", 0.3), ("secondary_coaching", 0.7)],
    FOCUS_QB_PRESSURE: [("dl_coaching", 0.65), ("lb_coaching", 0.35)],
    FOCUS_QB: [("qb_coaching", 1.0)],
    FOCUS_RECEIVERS: [("wr_coaching", 1.0)],
    FOCUS_OL: [("ol_coaching", 1.0)],
    FOCUS_DL: [("dl_coaching", 1.0)],
    FOCUS_SECONDARY: [("secondary_coaching", 1.0)],
    FOCUS_SPECIAL_TEAMS: [("st_coaching", 1.0)],
}

# focus -> the app.engine.draft.GROUP_POSITIONS keys it targets (Sec 5).
FOCUS_POSITION_GROUPS: dict[str, list[str]] = {
    FOCUS_OFFENSIVE_GAMEPLAN: ["QB", "RB", "WR", "TE", "OL"],
    FOCUS_DEFENSIVE_GAMEPLAN: ["DL", "LB", "CB", "S"],
    FOCUS_RUNNING_GAME: ["RB", "OL"],
    # OL added 2026-09-20 (Brian's ask): "boosting passing game - QB WR TE
    # OL, but for OL just their pass blocking ratings" -- app/engine/
    # coaching.py's FOCUS_GROUP_ATTRS narrows OL's actual boosted
    # attributes to pass_block only here (and run_block only under
    # Running Game above), so the two focuses never double up on the
    # same blocking skill.
    FOCUS_PASSING_GAME: ["QB", "WR", "TE", "OL"],
    FOCUS_RUN_DEFENSE: ["DL", "LB"],
    FOCUS_PASS_DEFENSE: ["LB", "CB", "S"],
    FOCUS_QB_PRESSURE: ["DL", "LB"],
    FOCUS_QB: ["QB"],
    FOCUS_RECEIVERS: ["WR", "TE"],
    FOCUS_OL: ["OL"],
    FOCUS_DL: ["DL"],
    FOCUS_SECONDARY: ["CB", "S"],
    FOCUS_SPECIAL_TEAMS: ["K", "P"],
}

# Breadth tier -- Sec 5/6: narrower buckets get a bigger this-game boost
# per player than broad ones ("DEF Gameplan boosts everyone but less than
# a DL-targeted focus"). Values are relative boost multipliers [tune].
FOCUS_BREADTH_MULTIPLIER: dict[str, float] = {
    FOCUS_OFFENSIVE_GAMEPLAN: 0.4, FOCUS_DEFENSIVE_GAMEPLAN: 0.4,
    FOCUS_RUNNING_GAME: 0.7, FOCUS_PASSING_GAME: 0.7, FOCUS_RUN_DEFENSE: 0.7,
    FOCUS_PASS_DEFENSE: 0.7, FOCUS_QB_PRESSURE: 0.7,
    FOCUS_QB: 1.0, FOCUS_RECEIVERS: 1.0, FOCUS_OL: 1.0, FOCUS_DL: 1.0,
    FOCUS_SECONDARY: 1.0, FOCUS_SPECIAL_TEAMS: 1.0,
}


def focus_options_for(coach: "Coach") -> list[str]:
    """The real menu this coach's role offers (Sec 4) -- every role gets
    the identical list regardless of specialty, since specialty no
    longer gates which focuses are even selectable (only the DEFAULT
    does, see default_focus_area_for())."""
    return FOCUS_OPTIONS_BY_ROLE[CoachRole(coach.role)]


def _rating_for_focus(coach: "Coach", focus: str) -> float:
    weights = FOCUS_RATING_WEIGHTS.get(focus)
    if not weights:
        return 0.0
    total_w = sum(w for _, w in weights)
    return sum(getattr(coach, rating) * w for rating, w in weights) / total_w


def default_focus_area_for(role: CoachRole, coach: Optional["Coach"] = None) -> str:
    """The sensible starting focus_area for a freshly-imported, freshly-
    migrated, or freshly-hired/promoted coach
    (docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md Sec 4).

    HC/OC/DC get a fixed role default (Balanced/Offensive/Defensive
    Gameplan) -- their job description IS that broad lane, not a
    position specialty to rate against.

    An AC defaults to whichever of their OWN menu options they're rated
    highest at (Sec 4's explicit design: "the focus of assistants should
    default to whichever they have the highest rating"), tie-broken
    toward Development -- requires the real Coach row (its 8 granular
    ratings), not just role, so `coach` is required for AC and ignored
    for every other role."""
    if role is CoachRole.OC:
        return FOCUS_OFFENSIVE_GAMEPLAN
    if role is CoachRole.DC:
        return FOCUS_DEFENSIVE_GAMEPLAN
    if role is CoachRole.HC:
        return FOCUS_BALANCED_GAMEPLAN
    assert coach is not None, "AC default requires the real Coach row"
    options = FOCUS_OPTIONS_BY_ROLE[CoachRole.AC]
    best = FOCUS_DEVELOPMENT
    best_rating = _rating_for_focus(coach, FOCUS_DEVELOPMENT)  # 0.0 -- Development has no rating weight
    for option in options:
        if option in (FOCUS_DEVELOPMENT, FOCUS_SCOUTING, FOCUS_TRAINING):
            continue  # no position-group rating backs these -- never the "best" pick here
        rating = _rating_for_focus(coach, option)
        if rating > best_rating:
            best, best_rating = option, rating
    return best


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
    # Line", "Special Teams (Assistant)"). Null for HC/OC/DC, whose
    # role already says what they do -- GDD Sec 7.7.2.1a. R16: this can
    # now change over a coach's career (see coach_progression.py's
    # specialty-relabeling pass) if their ratings drift somewhere else.
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
    discipline: int = 50
    motivation_chemistry: int = 50
    red_zone_offense: int = 50
    red_zone_defense: int = 50

    # --- R16: per-position-group coaching quality, 0-99, same anchored-
    # to-reputation generation as the ratings above (docs/R16_COACH_
    # POSITION_IMPACT_SPECIFICATION.md Sec 1). Every coach carries all 8
    # regardless of role, exactly like offensive_profile/defensive_profile
    # already do -- only the USE of each rating varies by role/focus.
    # `wr_coaching` covers WR AND TE; `dl_coaching` covers edge rushers
    # (this engine's Position enum files LE/RE under DL, not LB -- see
    # app/engine/draft.py's GROUP_POSITIONS). player_dev_offense/defense
    # (read by season_state.py/free_agency.py) are now COMPUTED from
    # these below, not stored -- see the properties near the bottom of
    # this class.
    qb_coaching: int = 50
    rb_coaching: int = 50
    wr_coaching: int = 50
    ol_coaching: int = 50
    dl_coaching: int = 50
    lb_coaching: int = 50
    secondary_coaching: int = 50
    st_coaching: int = 50

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

    # Which bucket this coach's focus feeds into (see FOCUS_OPTIONS_BY_ROLE
    # above). Real, changeable via the Staff page for the user's own team;
    # AI teams get reassigned autonomously every offseason
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
            + self.ac_afc_championships + self.ac_nfc_championships
        )

    @property
    def super_bowl_wins(self) -> int:
        return (
            self.hc_super_bowl_wins + self.oc_super_bowl_wins
            + self.dc_super_bowl_wins + self.ac_super_bowl_wins
        )

    @property
    def win_pct(self) -> float:
        total = self.career_wins + self.career_losses
        return self.career_wins / total if total else 0.0

    @property
    def player_dev_offense(self) -> float:
        """R16: computed, not stored -- the offense-side average of the
        8 granular position-group ratings (qb/rb/wr/ol_coaching), same
        pool `Sec 5's Offensive Gameplan focus averages. Replaces the old
        directly-generated field of the same name; every reader (this
        class's own `overall`, season_state.apply_progression_to_roster(),
        free_agency.fill_roster_gaps()) is unaffected by the rename to a
        property."""
        return (self.qb_coaching + self.rb_coaching + self.wr_coaching + self.ol_coaching) / 4.0

    @property
    def player_dev_defense(self) -> float:
        """R16: computed, not stored -- the defense-side average of the
        8 granular position-group ratings (dl/lb/secondary_coaching)."""
        return (self.dl_coaching + self.lb_coaching + self.secondary_coaching) / 3.0

    @property
    def primary_side(self) -> str:
        """R16: which side of the ball this coach is really best at,
        purely from their own ratings -- whichever of {offense average,
        defense average, st_coaching} is highest. Used two ways (Sec 1):
        a quick-glance "Offense"/"Defense"/"Special Teams" tag on the
        Staff page, and the Coaching Tree's alignment signal (Sec 3) --
        deliberately rating-based rather than a specialty-text lookup,
        so it can never disagree with the numbers actually driving
        everything else."""
        sides = {"Offense": self.player_dev_offense, "Defense": self.player_dev_defense,
                 "Special Teams": float(self.st_coaching)}
        return max(sides, key=lambda k: sides[k])

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
