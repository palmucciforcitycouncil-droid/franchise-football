# Handoff — Team Prestige, Roster Strength & Coach Impact

**Status:** Section 5 (remove `clock_management`/`challenge_sense`) is DONE —
built and folded into `ROADMAP.md` Sec 4c-addendum and `docs/GDD_v3.2.md`
§8.2.1 on 2026-09-11, Option 1 (full removal). **A1 (roster strength) is also
DONE** — `app/engine/roster_strength.py`, folded into `ROADMAP.md`
Sec 4c-addendum-2 and `docs/GDD_v3.2.md` §8.2.3 on 2026-09-11. **A2 (the
position-rank sheet) is also DONE** — folded into `ROADMAP.md`
Sec 4c-addendum-3 on 2026-09-11. **Still open:** wiring `roster_strength`'s
output into JSS's `PreseasonPowerRankDelta` (needs its own scaling decision,
not yet made), A3 (the tuning pass), and A4 (prestige itself). Written
2026-09-11 during a design session on branch `docs/gdd-v3-2`.

**Why this is a new file and not an edit to `HANDOFF.md`/`ROADMAP.md`/`GDD_v3.2.md`:**
a separate session had uncommitted work in all three at the time. This file is
untracked and touches nothing else. **When this work is actually specced or
built, fold it into `ROADMAP.md` and `docs/GDD_v3.2.md` in the same commit** —
those two must not drift apart.

---

## 1. Why this exists

"Team prestige" appears exactly once in the whole project: `docs/GDD_v3.2.md`
§8.2.3, as an undefined input to `Coach_Offer_Score`. It has no definition, no
formula, no weight, no storage, and no consumer. The player-side equivalent,
`Team_Quality_Points` in §8.3.3's Offer Score, is the same idea under a second
name and is equally unbuilt.

Both are needed by **R3d** (coach hiring market) and **R4a** (contracts /
negotiation). Defining prestige *once*, before either chunk starts, prevents
building two parallel systems for the same concept.

---

## 2. Verified engine state (grep-confirmed, not inferred)

**Read this section before designing anything.** Several long-standing docstrings
in the codebase are stale and will lead you to the wrong conclusion.

### 2.1 The sim resolves plays from individual players, not team aggregates

`app/engine/placeholder_ratings.py` still generates
`TeamRatings(offense, defense, special, run_bias, aggression, pace)` as seeded
randoms off `league_seed + team_abbr`, and its docstring still says *"There is no
real roster/player data yet."* **That docstring is stale.**

Confirmed by grepping for actual consumers:

| Field | Consumer |
|---|---|
| `offense`, `defense`, `special` | **None in `app/`.** Only `tests/` constructs them. Dead. |
| `run_bias` | **None.** Superseded by `player_ai.matchup_adjustment()` (see `drive_sim.py:79`). Dead. |
| `aggression` | `drive_sim.py:617`, `game_sim.py:172` (4th-down). Live. |
| `pace` | `game_sim.py:132` via `pace_drives()`. Live. |

Play outcomes run through `player_ai.py` / `services/depth_chart.py` /
`rotation.py` off real player attributes.

**Consequence:** a roster-derived team rating does **not** conflict with the sim —
it reads the same players the sim already reads. An earlier concern in this
session about needing to normalize a new rating onto the placeholder's
distribution was based on the stale docstring and **does not apply.**

**Available cleanup (small, optional):** `pace` and `aggression` are the only
live placeholder fields, and coaches now have real `pace` and
`offensive_aggression` sliders. Wiring those through retires
`placeholder_ratings.py` entirely.

### 2.2 How coach quality reaches games today

Via `StaffEffect` in `app/engine/coaching.py`:

| Rating | Effect | When |
|---|---|---|
| `discipline` | penalty rate x0.70–1.30 | in-game |
| `special_teams_focus` | FG attempt range +/-3 yds | in-game |
| `fourth_down_defense` | run-tactic commitment | in-game |
| `player_dev_offense` / `player_dev_defense` | progression x0.85–1.15 | offseason |

Everything else in `StaffEffect` (`run_pass_tendency`, `blitz_rate`,
`coverage_mix`, `red_zone_*_bias`, `offensive_aggression`, `two_point_tendency`)
is **style, not quality** — deliberately not anchored to reputation
(`models/coach.py:106`: *a great coach is no more likely to be pass-heavy*).
That is correct and should stay.

**Ratings that progress every season but touch no game:**
`motivation_chemistry`, `red_zone_offense`, `red_zone_defense`,
`clock_management`, `challenge_sense`. They render on the Coach Card
(`main.py:861-865`) and move via `coach_progression.py`, and that is all.

### 2.3 Calibration guardrail

`app/engine/coaching.py`'s header states every staff bias is bounded to roughly
**half** the magnitude of the equivalent Weekly Gameplan lever, because a staff
effect applies to all 32 teams in every game all season. Exceeding that drowns
out the player-attribute engine and invalidates `tests/test_stat_realism.py`'s
league-wide calibration. **Any new coach-impact hook must respect this bound.**

---

## 3. Settled decisions (Brian, this session — do not re-litigate)

1. **One prestige value.** Not split into coach-facing and player-facing
   variants. Rationale: a CB won't sign with a team that has a terrible QB any
   more than a coach will take that job. Same want — talent plus a winning
   tradition. `Coach_Offer_Score` and `Team_Quality_Points` both read the one
   value, with their own weights if tuning ever demands it.

2. **Preseason power rank is roster-derived**, computed at season start from
   players + coaches. Not Elo carryover. Two reasons:
   - It exists for **season 1 (2026)**, where every team seeds at a flat 1500
     Elo (`main.py:2199`) and a carryover baseline would be meaningless.
   - It stays **independent of last season's results**. JSS is already
     `0.55 x WinPct`; an Elo-carryover baseline would make
     `PreseasonPowerRankDelta` partly re-measure the same thing and credit a
     coach twice for inheriting a good roster. A roster baseline asks the right
     question: *did you beat your talent?*

3. **Roster strength = starters PLUS depth**, positionally weighted.
   **QB alone outweighs the entire special-teams group.** Coach weighted heavily.

4. **FBGM-style position-rank sheet** in the Power Rankings box: per-team rank
   1–32 for each position group, **plus a Coach column**, sortable, with
   horizontal side-scroll.

5. **No Current-vs-Healthy team-rating split yet.** That column pair depends on
   an injury system (**R1**, unbuilt). Ship one rating column.
   **Revisit and add the second column once the injury feature lands.**

6. **Coach impact is accepted as-is.** No new in-game coach-quality channels are
   being added in this chunk.

---

## 4. Workstream A — roster strength, the sheet, and prestige

### A1. Roster strength function [DONE] (the foundation — nothing like it existed)

**Resolved 2026-09-11: `app/engine/roster_strength.py`.** See `ROADMAP.md`
Sec 4c-addendum-2 for the full accounting. Kept below for the record of what
was open going in.

There is **no roster-to-team-strength aggregator anywhere in the codebase.**
`scouting.py` is entirely in-season play-derived and cannot produce a week-0
number. This function is new work, and it serves three consumers at once: the
position-rank sheet, JSS's `PreseasonPowerRankDelta`, and prestige.

Open decisions:

- ~~**Positional weights.**~~ Resolved: a documented first-pass placeholder
  (`POSITION_WEIGHTS`), with only "QB > K+P combined" actually asserted.
  **Still needs A3's tuning pass before being trusted.**
- ~~**Starter vs depth split.**~~ Resolved: ~80/20 as a roster-wide average,
  not a uniform per-group knob (varies by position, matching the live sim's
  own rotation variance).
- ~~**Group aggregation.**~~ Resolved: snap-share weighted, reusing
  `rotation.py`'s real per-position decay curves, plus a new `IRON_MAN_DECAY`
  for positions the live sim never rotates (QB, OL, S, K, P).
- ~~**Coach contribution.**~~ Resolved: additive (`COACH_WEIGHT = 0.15` blended
  onto `roster_score`, not a multiplier).
- **Where it's computed and stored — still open.** `roster_strength.py` is a
  pure read function today; it is not yet called from anywhere in the season
  lifecycle, and nothing persists its output. Deliberately deferred to land
  together with A2 (the sheet), since a stored week-0 snapshot with no reader
  would be a half-built feature. `power_rank_history.py`'s `DEFAULT_PATH`-
  redirect convention **must** be followed whenever this is wired up (see its
  own docstring: two real data-persistence incidents are documented in
  `ROADMAP.md` Sec2b).

### A2. The position-rank sheet [DONE]

**Resolved 2026-09-11.** See `ROADMAP.md` Sec 4c-addendum-3 for the full
accounting, including a real CSS Grid bug (`min-width: auto` on a grid item
blocking a descendant's `overflow-x: auto`) caught and fixed in this chunk's
own verification. Kept below for the record of the original spec, which was
followed as written with no deviations.

Falls out of A1 — ranking per group instead of summing is not extra work.

- Columns: Team, Conference, Division, Team Rating, Age, then rank 1–32 per
  position group, **plus Coach**.
- Horizontal side-scroll inside the Power Rankings box.
- **One rating column only.** No Current/Healthy until R1.
- `Age` is available today.
- Reuse the existing sort convention. `main.py`'s Roster page already has a
  `ROSTER_SORT_KEYS` / `_roster_sort_value()` GET-param pattern (see
  `ROADMAP.md` R11) — follow it rather than inventing a second mechanism.

**Not covered by A2, left as explicit next work:** wiring this sheet's output
into JSS's `PreseasonPowerRankDelta` (GDD Sec 8.2.3) — that needs its own
scaling/normalization decision (how many JSS-scale points a preseason-rank-
vs-final-rank gap is worth), which A2's own spec never addressed and which
was not decided in this session.

### A3. The tuning pass (agreed)

The weights in A1 are a *claim* about what matters; the sim's real sensitivity
emerges from matchup math. They can disagree in magnitude without either being
wrong.

**Method:** simulate seasons, then check whether the sheet's ordering actually
predicts results — correlate preseason team rating against final record and
final Elo, and check that varying one position group in isolation moves outcomes
by about the amount its weight claims. Adjust weights to match observed
sensitivity. `tests/test_stat_realism.py` is the existing precedent for
full-season calibration work; reuse its harness.

**This pass is what makes the sheet honest.** Without it the UI asserts a
hierarchy the engine doesn't honor.

### A4. Prestige itself

Still fully open, and should be designed **after** A1 exists, since roster
strength is likely one of its inputs. Questions not yet answered:

- **Inputs.** Recent on-field success (Elo, win%, playoff runs — all already in
  `history_store.py`); legacy / championships; a fixed per-franchise market value
  (would need 32 hand-authored numbers); money / facilities / owner (mostly
  blocked on R4a).
- **Momentum.** Slow stored stock that decays toward what recent results justify
  (dynasties compound), vs a stateless rolling window over the last 3–5 seasons
  (recomputable from `history_store.py`, no long franchise memory), vs fast and
  reactive (nearly redundant with Power Rating).
- **Scale and visibility.** Tier label + rank ("Elite, 4th of 32") vs an open
  0–99 matching player OVR and coach reputation vs league rank only vs hidden.
- **Direction of causality — decide explicitly.** Prestige should read
  *results*, never *expectations*. If prestige feeds preseason projections and
  projections feed prestige, teams get credit for being expected to be good.
  Keep it one-way: prestige + roster -> projection -> measured against actual
  results -> JSS.

---

## 5. Workstream B — remove `clock_management` and `challenge_sense` [DONE]

**Resolved 2026-09-11: Option 1 (full removal), Brian's explicit call.** See
`ROADMAP.md` Sec 4c-addendum for the full list of what changed. Kept below for
the record of the options that were weighed.

**Brian's call:** if they do nothing, they shouldn't be attributes.

Justified — there is no clock model and no challenge system, so neither rating
has any signal to move on. `coach_progression.py:26,30` already excludes both
for exactly this reason, and `tests/test_coaching.py:302-304` asserts the
exclusion.

### Everything the removal touches

| File | What |
|---|---|
| `app/models/coach.py:127-128` | field definitions |
| `app/models/coach.py:215` | **`overall` averages 8 ratings including both** |
| `app/main.py:862-863` | Coach Card rows |
| `scripts/import_coaches.py:271,428-429` | generation + persistence |
| `app/engine/coach_progression.py:26,30` | exclusion comments become moot |
| `tests/test_coaching.py:302-304` | assertions reference them by name |
| `docs/GDD_v3.2.md` §8.2.1 | **lists both as Dynamic Performance Ratings** |
| `ROADMAP.md:219` | explains why they don't progress |
| DB | `Coach` is a `SQLModel` table; existing DBs have the columns |

### The one consequence that is not cosmetic

`Coach.overall` is a plain average of **eight** performance ratings blended 50/50
with reputation. Dropping two changes the divisor and therefore **every coach's
Overall**, which drives Staff page sorting, the Coach Card dial, and — per
decision 3 — the coach weighting in team strength. This is a behavioral change,
not a deletion. Decide deliberately whether the new average is over six ratings
or whether the weights are rebalanced.

### Options

1. **Full removal.** Delete fields, migrate the DB, update the GDD and ROADMAP,
   fix the import script and tests. Matches Brian's stated intent. Most work,
   cleanest result. Costly to reverse if a clock model is ever added later.
2. **Remove from `overall` and the Coach Card; leave the columns dormant.**
   No migration, no GDD edit, reversible. The dials stop lying to the user,
   which was the actual complaint. Leaves two unused columns.
3. **Keep as-is.** Rejected.

Option 1 is what was asked for. Option 2 achieves the user-visible goal at a
fraction of the cost and risk — **worth confirming with Brian before doing 1.**

**Note:** `_legacy/` also references both ratings, including a `coach_focus.py`
that actually consumed them. `_legacy/` is dead code and out of scope; do not
let its presence suggest these ratings were ever wired into *this* engine.

---

## 6. Ordering

1. ~~Confirm the option-1-vs-2 question in §5.~~ Done — Option 1, 2026-09-11.
2. ~~Build A1 (roster strength) — it unblocks everything else.~~ Done, 2026-09-11.
3. ~~A2 (the sheet)~~ Done, 2026-09-11. JSS's `PreseasonPowerRankDelta` wiring
   (also flagged as falling out of A1) is **not** done — still needs its own
   scaling decision.
4. A3 (tuning pass) — required before the sheet can be called finished.
5. A4 (prestige) — needs its own design round; §4 lists the open questions.
6. R3d / R4a consume prestige once it exists.
