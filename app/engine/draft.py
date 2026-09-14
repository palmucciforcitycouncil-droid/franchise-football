"""
R5: Draft System (docs/R5_DRAFT_SYSTEM_SPECIFICATION.md). Real, deterministic
per-LEAGUE_SEED annual rookie class generation + a greedy need-aware draft
simulation, feeding real Player rows into the existing roster DB -- not a
separate "Prospect" table.

Real, disclosed scope decisions made building this (ROADMAP.md Sec4f has
the full account):

- **No new DB tables.** The spec's Prospect/DraftPick/DraftOrder/DraftBoard
  entities would each need a real schema migration against the live
  Player DB -- this project has hit REAL data-loss incidents from exactly
  that category of change multiple times already (see ROADMAP.md Sec2b's
  incident history, and tonight's own "data/franchise_football.db.bak-
  pre*" backups). Instead: a drafted OR undrafted prospect becomes a real
  `Player` row directly (using the table's existing columns, no new
  ones), and draft RESULTS (order, picks, round/team/player) persist as
  JSON via app/services/draft_store.py, the same pattern power_rank_
  history.py/award_race_history.py/headlines_history.py already use.
- **Runs automatically every season**, inside season_state.start_new_
  season() (not a one-time league-init event the spec's own Sec9.1
  describes as the "current implementation") -- a draft that only ever
  happens once produces a league that never gets meaningfully fresh
  rookies again, which undercuts the whole point of building this. The
  underlying generate+simulate logic is identical either way; this is a
  strictly more useful hook for the same amount of code.
- **Live pick-by-pick draft, added 2026-09-13 (Brian's ask).** The class
  for next season is now generated the moment the CURRENT season is
  built (`season_state._build_season()`) and persisted in full via
  `app/services/draft_class_store.py` -- browsable, sortable, and
  personally board-able (`app/services/draft_board_store.py`, reference-
  only, never affects the real simulated picks below) for that entire
  season, not just after the fact. The draft itself resolves one real
  slot at a time (`draft_slots()`/`resolve_one_pick()`/
  `apply_single_pick_to_db()` below), driven by the user's own pacing on
  the Draft page (Sim Pick / Sim to Your Next Pick / End) and tracked in
  `app/services/draft_progress_store.py` across separate HTTP requests
  -- it deliberately does NOT auto-run the user's own team's picks; only
  "End" auto-resolves them, as an explicit bail-out. `run_draft_for_
  season()`/`simulate_draft()`/`apply_draft_to_db()` below are UNCHANGED
  and still used as the atomic, one-call fallback (season_state.
  finish_offseason() only reaches for them if the live draft was never
  engaged with at all) and by every existing test -- the live event is
  an additional way to resolve the same real, deterministic picks, not
  a replacement pipeline.
- **Attribute generation is a simplified position-profile formula**, not
  the spec's fuller per-attribute-variance table for every one of the
  Player model's ~50 real attributes. Each position has a small set of
  "key attributes" (the ones overall_rating is actually derived from,
  same spirit as the spec's own WR/QB worked examples) generated from a
  seeded per-prospect `base_talent` plus a position-specific bias;
  everything else defaults to a duller `base_talent - 15` value with
  modest noise -- real variance, position-flavored, just not hand-tuned
  per attribute per position.
- **Rookie-scale AAV uses the spec's own Sec 8.1 real-dollar anchor
  points** (pick 1 = $13.64M, etc.), scaled by this project's REAL
  SALARY_CAP_BASE ($720M, contracts.py) rather than Sec 8.1's literal
  $302M divisor -- that divisor is the real-world 2026 NFL cap figure,
  numerically incompatible with this project's own rescaled cap for the
  exact reason contracts.py's own SALARY_CAP_BASE comment documents
  (Sec 8.3's real dollar anchor is incompatible with this project's
  Madden-derived player-salary scale). Individual real-dollar salary
  figures elsewhere in this project (e.g. M8's real Mahomes contract)
  stay on the real scale -- it's only ever the CAP CEILING that gets
  rescaled -- so anchoring rookie growth to SALARY_CAP_BASE keeps this
  internally consistent with every other contract calculation.
- **Undrafted-pool cleanup is Tier-1-only** (hard delete at
  years_remaining == 0), not the spec's fuller two-tier percentile
  pruning (Sec 9.2's "delete bottom 25%/10%"). A real, simpler rule in
  the same spirit -- expired UDFAs leave, everyone else stays -- without
  needing a percentile-ranking pass across the whole pool every offseason.
- **Position groups collapse to this engine's real granular Position
  enum** (spec's "OL"/"DL"/"LB"/"S" groups map onto 5/3/3/2 real Madden-
  style positions respectively; "RB" maps onto HB only -- fullbacks
  aren't drafted, a disclosed simplification, not an oversight).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.rng import RNG, stable_seed
from app.models.coach import CoachRole, FOCUS_SCOUTING
from app.models.player import Player, Position

# ---------------------------------------------------------------------------
# Position groups + quota bands (docs/R5_DRAFT_SYSTEM_SPECIFICATION.md Sec14)
# ---------------------------------------------------------------------------

GROUP_POSITIONS: dict[str, list[Position]] = {
    "QB": [Position.QB],
    "RB": [Position.HB],
    "WR": [Position.WR],
    "TE": [Position.TE],
    "OL": [Position.T, Position.G, Position.C],
    "DL": [Position.EDGE, Position.DT],
    "LB": [Position.LB],
    "CB": [Position.CB],
    "S": [Position.S],
    "K": [Position.K],
    "P": [Position.P],
}

GROUP_BANDS: dict[str, tuple[int, int]] = {
    "QB": (7, 9), "RB": (24, 28), "WR": (33, 37), "TE": (16, 20),
    "OL": (40, 44), "DL": (30, 34), "LB": (24, 28), "CB": (22, 26),
    "S": (14, 18), "K": (1, 2), "P": (1, 2),
}

ROUNDS = 7

# attr_name -> (overall_rating weight, bias added to base_talent)
_OL_PROFILE = {"pass_block": (0.30, 5), "run_block": (0.30, 5), "strength": (0.20, 8), "awareness": (0.20, -5)}
_DL_PROFILE = {"block_shedding": (0.25, 5), "pursuit": (0.20, 0), "strength": (0.20, 8), "power_moves": (0.20, 5), "tackle": (0.15, 0)}
_LB_PROFILE = {"tackle": (0.25, 5), "pursuit": (0.20, 5), "play_recognition": (0.20, 0), "hit_power": (0.15, 5), "speed": (0.10, 0), "zone_coverage": (0.10, -5)}
_DB_PROFILE = {"man_coverage": (0.20, 0), "zone_coverage": (0.25, 5), "speed": (0.20, 3), "hit_power": (0.15, 0), "play_recognition": (0.20, 5)}

POSITION_PROFILES: dict[Position, dict[str, tuple[float, int]]] = {
    Position.QB: {
        "throw_power": (0.15, 5), "throw_accuracy_short": (0.15, 5), "throw_accuracy_mid": (0.15, 3),
        "throw_accuracy_deep": (0.15, 0), "awareness": (0.20, 0), "throw_under_pressure": (0.10, -5),
        "agility": (0.10, -10),
    },
    Position.HB: {
        "speed": (0.25, 8), "agility": (0.20, 8), "carrying": (0.15, 5), "break_tackle": (0.15, 0),
        "ball_carrier_vision": (0.15, 3), "strength": (0.10, -5),
    },
    Position.WR: {
        "speed": (0.30, 8), "agility": (0.25, 5), "catching": (0.30, 8), "strength": (0.15, -8),
    },
    Position.TE: {
        "catching": (0.30, 3), "run_block": (0.25, 0), "strength": (0.20, 5), "speed": (0.15, -5),
        "medium_route_running": (0.10, 0),
    },
    Position.T: _OL_PROFILE, Position.G: _OL_PROFILE, Position.C: _OL_PROFILE,
    Position.EDGE: _DL_PROFILE, Position.DT: _DL_PROFILE,
    Position.LB: _LB_PROFILE,
    Position.CB: {
        "man_coverage": (0.25, 5), "zone_coverage": (0.20, 3), "speed": (0.25, 8), "press": (0.15, 0),
        "agility": (0.15, 5),
    },
    Position.S: _DB_PROFILE,
    Position.K: {"kick_power": (0.45, 10), "kick_accuracy": (0.45, 10), "awareness": (0.10, 0)},
    Position.P: {"kick_power": (0.5, 5), "kick_accuracy": (0.4, 10), "awareness": (0.1, 0)},
}

ALL_ATTR_FIELDS = [
    "speed", "acceleration", "strength", "agility", "jumping", "stamina", "toughness", "durability",
    "throw_power", "throw_accuracy_short", "throw_accuracy_mid", "throw_accuracy_deep", "play_action",
    "throw_on_the_run", "throw_under_pressure", "break_sack",
    "catching", "spectacular_catch", "catch_in_traffic", "short_route_running", "medium_route_running",
    "deep_route_running", "release",
    "carrying", "trucking", "change_of_direction", "ball_carrier_vision", "stiff_arm", "spin_move",
    "juke_move", "break_tackle",
    "run_block", "pass_block", "run_block_power", "run_block_finesse", "pass_block_power",
    "pass_block_finesse", "lead_block", "impact_blocking",
    "tackle", "hit_power", "block_shedding", "pursuit", "play_recognition", "man_coverage", "zone_coverage",
    "press", "power_moves", "finesse_moves",
    "kick_power", "kick_accuracy", "kick_return",
    "awareness",
]

QB_STRENGTH_BASE_TALENT = {"weak": 55.0, "strong": 65.0, "elite": 75.0}

_FIRST_NAMES = [
    "James", "Michael", "Chris", "Marcus", "Devon", "Tyler", "Jordan", "Xavier", "Malik", "Isaiah",
    "Dominique", "Trevon", "Jaylen", "Antoine", "Cameron", "Darius", "Elijah", "Jamal", "Kendall", "Andre",
    "Bryce", "Caleb", "Damon", "Emmanuel", "Frankie", "Gerald", "Harrison", "Ivan", "Jaden", "Keon",
    "Lamar", "Mason", "Nasir", "Omari", "Preston", "Quentin", "Rashad", "Sean", "Terrance", "Vincent",
]
_LAST_NAMES = [
    "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson",
    "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Robinson", "Clark", "Rodriguez", "Lewis",
    "Walker", "Hall", "Allen", "Young", "King", "Wright", "Scott", "Green", "Baker", "Adams",
    "Nelson", "Carter", "Mitchell", "Perez", "Roberts", "Turner", "Phillips", "Campbell", "Parker", "Evans",
]
_COLLEGES = [
    "Alabama", "Georgia", "Ohio State", "Clemson", "LSU", "Oklahoma", "Michigan", "Texas", "Florida", "USC",
    "Penn State", "Notre Dame", "Oregon", "Wisconsin", "Miami", "Auburn", "Florida State", "Texas A&M",
    "Tennessee", "Iowa", "Utah", "Baylor", "Washington", "UCLA", "Ole Miss", "Kentucky", "Missouri",
    "North Carolina", "Virginia Tech", "Michigan State", "Stanford", "Arizona State", "TCU", "Louisville",
    "West Virginia", "Nebraska", "Kansas State", "Oklahoma State", "Mississippi State", "South Carolina",
]

_HEIGHT_WEIGHT_BY_GROUP = {  # (min_in, max_in), (min_lb, max_lb) -- deterministic ranges, not real scouting data
    "QB": ((72, 77), (205, 235)), "RB": ((68, 73), (190, 225)), "WR": ((70, 76), (175, 215)),
    "TE": ((75, 79), (240, 260)), "OL": ((75, 80), (295, 330)), "DL": ((74, 79), (265, 320)),
    "LB": ((72, 76), (225, 250)), "CB": ((69, 74), (175, 200)), "S": ((70, 74), (190, 215)),
    "K": ((70, 74), (185, 210)), "P": ((72, 76), (195, 220)),
}


def _clamp(v: float) -> int:
    return max(20, min(99, round(v)))


@dataclass
class ProspectDraft:
    """A pure, DB-free representation of one generated prospect -- kept
    separate from Player so generation/simulation can be unit-tested
    (and re-tested for determinism) without a database at all. Only
    turned into a real Player row by apply_draft_to_db()."""
    index: int
    first_name: str
    last_name: str
    position: Position
    college: str
    age: int
    height_inches: int
    weight_lbs: int
    overall_rating: int
    potential: int
    attrs: dict[str, int]
    draft_grade: str
    group: str = ""


@dataclass
class DraftPickResult:
    round: int
    overall_pick: int
    team_abbr: str
    prospect_index: int


@dataclass
class DraftResult:
    order: list[str]
    picks: list[DraftPickResult]
    undrafted_indexes: list[int] = field(default_factory=list)


def _qb_class_strength(league_seed: int, season_number: int) -> str:
    roll = stable_seed(league_seed, "draft", season_number, "class_strength") % 100
    if roll < 25:
        return "weak"
    if roll < 75:
        return "strong"
    return "elite"


def _group_for(position: Position) -> str:
    # FB isn't in GROUP_POSITIONS (fullbacks aren't generated as prospects,
    # see module docstring), but real rostered FBs still have to count
    # toward a team's RB group -- they used to fall through to "OL".
    if position == Position.FB:
        return "RB"
    for group, positions in GROUP_POSITIONS.items():
        if position in positions:
            return group
    return "OL"  # unreachable given GROUP_POSITIONS covers every Position member


def _draft_grade(overall: int) -> str:
    if overall >= 85:
        return "A"
    if overall >= 70:
        return "B"
    if overall >= 55:
        return "C"
    return "D"


def _generate_one_prospect(index: int, position: Position, league_seed: int, season_number: int, qb_strength: str) -> ProspectDraft:
    seed = stable_seed(league_seed, "draft", season_number, index)
    rng = RNG.with_seed(seed)

    mean = QB_STRENGTH_BASE_TALENT[qb_strength] if position == Position.QB else 60.0
    base_talent = max(30.0, min(90.0, rng.gauss(mean, 12)))

    profile = POSITION_PROFILES.get(position, {})
    attrs: dict[str, int] = {}
    for name in ALL_ATTR_FIELDS:
        if name in profile:
            _, bias = profile[name]
            attrs[name] = _clamp(base_talent + bias + rng.gauss(0, 10))
        else:
            attrs[name] = _clamp(base_talent - 15 + rng.gauss(0, 10))

    if profile:
        total_w = sum(w for w, _ in profile.values())
        overall = _clamp(sum(attrs[name] * w for name, (w, _) in profile.items()) / total_w)
    else:
        overall = _clamp(sum(attrs.values()) / len(attrs))

    potential = _clamp(overall + rng.uniform(0, 20))
    group = _group_for(position)
    (h_min, h_max), (w_min, w_max) = _HEIGHT_WEIGHT_BY_GROUP[group]
    height = rng.r().randint(h_min, h_max)
    weight = rng.r().randint(w_min, w_max)
    age = rng.r().randint(21, 23)
    first = rng.choice(_FIRST_NAMES)
    last = rng.choice(_LAST_NAMES)
    college = rng.choice(_COLLEGES)

    return ProspectDraft(
        index=index, first_name=first, last_name=last, position=position, college=college,
        age=age, height_inches=height, weight_lbs=weight, overall_rating=overall, potential=potential,
        attrs=attrs, draft_grade=_draft_grade(overall), group=group,
    )


def generate_draft_class(league_seed: int, season_number: int) -> list[ProspectDraft]:
    """Deterministic: the same (league_seed, season_number) always produces
    the same class (GDD Sec 1.3). Class size is whatever the independent
    per-group band draws sum to (no forced total -- the spec's own
    235-265 target is a natural byproduct of the real per-group bands,
    not separately enforced)."""
    qb_strength = _qb_class_strength(league_seed, season_number)
    prospects: list[ProspectDraft] = []
    index = 0
    for group, positions in GROUP_POSITIONS.items():
        lo, hi = GROUP_BANDS[group]
        count_seed = stable_seed(league_seed, "draft", season_number, "count", group)
        count = lo + count_seed % (hi - lo + 1)
        for i in range(count):
            position = positions[i % len(positions)]
            prospects.append(_generate_one_prospect(index, position, league_seed, season_number, qb_strength))
            index += 1
    return prospects


def _strength_of_schedule(season, team_abbr: str) -> float:
    """Average win% of every opponent team_abbr actually played this
    season -- the standard real SOS formula, computed directly from
    already-real season.records/schedule, not a modeled stat."""
    opponents = []
    for week in season.schedule:
        for game in week:
            if game.result is None:
                continue
            if game.home_abbr == team_abbr:
                opponents.append(game.away_abbr)
            elif game.away_abbr == team_abbr:
                opponents.append(game.home_abbr)
    if not opponents:
        return 0.0
    return sum(season.records[o].win_pct for o in opponents) / len(opponents)


def compute_draft_order(season, league_seed: int, season_number: int) -> list[str]:
    """Worst-to-best (Sec 3.1): win% ascending, then SOS ascending (a
    weaker schedule means the team's record overstates them, so they
    pick earlier -- the real, standard tiebreak direction), then a
    seeded coin flip for anything still tied. UNCHANGED by Draft-Pick
    Trading (Sec 8.5) -- this is still the real, pure ORIGINAL-team slot
    order; app/services/draft_pick_store.py's ownership layer sits on
    top of it, never inside it (a traded pick is still "the original
    team's slot," just picked by whoever traded for it)."""
    abbrs = list(season.records.keys())
    sos = {a: _strength_of_schedule(season, a) for a in abbrs}

    def sort_key(a: str):
        tie = stable_seed(league_seed, season_number, "draft_tiebreak", a)
        return (season.records[a].win_pct, sos[a], tie)

    return sorted(abbrs, key=sort_key)


def estimated_pick_order_rank(season, original_team_abbr: str) -> int:
    """Sec 8.5's trades can include a pick from a season that HASN'T
    happened yet (this year's own draft resolves only once the season
    ends; next year's and the year after's are even further out) -- so
    there is no real final slot to price a future pick by. This is the
    best REAL signal available before that: this team's rank (1 = worst)
    by the CURRENT season's live win_pct, the exact same real, computed
    ordering compute_draft_order() itself uses once a season is actually
    over, just read mid-season as an estimate. A disclosed simplification
    (a real front office can't know a future pick's exact slot before the
    season that earns it ends either) -- not a fabricated placeholder."""
    abbrs = sorted(season.records.keys(), key=lambda a: season.records[a].win_pct)
    return abbrs.index(original_team_abbr) + 1 if original_team_abbr in abbrs else 16


# Sec 8.5's own pick-value chart (R5_DRAFT_SYSTEM_SPECIFICATION.md Sec
# 4.1) -- "disclosed as a game-balance simplification, not a real NFL
# claim," that spec's own words. Used as-is: it's the only real number
# this project has for pick value, so it's the real default rather than
# a fabricated alternative. round -> [(pick_order_rank upper bound
# within that round, value), ...], banded in quarters of 8 (this
# engine's real 32-team league).
PICK_VALUE_TABLE: dict[int, list[tuple[int, float]]] = {
    1: [(8, 3000), (16, 2200), (24, 1800), (32, 1400)],
    2: [(8, 1000), (16, 800), (24, 600), (32, 500)],
    3: [(8, 400), (16, 300), (24, 250), (32, 200)],
    4: [(8, 150), (16, 120), (24, 100), (32, 80)],
    5: [(8, 60), (16, 50), (24, 40), (32, 30)],
    6: [(8, 25), (16, 20), (24, 15), (32, 10)],
    7: [(8, 8), (16, 6), (24, 4), (32, 2)],
}


def pick_value(round: int, pick_order_rank: int) -> float:
    """PICK_VALUE_TABLE's real lookup. `pick_order_rank` is this pick's
    1-32 position WITHIN its round (1 = the first team to pick that
    round, i.e. the worst record) -- not the overall 1-224 pick number."""
    bands = PICK_VALUE_TABLE.get(round)
    if not bands:
        return 0.0
    for upper, value in bands:
        if pick_order_rank <= upper:
            return value
    return bands[-1][1]


def _all_teams_group_counts() -> dict[str, dict[str, int]]:
    """Real live roster counts per team per position group, for every
    team in ONE query -- not a fabricated priority list, but also not a
    per-pick DB round-trip: simulate_draft() calls this exactly ONCE and
    updates the in-memory counts itself as picks are made (a 224-pick,
    7-round draft doing 224 individual roster-count queries measured as
    the real, disclosed reason this needed a two-line fix during this
    chunk's own live verification -- same class of perf issue as the
    Dashboard's real 46s+ load, ROADMAP.md Sec2d-B's own precedent).
    Deliberately simpler than roster_strength.py's own quota-minimums
    table (tuned for the Roster page's "below quota" badges
    specifically); this just needs a real relative ranking for the
    greedy draft AI, not an absolute quota check."""
    from app.core.db import get_session
    from sqlmodel import select

    counts: dict[str, dict[str, int]] = {}
    with get_session() as s:
        for p in s.exec(select(Player).where(Player.team_abbr.is_not(None))):
            team_counts = counts.setdefault(p.team_abbr, {group: 0 for group in GROUP_POSITIONS})
            team_counts[_group_for(p.position)] += 1
    return counts


# Roughly the league's real average per-team count per group (measured off
# the imported rosters, 2026-09-14: QB 3.0, RB 5.1, WR 6.6, TE 4.2, OL 10.8,
# DL 11.9, LB 6.0, CB 7.0, S 5.3, K 1.2, P 1.0). A need is how far a team is
# BELOW its typical depth at a group, not its raw count -- ranking raw counts
# (the original rule) made K and P, which every team carries exactly one
# of, the two "scarcest" groups on every roster in the league, so every
# team treated a kicker and a punter as a top-3 need with its first pick
# (Brian's report: a K at #2 and a P at #5).
GROUP_ROSTER_TARGETS: dict[str, float] = {
    "QB": 3, "RB": 5, "WR": 6.5, "TE": 4, "OL": 10.5, "DL": 11.5,
    "LB": 6, "CB": 7, "S": 5, "K": 1, "P": 1,
}


def _needs_from_counts(counts: dict[str, int]) -> list[str]:
    return sorted(GROUP_POSITIONS, key=lambda g: counts.get(g, 0) / GROUP_ROSTER_TARGETS[g])


# ---------------------------------------------------------------------------
# Positional draft value (Brian's report, 2026-09-14: "A K and P were taken
# in the first 5 picks"). ADDED on top of a prospect's (perceived) overall
# when ranking who to take -- never replaces it, and never touches the
# prospect's real OVR. Real NFL teams pay a premium for passers, pass
# rushers, blindside tackles and corners, and almost never spend a Day 1-2
# pick on a specialist; specialists here also carry an inflated OVR scale
# (their profile is two +10-biased kicking attributes), which the heavy
# discount absorbs.
# ---------------------------------------------------------------------------
POSITION_DRAFT_VALUE: dict[Position, float] = {
    Position.QB: 8.0, Position.EDGE: 6.0, Position.T: 6.0, Position.CB: 5.0,
    Position.WR: 2.0, Position.DT: 2.0, Position.HB: 1.0, Position.S: 1.0, Position.G: 1.0, Position.C: 1.0,
    Position.TE: 0.0, Position.LB: 0.0, Position.FB: -4.0,
    Position.K: -25.0, Position.P: -25.0,
}
SPECIALIST_POSITIONS = (Position.K, Position.P)
SPECIALIST_EARLIEST_ROUND = 5      # no K/P is ever taken before this round
SPECIALISTS_MAX_PER_ROUND = 2      # K+P combined, per round, league-wide
NEED_BONUS = (5.0, 3.0, 2.0)       # OVR-point bonus for a team's 1st/2nd/3rd scarcest group


def draft_value(prospect: ProspectDraft, evaluated_overall: float | None = None) -> float:
    """The ranking score a front office drafts by: the prospect's overall
    (or a team's own noisy read of it) plus that position's draft value."""
    base = float(prospect.overall_rating) if evaluated_overall is None else evaluated_overall
    return base + POSITION_DRAFT_VALUE.get(prospect.position, 0.0)


def specialist_allowed(round_num: int | None, specialists_taken_this_round: int) -> bool:
    if round_num is None:
        return True
    return round_num >= SPECIALIST_EARLIEST_ROUND and specialists_taken_this_round < SPECIALISTS_MAX_PER_ROUND


def projected_rounds(prospects: list[ProspectDraft], rounds: int = ROUNDS, teams: int = 32) -> dict[int, int | None]:
    """A consensus (noise-free, need-free) projection of where each prospect
    goes, ranked by the same draft_value() the AI drafts by: rank / 32,
    rounded up. None = projected undrafted. Specialists are never projected
    earlier than SPECIALIST_EARLIEST_ROUND, matching the AI's hard rule."""
    ranked = sorted(prospects, key=lambda p: (-draft_value(p), p.index))
    out: dict[int, int | None] = {}
    for rank, p in enumerate(ranked):
        rnd = rank // teams + 1
        if p.position in SPECIALIST_POSITIONS:
            rnd = max(rnd, SPECIALIST_EARLIEST_ROUND)
        out[p.index] = rnd if rnd <= rounds else None
    return out


def _choose_prospect(remaining: list[ProspectDraft], needs: list[str], round_num: int | None,
                     specialists_taken_this_round: int, evaluate) -> ProspectDraft:
    """Shared by simulate_draft() and resolve_one_pick(): best draft_value()
    plus a need bonus for the team's top needs. K/P are removed from
    consideration entirely before SPECIALIST_EARLIEST_ROUND or once this
    round's specialist quota is used -- a hard rule, not just a score
    penalty, so a team whose only kicker retired still waits.

    Needs used to be a hard FILTER (only the top-3 need groups were even
    considered). Kept as a filter, positional value could never matter
    across groups: a team whose top needs were WR/OL/DL would pass on an
    elite QB or CB every time, and in a league where most rosters share
    the same shallowest groups whole first rounds went WR/G/C. A need is
    now a bonus on top of the value score instead (NEED_BONUS, scarcest
    first), so real need still tilts close calls without overriding a
    clearly better prospect at a premium position."""
    if not specialist_allowed(round_num, specialists_taken_this_round):
        eligible = [p for p in remaining if p.position not in SPECIALIST_POSITIONS]
        remaining = eligible or remaining
    need_bonus = {group: NEED_BONUS[i] for i, group in enumerate(needs[:len(NEED_BONUS)])}
    return max(remaining, key=lambda p: (draft_value(p, evaluate(p)) + need_bonus.get(p.group, 0.0), -p.index))


# ---------------------------------------------------------------------------
# R13 Sec 5.3: Scouting focus -> per-team draft-evaluation noise. The real
# prospect (generated above) is NEVER touched -- only what a team's OWN pick
# decision is made FROM. A team with no Scouting-focused staff evaluates
# every prospect through MAX_SCOUTING_NOISE of random error; investing
# Scouting-focused coaches (role-tiered, more coaches stacking with
# diminishing returns -- Brian's own explicit design) shrinks that toward
# MIN_SCOUTING_NOISE, never all the way to zero (real NFL scouting is never
# perfect either).
# ---------------------------------------------------------------------------
MAX_SCOUTING_NOISE = 12.0   # stddev, overall_rating units -- nobody focused on Scouting
MIN_SCOUTING_NOISE = 3.0    # stddev floor -- scouting uncertainty never fully disappears
SCOUTING_STRENGTH_K = 40.0  # saturating-curve constant: strength / (strength + K) -> noise-reduction fraction

def _scouting_role_weight(role: CoachRole) -> float:
    """Role-tier weight, reusing coaching.py's own R13 three-tier scheme
    (HC > coordinator > assistant) rather than inventing a second one."""
    from app.engine import coaching
    if role is CoachRole.HC:
        return coaching.HC_TIER_WEIGHT
    if role is CoachRole.AC:
        return coaching.ASSISTANT_TIER_WEIGHT
    return coaching.COORDINATOR_TIER_WEIGHT


def team_scouting_strength(team_abbr: str) -> float:
    """Role-tiered SUM (not average -- more coaches focusing on Scouting
    keeps helping, with diminishing returns applied downstream by
    perceived_overall()'s saturating curve) of `overall` across every coach
    on `team_abbr` whose focus_area is Scouting. 0.0 if nobody is (the
    common case, day one -- R13 Sec 4 has no real default assignee for
    Scouting) or if this database has no coach system at all."""
    from app.services import coach_store
    if not coach_store.has_coaches():
        return 0.0
    return sum(
        _scouting_role_weight(CoachRole(c.role)) * c.overall
        for c in coach_store.staff_for(team_abbr) if c.focus_area == FOCUS_SCOUTING
    )


def perceived_overall(prospect: ProspectDraft, team_abbr: str, league_seed: int, season_number: int) -> float:
    """This team's OWN noisy evaluation of `prospect`, used ONLY to decide
    who they draft -- the real prospect (and the Player row it becomes once
    drafted) always keeps its true, real attributes. Deterministic: the same
    (league_seed, season_number, team_abbr, prospect.index) always produces
    the same perceived value, so re-running simulate_draft() with the same
    inputs reproduces the same picks."""
    from app.services import coach_store
    if not coach_store.has_coaches():
        # No coach system in this database at all -- simulate exactly as
        # this engine did before R13, same backward-compatibility guarantee
        # every other coaching hook here already has.
        return float(prospect.overall_rating)

    strength = team_scouting_strength(team_abbr)
    reduction = strength / (strength + SCOUTING_STRENGTH_K)
    noise_stddev = MAX_SCOUTING_NOISE - reduction * (MAX_SCOUTING_NOISE - MIN_SCOUTING_NOISE)
    seed = stable_seed(league_seed, season_number, "scouting_noise", team_abbr, prospect.index)
    rng = RNG.with_seed(seed)
    return prospect.overall_rating + rng.gauss(0, noise_stddev)


def simulate_draft(prospects: list[ProspectDraft], order: list[str], league_seed: int, season_number: int,
                   rounds: int = ROUNDS) -> DraftResult:
    """Greedy, deterministic, need-aware: on the clock, a team drafts the
    prospect with the best PERCEIVED overall plus positional draft value
    plus a need bonus for its 3 scarcest position groups (using a real live
    roster count, fetched once up front and updated in memory as this
    function's own picks land -- see _all_teams_group_counts()'s docstring
    for why), with K/P held out until round 5 (_choose_prospect(); changed
    2026-09-14 from a hard top-3-needs filter on raw OVR).
    "Perceived" (R13 Sec 5.3) is the prospect's true overall_rating plus
    that team's own Scouting-investment-scaled noise -- the drafted
    Player row itself still gets the prospect's real, true attributes;
    only the DECISION of who to take was made off noisy information. The
    only DB access is the up-front roster-count query, one coach-staff
    lookup per team (cached by coach_store), and one up-front pick-
    ownership read for the whole season (app/services/draft_pick_store.py,
    Sec 8.5 -- a traded pick's CURRENT OWNER makes the pick, not the
    original team `order` names; that original team's real record still
    earned the SLOT, unchanged); everything else here is a pure
    computation over `prospects`/`order`, so determinism is exhaustively
    unit-testable without needing to mock the database."""
    from app.services import draft_pick_store

    remaining = {p.index: p for p in prospects}
    counts = _all_teams_group_counts()
    owners = draft_pick_store.owners_for_season(season_number)
    picks: list[DraftPickResult] = []
    overall_pick = 1
    for rnd in range(1, rounds + 1):
        specialists_this_round = 0
        for original_team_abbr in order:
            if not remaining:
                break
            picking_team = owners.get((rnd, original_team_abbr), original_team_abbr)
            team_counts = counts.setdefault(picking_team, {group: 0 for group in GROUP_POSITIONS})
            needs = _needs_from_counts(team_counts)[:3]
            best = _choose_prospect(
                list(remaining.values()), needs, rnd, specialists_this_round,
                lambda p, team=picking_team: perceived_overall(p, team, league_seed, season_number),
            )
            picks.append(DraftPickResult(round=rnd, overall_pick=overall_pick, team_abbr=picking_team, prospect_index=best.index))
            del remaining[best.index]
            team_counts[best.group] += 1
            if best.position in SPECIALIST_POSITIONS:
                specialists_this_round += 1
            overall_pick += 1
    return DraftResult(order=order, picks=picks, undrafted_indexes=list(remaining.keys()))


# ---------------------------------------------------------------------------
# Live, pick-by-pick draft (Brian's ask, 2026-09-13) -- the exact same
# needs-aware greedy logic as simulate_draft() above, factored so ONE
# slot can resolve per real HTTP request instead of the whole draft
# resolving inside one function call. See app/services/
# draft_progress_store.py's own docstring for how a slot's real position
# in the sequence survives across those separate requests.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DraftSlot:
    round: int
    overall_pick: int
    team_abbr: str


def draft_slots(order: list[str], season_number: int | None = None, rounds: int = ROUNDS) -> list[DraftSlot]:
    """The fixed, real sequence of (round, overall_pick, team) slots a
    draft resolves in -- a pure function of `order` (compute_draft_
    order()'s real standings-based result) and `rounds`.

    **Bug fix, 2026-09-14**: this function used to hand back `order`'s
    ORIGINAL teams unconditionally, exactly like simulate_draft() did
    before R15 -- but simulate_draft() itself was fixed to resolve real
    pick ownership (app/services/draft_pick_store.py) when R15 shipped,
    and this live, pick-by-pick sibling (added the same day, "rebuilt
    2026-09-13") never got the same fix. Result: a real GM Desk pick
    trade had zero effect on who actually went on the clock in the live
    draft -- season_state.py's advance_draft_pick() credits `slot.
    team_abbr` straight to the drafted Player row, so this wasn't a
    display-only bug. `season_number` (the draft's own season number,
    e.g. draft_progress_store/draft_class_store's `next_number`) now
    resolves each slot's CURRENT owner the exact same way simulate_
    draft() already does -- omitted only by this function's own existing
    unit tests that predate trading and don't care about it."""
    owners: dict[tuple[int, str], str] = {}
    if season_number is not None:
        from app.services import draft_pick_store
        owners = draft_pick_store.owners_for_season(season_number)
    slots: list[DraftSlot] = []
    overall_pick = 1
    for rnd in range(1, rounds + 1):
        for original_team_abbr in order:
            picking_team = owners.get((rnd, original_team_abbr), original_team_abbr)
            slots.append(DraftSlot(round=rnd, overall_pick=overall_pick, team_abbr=picking_team))
            overall_pick += 1
    return slots


def resolve_one_pick(
    prospects_by_index: dict[int, ProspectDraft], drafted_indexes: set[int],
    team_abbr: str, group_counts: dict[str, dict[str, int]],
    round_num: int | None = None, specialists_taken_this_round: int = 0,
    league_seed: int | None = None, season_number: int | None = None,
) -> ProspectDraft:
    """The exact same needs-aware greedy choice simulate_draft() makes
    for one team's turn (see that function's own docstring), extracted
    so the live pick-by-pick engine can call it for one slot at a time.
    `group_counts` is mutated in place (the picked prospect's own group
    incremented) so the next call for this same team sees an accurate
    need, same as simulate_draft()'s own in-memory bookkeeping -- the
    caller owns this dict across calls (typically seeded once from
    _all_teams_group_counts() at the start of a live draft).

    `round_num`/`specialists_taken_this_round` enforce the K/P hard rule
    (see _choose_prospect); `league_seed`/`season_number`, when given, make
    the choice off this team's own Scouting-noise read (perceived_overall)
    exactly like simulate_draft() -- omitted, the true OVR is used."""
    team_counts = group_counts.setdefault(team_abbr, {group: 0 for group in GROUP_POSITIONS})
    needs = _needs_from_counts(team_counts)[:3]
    remaining = [p for i, p in prospects_by_index.items() if i not in drafted_indexes]
    if league_seed is not None and season_number is not None:
        def evaluate(p):
            return perceived_overall(p, team_abbr, league_seed, season_number)
    else:
        def evaluate(p):
            return float(p.overall_rating)
    best = _choose_prospect(remaining, needs, round_num, specialists_taken_this_round, evaluate)
    team_counts[best.group] += 1
    return best


def apply_single_pick_to_db(prospect: ProspectDraft, team_abbr: str, overall_pick: int, round_num: int,
                             league_seed: int, season_number: int) -> dict:
    """Writes ONE drafted prospect as a real Player row the moment its
    pick resolves -- the live pick-by-pick engine's own unit of work.
    Same real rookie-scale contract terms apply_draft_to_db() already
    uses, just for a single prospect instead of a whole DraftResult's
    worth at once. Returns the same pick-dict shape draft_store.py's
    `picks` list uses, ready for draft_progress_store.record_pick()."""
    from app.core.db import get_session

    salary = rookie_scale_aav(overall_pick, season_number)
    player = _prospect_to_player(prospect, league_seed, season_number, team_abbr, salary, contract_years_remaining=4,
                                 draft_round=round_num, overall_pick=overall_pick)
    # player_id/full_name are both deterministic and known BEFORE the
    # insert (_player_id_for()/prospect's own name) -- read them off the
    # object before commit, not after: a SQLAlchemy Session expires an
    # object's attributes on commit by default, and this function's own
    # `with get_session()` block has already closed by the time the
    # caller would otherwise touch `player` again, which raised a real
    # DetachedInstanceError the first time this ran live (caught by this
    # feature's own test suite, not by inspection).
    player_id, full_name = player.player_id, player.full_name
    with get_session() as s:
        s.add(player)
        s.commit()
    return {
        "round": round_num, "overall_pick": overall_pick, "team_abbr": team_abbr,
        "player_id": player_id, "name": full_name, "position": prospect.position.value,
        "college": prospect.college, "overall_rating": prospect.overall_rating,
    }


def finalize_undrafted_to_db(prospects_by_index: dict[int, ProspectDraft], drafted_indexes: set[int],
                              league_seed: int, season_number: int) -> int:
    """Once every slot has resolved, whoever's left in the class becomes
    a real free agent -- the exact same treatment apply_draft_to_db()
    already gives undrafted prospects (real Player row, team_abbr=None,
    league-minimum 1-year deal, registered in undrafted_pool), extracted
    so the live pick-by-pick engine can call it once at the draft's real
    end instead of inside one atomic function. Returns the count."""
    from app.core.db import get_session
    from app.services import undrafted_pool

    undrafted_player_ids: list[str] = []
    with get_session() as s:
        for index, prospect in prospects_by_index.items():
            if index in drafted_indexes:
                continue
            player = _prospect_to_player(
                prospect, league_seed, season_number, None,
                salary=LEAGUE_MINIMUM_BASE, contract_years_remaining=1,
            )
            s.add(player)
            undrafted_player_ids.append(player.player_id)
        s.commit()
    undrafted_pool.add_undrafted(undrafted_player_ids)
    return len(undrafted_player_ids)


# ---------------------------------------------------------------------------
# Rookie-scale AAV (Sec 8.1, real-dollar anchors, scaled by THIS project's
# real SALARY_CAP_BASE -- see module docstring for why $302M isn't used)
# ---------------------------------------------------------------------------

_ROOKIE_SCALE_ANCHORS = [  # (overall_pick_upper_bound, base_aav)
    (1, 13_640_000), (2, 13_030_000), (10, 7_400_000), (32, 6_930_000),
    (64, 3_230_000), (100, 1_450_000), (10_000, 1_150_000),
]
LEAGUE_MINIMUM_BASE = 885_000


def rookie_scale_aav(overall_pick: int, season_number: int) -> int:
    from app.engine.contracts import salary_cap_for_season, SALARY_CAP_BASE

    base = _ROOKIE_SCALE_ANCHORS[-1][1]
    prev_pick, prev_aav = 0, _ROOKIE_SCALE_ANCHORS[0][1]
    for upper, aav in _ROOKIE_SCALE_ANCHORS:
        if overall_pick <= upper:
            if upper == prev_pick:
                base = aav
            else:
                frac = (overall_pick - prev_pick) / (upper - prev_pick)
                base = prev_aav + frac * (aav - prev_aav)
            break
        prev_pick, prev_aav = upper, aav
    growth = salary_cap_for_season(season_number) / SALARY_CAP_BASE
    return round(base * growth)


def _player_id_for(league_seed: int, season_number: int, prospect_index: int) -> str:
    """Deterministic, not a random UUID (GDD Sec 1.3) -- collision-safe in
    practice via the seeded numeric suffix, same spirit as injuries.py's
    own deterministic injury_id."""
    tag = stable_seed(league_seed, season_number, prospect_index) % 1_000_000
    return f"draft_{season_number}_{prospect_index:04d}_{tag:06d}"


def _prospect_to_player(p: ProspectDraft, league_seed: int, season_number: int, team_abbr: str | None,
                         salary: int, contract_years_remaining: int,
                         draft_round: int | None = None, overall_pick: int | None = None) -> Player:
    from app.config import season_year

    kwargs = dict(p.attrs)
    if team_abbr is not None and overall_pick is not None:
        # Acquisition tracking (2026-09-14): a drafted rookie's origin is
        # the draft itself. acquisition_season is the draft's own calendar
        # year -- `season_number` here is the season the class is FOR (the
        # Draft page's "2027 NFL Draft" for season_year(25)). Undrafted
        # prospects stay None until someone actually signs them.
        kwargs.update(
            acquisition_type="Draft", acquisition_season=season_year(season_number),
            acquisition_round=draft_round, acquisition_pick=overall_pick,
        )
    return Player(
        player_id=_player_id_for(league_seed, season_number, p.index),
        first_name=p.first_name, last_name=p.last_name, position=p.position, team_abbr=team_abbr,
        jersey_number=0, age=p.age, height_inches=p.height_inches, weight_lbs=p.weight_lbs,
        college=p.college, years_pro=0, overall_rating=p.overall_rating, potential=p.potential,
        morale=75, salary=salary, signing_bonus=0, guaranteed_money=0,
        contract_years_remaining=contract_years_remaining,
        **kwargs,
    )


def apply_draft_to_db(prospects: list[ProspectDraft], result: DraftResult, league_seed: int, season_number: int) -> dict:
    """The one impure step: drafted prospects become real Player rows on
    their new team with a real rookie-scale contract (4-year, Sec 8.1);
    undrafted prospects become real Player rows too, as genuine free
    agents (team_abbr=None) -- reusing the EXISTING free-agency
    infrastructure (Roster page browsing, Sign routes, contract
    negotiation) instead of a second, parallel "UndraftedRookie" system,
    tracked for the real 3-year expiration window via
    app.services.undrafted_pool (Tier-1-only cleanup, see module
    docstring). Returns a summary dict for the caller to log/store."""
    from app.core.db import get_session
    from app.services import undrafted_pool, draft_store

    by_index = {p.index: p for p in prospects}
    drafted_player_ids: list[str] = []
    picks_for_store = []
    with get_session() as s:
        for pick in result.picks:
            prospect = by_index[pick.prospect_index]
            salary = rookie_scale_aav(pick.overall_pick, season_number)
            player = _prospect_to_player(prospect, league_seed, season_number, pick.team_abbr, salary, contract_years_remaining=4,
                                         draft_round=pick.round, overall_pick=pick.overall_pick)
            s.add(player)
            drafted_player_ids.append(player.player_id)
            picks_for_store.append({
                "round": pick.round, "overall_pick": pick.overall_pick, "team_abbr": pick.team_abbr,
                "player_id": player.player_id, "name": player.full_name, "position": prospect.position.value,
                "college": prospect.college, "overall_rating": prospect.overall_rating,
            })

        undrafted_player_ids: list[str] = []
        for index in result.undrafted_indexes:
            prospect = by_index[index]
            player = _prospect_to_player(
                prospect, league_seed, season_number, None,
                salary=LEAGUE_MINIMUM_BASE, contract_years_remaining=1,
            )
            s.add(player)
            undrafted_player_ids.append(player.player_id)
        s.commit()

    undrafted_pool.add_undrafted(undrafted_player_ids)
    draft_store.record_draft(season_number, result.order, picks_for_store, len(undrafted_player_ids))
    return {"drafted": len(drafted_player_ids), "undrafted": len(undrafted_player_ids)}


def run_draft_for_season(season, season_number: int) -> dict:
    """Orchestrates the whole real pipeline for one season's draft --
    generate the class, compute the real order, simulate every pick
    need-aware (ownership-aware since Draft-Pick Trading, Sec 8.5 --
    simulate_draft() itself resolves each slot's CURRENT owner), write
    real Player rows. Called from season_state.start_new_season() (see
    that function's own call site comment for exactly where in the
    offseason calendar this runs)."""
    from app.services import draft_pick_store

    prospects = generate_draft_class(season.league_seed, season_number)
    order = compute_draft_order(season, season.league_seed, season_number)
    result = simulate_draft(prospects, order, season.league_seed, season_number)
    summary = apply_draft_to_db(prospects, result, season.league_seed, season_number)
    # This season's picks are now resolved -- no longer a tradeable
    # future asset (Sec 8.5's "current draft" window has just closed).
    draft_pick_store.consume_season(season_number)
    return summary


# ---------------------------------------------------------------------------
# Supplemental undrafted free agents (Brian's ask, 2026-09-14: "I want there
# to always be enough free agents to fill holes on rosters. That should
# happen naturally with undrafted free agents.")
# ---------------------------------------------------------------------------

# Realistic street-free-agent quality: below a typical rostered starter
# (league position averages sit in the 70s), still playable depth.
SUPPLEMENTAL_UDFA_OVR_RANGE = (45, 62)


def supplemental_udfa_id(season_number: int, position: Position, ordinal: int, league_seed: int) -> str:
    """Deterministic id, distinct from _player_id_for()'s draft_ namespace
    so a supplemental signing never collides with a real class member."""
    tag = stable_seed(league_seed, "udfa", season_number, position.value, ordinal) % 1_000_000
    return f"udfa_{season_number}_{position.value}_{ordinal:03d}_{tag:06d}"


def generate_supplemental_udfa(position: Position, ordinal: int, league_seed: int, season_number: int) -> ProspectDraft:
    """One extra undrafted rookie at `position`, built with the same
    attribute pipeline as _generate_one_prospect() (POSITION_PROFILES
    key attributes + duller off-profile attributes, profile-weighted
    overall) so ratings stay internally coherent -- only the talent draw
    is lower, targeting SUPPLEMENTAL_UDFA_OVR_RANGE. The overall is
    shifted into range by moving every attribute together, not by
    overwriting overall_rating alone, so the Player Card's attributes
    still explain the number."""
    rng = RNG.with_seed(stable_seed(league_seed, "udfa", season_number, position.value, ordinal))
    lo, hi = SUPPLEMENTAL_UDFA_OVR_RANGE
    target = rng.uniform(lo, hi)
    profile = POSITION_PROFILES.get(position, {})
    base_talent = target - 5  # profile biases average roughly +5 above base_talent
    attrs: dict[str, int] = {}
    for name in ALL_ATTR_FIELDS:
        bias = profile[name][1] if name in profile else -15
        attrs[name] = _clamp(base_talent + bias + rng.gauss(0, 8))

    def _overall(a: dict[str, int]) -> int:
        if profile:
            total_w = sum(w for w, _ in profile.values())
            return _clamp(sum(a[n] * w for n, (w, _) in profile.items()) / total_w)
        return _clamp(sum(a.values()) / len(a))

    overall = _overall(attrs)
    shift = max(lo, min(hi, round(target))) - overall
    if shift:
        attrs = {n: _clamp(v + shift) for n, v in attrs.items()}
        overall = max(lo, min(hi, _overall(attrs)))

    group = _group_for(position)
    (h_min, h_max), (w_min, w_max) = _HEIGHT_WEIGHT_BY_GROUP[group]
    return ProspectDraft(
        index=ordinal, first_name=rng.choice(_FIRST_NAMES), last_name=rng.choice(_LAST_NAMES),
        position=position, college=rng.choice(_COLLEGES), age=rng.r().randint(22, 24),
        height_inches=rng.r().randint(h_min, h_max), weight_lbs=rng.r().randint(w_min, w_max),
        overall_rating=overall, potential=_clamp(overall + rng.uniform(0, 12)),
        attrs=attrs, draft_grade=_draft_grade(overall), group=group,
    )


def supplemental_udfa_player(position: Position, ordinal: int, league_seed: int, season_number: int) -> Player:
    """generate_supplemental_udfa() as a real free-agent Player row
    (team_abbr=None) on the same league-minimum 1-year terms
    finalize_undrafted_to_db() gives a real undrafted prospect, grown with
    the cap the same way rookie_scale_aav() grows its anchors."""
    from app.engine.contracts import salary_cap_for_season, SALARY_CAP_BASE

    prospect = generate_supplemental_udfa(position, ordinal, league_seed, season_number)
    salary = round(LEAGUE_MINIMUM_BASE * salary_cap_for_season(season_number) / SALARY_CAP_BASE)
    player = _prospect_to_player(prospect, league_seed, season_number, None, salary=salary, contract_years_remaining=1)
    player.player_id = supplemental_udfa_id(season_number, position, ordinal, league_seed)
    return player
