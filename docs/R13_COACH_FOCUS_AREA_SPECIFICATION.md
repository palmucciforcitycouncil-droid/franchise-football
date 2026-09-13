# R13: Coach Focus Areas

Real spec, written 2026-09-13 (design-only session, nothing built yet). Origin:
Brian saw the Figma source's per-coach "Focus Area" dropdown (`OF Gameplan` /
`DF Gameplan` / `Training` / `Development` / `Scouting` / `Special Teams Work` /
`2 Min Offense`) and asked for it to become a real, consumed system instead of
staying the disclosed no-op R3c cut it as (ROADMAP.md §4c: "the source's
per-coach 'Focus Area' dropdown — nothing in the engine reads a focus area, so
it would be a control that visibly does nothing").

## 1. Overview

`app/engine/coaching.py` already reduces one team's staff into a `StaffEffect`
(pass/blitz bias, dev multipliers, penalty rate, FG range) consumed every game.
Today, *who* contributes to *which* number is hardcoded by role: the OC's
tendency sliders drive offense, the DC's drive defense, and every coach's
`player_dev_offense`/`player_dev_defense` gets pooled into development
regardless of what that coach actually does. Focus Area replaces that
hardcoding with a real per-coach choice: each coach picks ONE bucket their
ratings feed into, and `build_staff_effect()` groups the whole staff by that
choice instead of by role.

**Design principle (settled, do not reopen): Focus Area reallocates an
existing coach's influence — it does not add power.** A coach not focused on
a bucket contributes nothing to it. This is deliberate: `coaching.py`'s own
`LeagueBaseline` mechanism exists specifically so a staff can only move its
own team relative to the league, never move the league — a Focus Area system
that granted bonus multipliers for "specializing" would break that guarantee
and invalidate `tests/test_stat_realism.py`'s calibration. Reallocation keeps
the league mean fixed by construction: swap where an existing number lands,
never invent a new one.

## 2. Settled Decisions (Do Not Reopen)

- **Seven focus areas ship in v1**: OF Gameplan, DF Gameplan, **Balanced
  Gameplan** (new — added 2026-09-13, see below), Development, Special Teams
  Work, Training, Scouting.
- **`2 Min Offense` is cut entirely**, not disclosed-as-a-stub. Same
  precedent as deleting `clock_management`/`challenge_sense` from `Coach`
  outright (ROADMAP.md §4c-addendum): this engine has no clock/2-minute-drill
  model anywhere, so there is no signal this option could ever move. A rating
  or option with no consumer shouldn't exist on screen at all.
- **The Head Coach picks freely**, same single dropdown and same rules as
  every other coach — competing with their own OC/DC/ST/assistants for a
  bucket, not a privileged role-agnostic fallback. An HC who sets focus to
  Development contributes ZERO to gameplan tendencies.
- **Balanced Gameplan** (Brian's own resolution to the HC single-side
  problem below): a coach focused here contributes to BOTH OF Gameplan and DF
  Gameplan simultaneously, at a REDUCED weight on each — deliberately smaller
  impact per side than fully focusing on just one, in exchange for touching
  both. See §5.1 for the split mechanic. This is now the Head Coach's
  migration default (§4) instead of an arbitrary single-side pick.
- **Training reuses `Coach.motivation_chemistry`** — currently a real,
  already-imported/generated field with NO sim consumer at all (it only
  feeds the `overall` display composite; `coaching.py` never reads it). This
  closes an existing disclosed gap rather than opening a new rating field.
- **Scouting is a new mechanic** (not a StaffEffect reshuffle): it reduces
  the noise in a team's OWN draft-evaluation, not the underlying prospect's
  real generated attributes. See §5.3.
- **Stacking rule (Scouting specifically, and general to the reallocation
  model): more coaches focusing on the same bucket helps, with diminishing
  returns, weighted by role** — Head Coach > Coordinator (OC/DC/ST) >
  Assistant. This generalizes the existing `COORDINATOR_WEIGHT`/
  `HEAD_COACH_WEIGHT` (0.6/0.4) two-tier blend into three tiers for buckets
  any of HC/coordinator/assistant can realistically all pile into
  (Development, Training, Scouting); OF/DF/Balanced Gameplan and Special
  Teams Work stay effectively two-tier in practice since only the relevant
  coordinator and HC are likely to focus there.
- **No artificial stacking cap, by design (confirmed with Brian).** A team
  that parks its whole staff on Scouting pays for it automatically through
  opportunity cost, not a hardcoded limit: every coach on Scouting is a coach
  NOT contributing to OF/DF Gameplan or Development, and the diminishing-
  returns curve (§5.3) means the 5th Scouting-focused assistant helps far
  less than the 1st anyway. A real, correct trade-off, not a loophole to
  patch.
- **AI teams DO dynamically reassign focus, every offseason** (reversing
  this spec's original v1 cut — Brian's explicit call, 2026-09-13: "AI should
  decide focus, it should be dynamic"). Scoped to the ASSISTANT tier only —
  see §7 for why HC/OC/DC/ST stay pinned to their natural lane and the real
  signals the AI policy uses.
- **Backward compatibility to the CURRENT live save is explicitly NOT a
  constraint** (Brian, 2026-09-13: "I do not care about current saves.
  Everything is just testing. It's okay to wipe it."). The defaults in §4 are
  chosen because they're sensible starting points for any NEW save going
  forward, not because they need to reproduce today's exact numbers for
  Brian's real in-progress franchise — no migration-day calibration
  before/after comparison is required as a gate before shipping.

## 3. Data Model

`app/models/coach.py` gets one new column:

```python
FOCUS_OF_GAMEPLAN = "OF Gameplan"
FOCUS_DF_GAMEPLAN = "DF Gameplan"
FOCUS_BALANCED_GAMEPLAN = "Balanced Gameplan"
FOCUS_DEVELOPMENT = "Development"
FOCUS_SPECIAL_TEAMS = "Special Teams Work"
FOCUS_TRAINING = "Training"
FOCUS_SCOUTING = "Scouting"
FOCUS_AREAS = [
    FOCUS_OF_GAMEPLAN, FOCUS_DF_GAMEPLAN, FOCUS_BALANCED_GAMEPLAN, FOCUS_DEVELOPMENT,
    FOCUS_SPECIAL_TEAMS, FOCUS_TRAINING, FOCUS_SCOUTING,
]

class Coach(SQLModel, table=True):
    ...
    focus_area: str = FOCUS_DEVELOPMENT  # see §4 for the real per-role default
```

Migration: `scripts/migrate_add_r13_focus_area.py`, same convention as
`migrate_add_r3d_coach_fields.py` (SQLite `ALTER TABLE ADD COLUMN` with a
real default for every existing row, timestamped `.bak-*` snapshot first,
safe to re-run). `TEMPLATE_DB_PATH`/`data/franchise_football.db` both need
this migration run once.

## 4. Default Assignment

Brian has explicitly waived exact backward compatibility with the current
live save (§2: "everything is just testing, okay to wipe it") — so these
defaults are chosen as sensible starting points for any save going forward,
not because they must reproduce today's precise numbers. Applied by the
migration script, keyed off `Coach.role`/`Coach.specialty`:

| Role / specialty | Default focus_area | Why |
|---|---|---|
| OC | OF Gameplan | The natural lane for the role; also what §7's AI policy pins them to permanently. |
| DC | DF Gameplan | Same, defense. |
| ST | Special Teams Work | ST is already the sole `special_teams_focus` contributor today. |
| HC | **Balanced Gameplan** | Resolves the single-side problem an earlier draft of this spec had (defaulting HC to one side silently zeroed their contribution to the other) — a real design fix, not just a compatibility patch. See §5.1 for the split mechanic. |
| AC, specialty matches `special teams` (case-insensitive substring) | Special Teams Work | Real seed title says so. |
| AC, specialty matches `strength`/`conditioning` | Training | Real seed title says so; also the closest real-title match to "keeps players healthy." |
| AC, everything else (position coaches: QB/WR/OL/DL/LB/DB/etc.) | Development | Matches today's existing pooling of every assistant into `dev_off_pool`/`dev_def_pool` uniformly. Also §7's AI policy dynamically moves these off Development over time based on real team need. |

**Scouting has no real default assignee.** Unlike the other six, nothing
about today's engine or the real seed data implies "this coach already does
scouting" — the real seed lists on-field coaching staff, not a front-office
scouting department. Confirm during implementation whether any of the 433
real specialty tags plausibly map to a scouting-flavored role (e.g. "Player
Personnel", "Pro Scout") via a real grep of
`data/raw/coaches/Comprehensive NFL Coaching Staff Directory with Salaries
2026.md`; if none exist (expected), every team starts with ZERO coaches
focused on Scouting at migration time — §7's AI policy is what actually
populates it over time for AI teams from there.

## 5. Sim Integration

### 5.1 OF Gameplan / DF Gameplan / Development / Special Teams Work

`build_staff_effect()` (`app/engine/coaching.py`) changes from role-based
lookup (`by_role.get(CoachRole.OC)`, etc.) to focus-based grouping: partition
the whole staff (HC + OC + DC + ST + every AC) by `coach.focus_area`, then for
each of these four buckets, blend the coaches in that bucket with role-tiered
weights (HC weight, coordinator weight, assistant weight — extending
`COORDINATOR_WEIGHT`/`HEAD_COACH_WEIGHT` to the three-tier
`HC_TIER_WEIGHT`/`COORDINATOR_TIER_WEIGHT`/`ASSISTANT_TIER_WEIGHT`, values TBD
during implementation). An empty bucket (nobody focused there) falls back to
the existing "no staff" neutral behavior — already handled by `_blend()`'s
current fallback path, no new code needed for that case.

**Balanced Gameplan** is the one bucket that isn't a clean partition: a coach
focused here contributes to BOTH the OF Gameplan and DF Gameplan buckets
simultaneously, at `BALANCE_SPLIT_FACTOR` (TBD, start at 0.5 — see §9) times
their normal tier weight on EACH side, rather than their full tier weight on
one side. Concretely, for a Balanced-focused HC with `HC_TIER_WEIGHT = W`:
`0.5*W` flows into the OF Gameplan blend and `0.5*W` flows into the DF
Gameplan blend, so both sides get a real (if smaller than a fully-committed
coach's) contribution — this is Brian's own explicit design ("smaller impact
on each than a focus on OFF or DEF alone"), fixing the earlier draft's
single-side HC default outright rather than patching around it.

Every existing `StaffEffect` field/call site (`offense_pass_bias`,
`defense_blitz_bias`, `penalty_rate_multiplier`, `fg_range_bonus`, etc.) is
UNCHANGED — this section only changes how the four relevant inputs are
gathered, not what they feed into. `discipline` stays a fixed HC-only read
(§2: not everything becomes reallocatable — a program's discipline culture is
a leadership trait, not a delegable focus, and no real Figma option offered
"Discipline" as a pickable focus anyway).

### 5.2 Training → Injury System

New `StaffEffect` field: `injury_risk_multiplier: float = 1.0`. Computed from
the role-tiered blend of `motivation_chemistry` across every coach whose
`focus_area == FOCUS_TRAINING`, same `_slider()`/`LeagueBaseline` pattern as
`penalty_rate_multiplier` (a league-average Training investment lands on
exactly 1.0; better-than-average lowers it, worse raises it — bounded, TBD
constants during implementation, calibrated similarly to
`PENALTY_RATE_AT_ZERO_DISCIPLINE`/`PENALTY_RATE_AT_MAX_DISCIPLINE`).

`app/engine/injuries.py`'s `_proneness_multiplier(player)` gains a second
factor: `proneness_multiplier(player) * staff_effect.injury_risk_multiplier`
at the one call site inside `_no_injury_probability`'s caller
(`roll_injuries_for_week`). `motivation_chemistry`'s new `LeagueBaseline` pool
is the mean across every coach (same pool shape as `dev_offense`/`dev_defense`
today), NOT HC-only like `discipline` — Training can be any coach's focus,
including assistants, unlike discipline which is read off the HC specifically
regardless of focus.

### 5.3 Scouting → Draft Evaluation Noise

**This is new engine surface, not a StaffEffect reshuffle — the draft system
has no existing true-vs-perceived split to plug into (confirmed: prospect
attributes in `draft.py` generate once via `rng.gauss(...)` and are
immediately real; `simulate_draft()`'s greedy pick logic sorts by the
prospect's true `overall_rating` directly, with zero noise, for every team,
today).**

**The real prospect never changes.** `generate_draft_class()`/
`_generate_one_prospect()` are untouched — the class stays deterministic per
`(league_seed, season_number)` and fair (every team eventually sees the same
real prospects with the same real attributes once drafted). What changes is
only what a team's OWN pick decision is made FROM.

New function, `app/engine/draft.py`:

```python
def _team_scouting_strength(team_abbr: str) -> float:
    """Role-tiered, diminishing-returns sum of `overall` across every coach
    on `team_abbr` whose focus_area == FOCUS_SCOUTING. 0.0 if nobody is
    focused there (the common case, day one — see §4)."""

def perceived_overall(prospect: ProspectDraft, team_abbr: str, rng: RNG) -> float:
    """prospect.overall_rating + gauss(0, noise_stddev(_team_scouting_strength(team_abbr))).
    noise_stddev descends from MAX_SCOUTING_NOISE (nobody focused on Scouting)
    toward MIN_SCOUTING_NOISE (a floor — scouting uncertainty never fully
    disappears, matching the real NFL's own "draft busts happen to everyone"
    baseline) as scouting strength rises, via a saturating (not linear) curve
    so no realistic staff investment can zero it out."""
```

`simulate_draft()`'s greedy pick step changes from ranking remaining
prospects at a team's neediest group by `p.overall_rating` to ranking by
`perceived_overall(p, team_abbr, rng)` — computed fresh (seeded via
`stable_seed(league_seed, season_number, "scouting_noise", team_abbr,
prospect.index)`, so it's deterministic and independently unit-testable) at
the moment that team is on the clock. **The player that actually lands on the
roster keeps their true, real attributes** — only the DECISION of who to take
was made off noisy information. A weak-scouting team can reach for a player
who turns out worse than they thought, or pass on a real steal; a
strong-scouting team's picks track much closer to true best-available-for-need.
This is a real, visible emergent narrative (same spirit as R3d's own §12
"Emergent Narratives" section) — "Team X's scouting department keeps finding
diamonds in the 5th round" becomes a true, causally-real story instead of
flavor text.

Role-tiered weighting matches Brian's own stated design ("higher coach skill,
and more coaches focusing on it make a difference... HC focus is more
valuable than an assistant"): sum `role_weight * coach.overall` across every
Scouting-focused coach on that team (`coach.overall` chosen over a narrower
single rating since no dedicated "scouting ability" attribute exists anywhere
in this data — same reuse-what's-already-real principle as `motivation_
chemistry` for Training, just at the composite level since scouting acumen
isn't obviously any ONE of the six performance ratings), then pass that sum
through a saturating curve (e.g. `strength / (strength + K)`, `K` TBD) into
the noise-reduction fraction — sum, not average, so a bigger Scouting
department (HC + several assistants all focused there) keeps helping, with
the expected diminishing returns, rather than diluting toward a mean.

## 6. UI

Real Focus Area dropdown on `/staff` (currently explicitly omitted per
`app/templates/staff.html`'s own header comment — that comment gets deleted
along with the omission once this ships), matching the Figma source's control
placement but backed by a real route:

```
POST /staff/{team_abbr}/{coach_id}/focus   (Form: focus_area)
```

Same pattern as the existing `/staff/{team_abbr}/fire` and `/staff/{team_abbr}
/hire` R3d routes. Only valid for the user's own team's coaches (AI teams'
staffs keep their migration-assigned defaults forever, same as AI teams never
touching the Weekly Gameplan — no AI logic to intelligently reassign focus is
in scope for v1; see §7). Changing a focus_area must call `coaching.clear_
cache()` (the `StaffEffect` cache is keyed on the staff tuple, which doesn't
change when only a field ON an existing coach changes) so the next game
actually reflects it.

The existing "Trait Effects" panel (ROADMAP.md §4c's "renders the actual
StaffEffect numbers the sim is using right now") is the natural place to also
surface the new `injury_risk_multiplier` and a real "Scouting: -N% draft
noise" readout — same "prove it's doing something" precedent, not a new UI
idea.

## 7. AI Focus Autonomy (added 2026-09-13 — reverses this spec's original v1 cut)

Brian's explicit call: "AI should decide focus. It should be dynamic." This
replaces the original "AI teams never reassign" scope cut.

**Scoped to the ASSISTANT tier only.** HC/OC/DC/ST stay permanently pinned to
their §4 default (Balanced/OF/DF/Special Teams Work respectively) for every
AI team — reassigning a Defensive Coordinator away from DF Gameplan makes no
narrative sense (who's calling the defense?), and coordinators/HC are exactly
the roles a real front office would never rotate off their titled job for a
side project. Assistants are the real flexible pool: a position coach
plausibly CAN spend more of their energy on player development, injury
prevention/training, or scouting support depending on organizational
priority, which is exactly the real-world distinction this cut draws on.

**Cadence: every offseason, alongside the existing hiring/firing autonomy
pass.** New `coach_ai.run_focus_autonomy(season, exclude_team_abbr)`, called
from the same `season_state.py` offseason rollover hook `run_offseason_
autonomy()` already runs from, for the same 31 non-user teams. Reuses
`coach_progression.compute_team_ranks(season)` — already computed for the
firing pass, no new signal invented — plus this season's real injury count
(`injury_store`) as the two real inputs:

- **Points-for rank bottom-third** (real offensive weakness) → bias assistant
  reassignment toward Development on the offensive side.
- **Real injury count this season, above league-average** (`injury_store`,
  R1) → bias reassignment toward Training.
- **Real season outcome well below the team's own preseason expectation**
  (`team_expectations` — the SAME signal `coach_hiring.classify_season_
  outcome()` already uses for firing decisions) → bias reassignment toward
  Scouting, on the theory that an underperforming team leans harder on the
  draft to rebuild.
- Otherwise, an assistant's default stays Development (§4's existing
  fallback) — the AI doesn't need a signal to justify NOT moving someone.

Deterministic, same convention as every other AI decision in this project:
weighted-random selection seeded via `stable_seed(league_seed, season_number,
"focus_ai", team_abbr, coach_id)`, not a hard rule-based assignment — so two
teams with identical signals don't necessarily make identical choices, same
spirit as `coach_ai.py`'s existing firing-probability rolls. No cap on how
many assistants move to the same bucket in one pass (§2's "no artificial
stacking cap" applies to the AI's own choices too — an AI team CAN
over-invest and pay the same opportunity-cost price a user's team would).

**What's genuinely NOT in scope even with this reversal:**
- **No mid-season AI reassignment.** Only the offseason pass moves AI
  assistants; `run_inseason_autonomy()`'s weekly firing check does NOT get an
  equivalent focus-reassignment companion — that would be a much noisier
  signal (one bad week isn't "this team needs more Scouting") and isn't what
  Brian asked for ("dynamic" reads as "evolves season to season," not
  "twitches weekly").
- **No mid-season lock for the USER's own team.** Unlike Weekly Gameplan
  (locked at kickoff per GDD Sec 7.7.3) or a StaffEffect (computed once per
  game), the user can change their own coaches' focus anytime; it takes
  effect on the NEXT `staff_effect_for()` call (next game) or next draft,
  whichever comes first.
- **Scouting's noise reduction is per-team, not a shared league resource.**
  One team investing in Scouting never affects another team's evaluation of
  the same prospect (the real, shared prospect attributes are never touched —
  see §5.3).
- **2 Min Offense**: cut, not deferred (§2). Would need a real clock/game-
  situation model built first; not proposed here.

## 8. Testing Scenarios

- Every existing `test_coaching.py` assertion about `build_staff_effect()`
  still passes when every coach's `focus_area` is set to its own §4 default —
  i.e., the regrouped logic reproduces sensible behavior at default settings
  (NOT required to byte-for-byte match pre-R13 numbers, per §2/§4 — Brian has
  waived exact backward compatibility — but a HC-defaults-to-Balanced-Gameplan
  team's OF/DF blends should look like a real, reasonable middle ground, not
  an obviously broken one).
- Reassigning an OC's focus away from OF Gameplan measurably zeroes their
  contribution to `pass_bias`/`rz_pass_bias`/etc. (falls back to HC's Balanced
  contribution or fully neutral, matching whoever's left in that bucket).
- An HC focused on Development contributes to `dev_multiplier_offense`/
  `defense` and NOT to either gameplan bucket.
- A Balanced-Gameplan-focused coach contributes to BOTH `pass_bias`-family
  outputs (via the OF bucket) AND `blitz_bias`-family outputs (via the DF
  bucket), each measurably smaller than the same coach's own contribution
  would be if fully focused on just one side (`BALANCE_SPLIT_FACTOR < 1.0`,
  confirmed directly, not just "it doesn't crash").
- `run_focus_autonomy()`: a synthetic team with real injuries well above
  league average ends up with a statistically higher share of its assistants
  on Training than a synthetic team with zero injuries, across many seeded
  trials (same "measure the real distribution, don't just assert one draw"
  discipline as `test_stat_realism.py`). The user's own team is excluded
  (`exclude_team_abbr`), same as the existing firing/hiring autonomy passes.
  Only assistants move; a synthetic team's HC/OC/DC/ST focus is asserted
  UNCHANGED after the pass runs.
- `injury_risk_multiplier` moves in the expected direction as
  Training-focused staff's blended `motivation_chemistry` moves above/below
  the league baseline; a league-average Training investment lands on exactly
  1.0 (same `LeagueBaseline` self-consistency test `coaching.py` already has
  for `discipline`/`dev_offense`/`dev_defense`).
- `_team_scouting_strength()` is 0.0 for a team with nobody focused on
  Scouting, and strictly increases as more coaches focus there or as their
  `overall` rises; HC-focused Scouting produces a strictly larger reduction
  than the same `overall` rating on an assistant.
- `perceived_overall()` is deterministic for a fixed `(league_seed,
  season_number, team_abbr, prospect.index)` — re-running `simulate_draft()`
  with the same inputs produces the same picks.
- A synthetic "zero Scouting investment vs. maximal Scouting investment"
  comparison shows the high-investment team's actual drafted players have a
  measurably higher average true `overall_rating` relative to their draft
  slot than the zero-investment team's, across many seeded trials — the real
  calibration proof this system does what it claims.
- Migration script: idempotent (safe to re-run), assigns every one of the
  real 433 seeded coaches a valid `FOCUS_AREAS` value, and a database
  predating this migration continues to simulate exactly as before if the
  column is absent (same backward-compatibility guarantee every other
  Coach-table migration in this project already carries — this guarantee is
  about a database missing the COLUMN entirely, a different concern from
  §2/§4's waived numeric-value compatibility).

## 9. Calibration Targets — BUILT, actual shipped values (2026-09-13)

- `HC_TIER_WEIGHT = 0.4` / `COORDINATOR_TIER_WEIGHT = 0.6` /
  `ASSISTANT_TIER_WEIGHT = 0.3` (`app/engine/coaching.py`) — the 0.4/0.6 pair
  reproduces the old two-tier HC/coordinator split exactly when only those
  two are present in a bucket.
- `BALANCE_SPLIT_FACTOR = 0.5` (`app/engine/coaching.py`) — live-verified in
  the browser: a Balanced-focused HC measurably moves both OF and DF
  Gameplan numbers, each by less than a single-side-focused coach would.
- `INJURY_RISK_AT_ZERO_TRAINING = 1.20` / `INJURY_RISK_AT_MAX_TRAINING = 0.80`
  (`app/engine/coaching.py`) — same shape as the existing discipline→
  penalty-rate pair.
- `MAX_SCOUTING_NOISE = 12.0` / `MIN_SCOUTING_NOISE = 3.0` /
  `SCOUTING_STRENGTH_K = 40.0` (`app/engine/draft.py`) — verified via a real
  calibration test (`test_perceived_overall_noise_shrinks_with_real_
  scouting_investment`): a 5-assistant, reputation-95 Scouting department's
  average evaluation error is measurably lower than an empty staff's, across
  50 real generated prospects.
- `_POINTS_FOR_BOTTOM_THIRD_RANK = 22` (`app/services/coach_ai.py`) — reuses
  the same real-rank-threshold convention `coach_hiring.py` already
  establishes elsewhere, rather than inventing a new one.

All five constant groups are this module's own documented, disclosed
choices (no GDD source specifies any of them) — adjustable later if actual
play reveals Focus Area feels too strong/weak in any one direction, same as
every other hand-tuned constant in `coaching.py`.

## 10. Implementation Notes — DONE (2026-09-13, same session as the design)

Built in the order below, each step verified independently before the next
started (full account: ROADMAP.md §4h):

1. ~~Data model + migration (§3, §4)~~ — `app/models/coach.py`'s
   `FOCUS_AREAS`/`default_focus_area_for()`, `scripts/migrate_add_r13_focus_
   area.py`, wired into `scripts/import_coaches.py` and `scripts/seed_coach_
   pool.py` too so every coach-creation path agrees.
2. ~~Generalize `build_staff_effect()`~~ — `_weighted_blend()`/
   `_bucket_weight()`/`_tier_weight()` replace the deleted `_blend()`; the
   Balanced Gameplan split lives in `_bucket_weight()`.
3. ~~Training → injuries.py~~ — `_team_injury_risk_multiplier()` in
   `app/engine/injuries.py`, multiplied into `_proneness_multiplier()` per
   team per week.
4. ~~Scouting → draft.py~~ — `team_scouting_strength()`/`perceived_overall()`;
   `simulate_draft()` grew required `league_seed`/`season_number` params to
   seed the noise deterministically.
5. ~~`coach_ai.run_focus_autonomy()`~~ — called from `season_state.py`'s
   `apply_coach_offseason()`, right after the existing hiring/firing pass.
6. ~~UI~~ — `/staff`'s real dropdown (`staff.html`), the new `POST /staff/
   {team_abbr}/{coach_id}/focus` route, the Coach Card's new Focus Area row,
   and two new Trait Effects panel rows.

24 new tests (`tests/test_coaching.py`, `tests/test_draft.py`, `tests/
test_coach_hiring.py`). Full suite: 549 passed, 1 skipped, 0 failed.
Live-verified end-to-end in the browser against an isolated server on a
scratch port (never the user's own real dev server).

## 11. User-Visible Changes

- Real, working Focus Area dropdown on `/staff` for the user's own team's
  coaching staff.
- Reassigning a coordinator or HC's focus visibly shifts that team's
  play-calling identity (Trait Effects panel numbers move) starting next
  game.
- A Training-focused staff visibly reduces (or, if under-invested, worsens)
  that team's real injury rate.
- A Scouting-invested team's draft results start tracking closer to true
  best-player-available; an under-invested team can visibly reach/whiff more
  often — a real, causal story, not flavor text.
- AI teams' assistant coaches visibly reshuffle over multiple offseasons —
  a franchise you keep playing for 5-10 seasons should show real, different
  AI teams leaning into Development, Training, or Scouting based on their
  own real recent performance and injury history, not a static, forever-frozen
  league.
