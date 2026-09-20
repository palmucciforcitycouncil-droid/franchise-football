# R16: Coach Position-Group Impact, the Coaching Tree, and Removing ST

Real spec, written and built 2026-09-15. Origin: Brian asked to remove the
ST (Special Teams Coordinator) role and split the shared 7-option R13 Focus
Area menu into role-specific ones. Through planning this grew into a full
redesign of what a coach's ratings mean and what Focus Area actually does —
this doc fully **supersedes R13's mechanism** (`docs/
R13_COACH_FOCUS_AREA_SPECIFICATION.md`, kept for history, not maintained).

This is Part A of a two-part overhaul. Part B (a realistic HC/OC/DC
promotion market — poaching, retention offers, headline integration) is
`docs/R17_COACHING_MARKET_SPECIFICATION.md`, designed but not yet built.

## 1. Overview — the core mechanic change

R13 had Focus Area reallocate a coach's tendency sliders into
`StaffEffect`, which drove **play-calling** bias (pass/blitz/coverage
tendencies). R16 splits that into two unrelated systems:

1. **Play-calling** reverts to its pre-R13 shape: read by ROLE, not focus.
   An OC's own tendency sliders always drive their team's offensive calls,
   a DC's always drive defense — completely decoupled from anyone's
   current Focus Area. Confirmed in planning: "only the Gameplan setting
   the user picks changes play-calling" (the user's own Weekly Gameplan,
   for their own team) — but AI teams still need SOME staff-driven
   differentiation, or every AI team's play-calling becomes identical.
2. **Focus Area** does something new entirely: a **this-game player-
   attribute boost** to a targeted position group, plus a **running
   seasonal development total** consumed at rollover. Never touches
   play-calling.

## 2. New Coach rating catalog (`app/models/coach.py`)

Eight granular position-group coaching ratings, 0-99, generated the same
disclosed way (anchored to `reputation` + seeded variance,
`scripts/import_coaches.py`) as everything else on `Coach`:

`qb_coaching`, `rb_coaching`, `wr_coaching` (covers WR **and** TE),
`ol_coaching`, `dl_coaching` (covers edge rushers — this engine's
`Position` enum files `LE`/`RE` under the DL group, not LB, per
`app/engine/draft.py`'s `GROUP_POSITIONS`), `lb_coaching` (interior/
off-ball), `secondary_coaching`, `st_coaching`. Every coach — HC included
— carries all 8.

`player_dev_offense`/`player_dev_defense` are now **computed properties**,
not stored fields: `player_dev_offense = avg(qb, rb, wr, ol)`,
`player_dev_defense = avg(dl, lb, secondary)`.

`Coach.primary_side` is a computed property: whichever of {offense
average, defense average, `st_coaching`} is highest, for two uses at
once — a quick-glance "Offense"/"Defense"/"Special Teams" tag anywhere a
coach is displayed, and the Coaching Tree's alignment signal (§5) — never
a specialty-text lookup, so it can never disagree with the ratings
actually driving everything else.

**A real generation bug, caught by live verification**: the first pass
anchored all 8 ratings to `reputation` with an independent bonus for the
matching specialty. For any coach with `reputation` above ~75, both the
bonused and un-bonused draws clamp to the 99 ceiling, so every rating on
the league's most notable coaches converged to 99 regardless of real
specialty. Fixed in `scripts/import_coaches.py`'s `_rating_penalty_for()`:
every NON-matching rating's center is penalized DOWN instead of the
matching one being bonused UP — preserves real separation at any
reputation level, since the penalized ratings keep headroom below the
ceiling even when the matching one is clamped.

### Reputation is now earned

`reputation` starts at import as the same real anchor as before (salary
percentile within role tier — there's no other real signal available at
hire time). Every offseason (`coach_progression.py`'s `_reputation_
delta()`) it now moves: a continuous nudge from real win-pct rank (same
shape as `motivation_chemistry`'s existing movement), plus a discrete
bonus for a conference title (`REPUTATION_TITLE_BONUS`) or Super Bowl win
(`REPUTATION_SUPER_BOWL_BONUS`) that season, from `coach_hiring.
best_achievement()` — a real, already-computed signal. `overall`'s
existing 50%-reputation-weighted formula is unchanged, so `coach_
contracts.coach_market_value()` responds automatically — zero changes to
`coach_contracts.py` needed.

### Specialty can change

After each season's rating movement and Coaching Tree drift, `coach_
progression.relabel_specialty_if_needed()` checks each AC: if a
different group's rating now clearly exceeds their current specialty's
own group rating (`SPECIALTY_RELABEL_MARGIN`, a real margin so noise
doesn't flip a title back and forth), `specialty` updates to match.

## 3. Position-group rating progression (`coach_progression.py`)

Separate from reputation and from the EXISTING rank-based movement of
`discipline`/`motivation_chemistry`/`red_zone_offense`/`red_zone_defense`
(unchanged, still Sec 8.2.2's formula — `RATING_SOURCES` no longer
includes `player_dev_offense`/`player_dev_defense`, since those are
computed now, not stored).

The 8 granular ratings move once per offseason (`_position_rating_
deltas()`) from two combined inputs:
1. **Base weekly practice** — this season's real accumulated Focus Area
   investment for that coach's own available groups (§6's accumulator).
2. **Unit outcome modifier** — the real offense/defense-wide rank
   (`points_for_rank`/`points_against_rank`) for whichever side that
   rating is on (no per-unit rank — e.g. "OL play alone" — exists cheaply
   in this engine, same disclosed substitution `coach_hiring.py`'s own
   JSS formulas already use for an analogous gap).

Scaled by organizational tier — reuses `POSITIONAL_MODIFIER` (HC=1.0,
OC/DC=0.8, AC=0.4) — "proportional to the level of coach they are,"
clarified in planning to mean the coach's OWN progression speed by
role tier, not a player-boost concept.

## 4. New Focus Area taxonomy (`app/models/coach.py`)

One stored string per concept — `FOCUS_OPTIONS_BY_ROLE` gives each role
its own menu, widest → narrowest:

- **HC**: Balanced Gameplan, Offensive Gameplan, Defensive Gameplan,
  Special Teams, Development, Scouting, Strength & Conditioning
- **DC**: Defensive Gameplan, Run Defense, Pass Defense, QB Pressure,
  Development, Scouting, Strength & Conditioning
- **OC**: Offensive Gameplan, Running Game, Passing Game, QB, Receivers,
  OL, Development, Scouting, Strength & Conditioning
- **AC**: Run Defense, Pass Defense, QB Pressure, Running Game, Passing
  Game, QB, Receivers, OL, DL, Secondary, Special Teams, Development,
  Scouting, Strength & Conditioning

`Special Teams` (renamed from R13's `Special Teams Work`) is now offered
to BOTH HC and AC, matching the new `"Special Teams"` AC specialty.
`Training` is renamed `Strength & Conditioning` to match its real second
lever (§7).

`default_focus_area_for()`: HC/OC/DC get a fixed role default (Balanced/
Offensive/Defensive Gameplan). An AC defaults to whichever of their own
menu options they're rated highest at (`_rating_for_focus()`), tie-broken
toward Development — this is the literal "the focus of assistants should
default to whichever they have the highest rating" design ask.

## 5. Focus → position group → rating mapping

Reuses `app/engine/draft.py`'s `GROUP_POSITIONS`. `FOCUS_RATING_WEIGHTS`
and `FOCUS_POSITION_GROUPS` in `app/models/coach.py`:

| Focus | Groups | Driving rating | Breadth |
|---|---|---|---|
| Offensive Gameplan | QB,RB,WR,TE,OL | avg(qb,rb,wr,ol) | broadest |
| Defensive Gameplan | DL,LB,CB,S | avg(dl,lb,secondary) | broadest |
| Running Game | RB(+OL) | 0.6·rb+0.4·ol | medium |
| Passing Game | QB,WR,TE | 0.5·qb+0.5·wr | medium |
| Run Defense | DL,LB | 0.6·dl+0.4·lb | medium |
| Pass Defense | LB,CB,S | 0.3·lb+0.7·secondary | medium |
| QB Pressure | DL,LB (pass-rush) | 0.65·dl+0.35·lb | medium |
| QB / Receivers / OL / DL / Secondary | that group only | matching single rating | narrow |
| Special Teams | K,P | st_coaching | narrow |

Narrow buckets carry a bigger `FOCUS_BREADTH_MULTIPLIER` than broad ones
— "DEF Gameplan boosts everyone but less than a DL-targeted focus."

## 6. This-game position-group boost (`app/engine/coaching.py`)

`apply_focus_boosts(team_abbr, offense, defense)` — magnitude per
targeted player scales off the focused coach's own relevant rating vs.
league baseline (`_slider()`/`LeagueBaseline`, same pattern as every
other rating→bias conversion in this module). **Multiple coaches focused
on the same/overlapping group compound** (additive, via `_team_group_
boosts()`).

Wired into `app/engine/game_sim.py`'s `simulate_game()`, right where real
starters are already fetched (`get_offensive_starters()`/`get_defensive_
starters()`) before `player_ai.build_matchup_context()` runs — the boost
lands on a DETACHED copy of each targeted `Player` (`model_copy(update=
...)`, never the real DB-backed row), so it can never persist and never
touches anything outside that one simulated game. `_GROUP_BOOST_ATTRS`
maps each position group to the real `Player` attributes `player_ai.py`'s
matchup functions already read (`run_block`/`pass_block` for OL,
`man_coverage`/`zone_coverage` for CB, etc.) — a boost here is guaranteed
to reach the sim through an existing, real read path, not a new one.

## 7. Seasonal development accumulator (`app/services/coach_focus_accumulator.py`)

Per-position-group, not coarser (real pros/cons weighed: matches the
whole point of granular Focus Areas, and the SAME accumulated data feeds
three consumers — player dev multipliers, §3's coach rating progression,
and the Trait Effects panel — instead of three separate trackers; cost is
one more JSON store and more weekly bookkeeping).

`record_week()` runs once per simulated week (`season_state.simulate_
current_week()`, before that week's AI firing pass so a coach fired
mid-week still gets credit for the focus they actually held), reusing
`coaching._team_group_boosts()` so "how much a coach's focus counts" is
defined in exactly one place. `dev_multiplier_for_group()` converts
accumulated points into a bounded multiplier
(`DEV_MULTIPLIER_MIN`/`MAX`, `ACCUMULATOR_FULL_SEASON_REFERENCE` — a
disclosed placeholder for "a full season of one dedicated coach's narrow
focus," **[tune]**), consumed by `season_state.apply_progression_to_
roster()` (replacing the old blanket offense/defense split) and `free_
agency.evaluate_fa_offer()`'s `CoachDev` term.

Keyed by `season_number` first (same convention as `power_rank_
history.py`), so a value never crosses a season boundary; no explicit
reset needed, a new season's key just starts empty.

## 8. What's retired vs. kept from `StaffEffect`

**Retired**: `pass_bias` et al. don't disappear from `StaffEffect` — they
stay, but their INPUT switches from R13's focus-gated blend
(`_weighted_blend`/`_bucket_weight`/`_tier_weight`, all deleted) to
`_role_attr()`, a direct role-based read with an HC fallback for a vacant
coordinator seat. `fg_range_bonus` is fully retired as a decision lever —
Special Teams focus no longer widens FG-attempt range; it boosts the
kicker's own rating instead (§6). `dev_multiplier_offense`/`dev_
multiplier_defense` fields are removed from `StaffEffect` entirely,
replaced by §7's per-group accumulator lookup.

**Kept, unchanged mechanism**: `penalty_rate_multiplier` (HC discipline
— already independent of focus before R16). `injury_risk_multiplier`
(Strength & Conditioning via `motivation_chemistry`) gains a sibling,
`stamina_recovery_multiplier`, computed the identical way — Brian's own
ask: "strength and conditioning in general will impact stamina and
injury." **Disclosed, not yet wired**: `stamina_recovery_multiplier` is
computed and shown on the Trait Effects panel, but not yet threaded into
`app/engine/rotation.py`'s `reliability_factor()` (today purely `p.
durability`/`p.stamina`-driven with no team context) — doing that
properly means passing a team-level multiplier through several shared
call sites; judged too risky to rush into this build.

## 9. Removing the ST role

`CoachRole.ST` deleted outright — no back-compat value (saves are
disposable). Every real ST coach becomes an AC with specialty
`"Special Teams"` (`scripts/import_coaches.py`'s `_SPECIALTY_BY_TITLE`,
replacing its old `_ROLE_BY_TITLE` mapping to `CoachRole.ST`) — a real
org-chart demotion, not a firing.

Cascading cleanup: `app/models/coach.py` (enum, `ROLE_TITLES`,
`tier_key()`'s `COORD` tier → `{OC, DC}`, dropped `st_*_championships`
fields), `app/engine/coach_hiring.py` (`ST_WEIGHTS`, `compute_st_jss()`
deleted), `app/engine/coach_replacement.py` (`_ST_HIERARCHY`,
coordinator-tuple references), `app/engine/coach_contracts.py`
(`DEFAULT_CONTRACT_YEARS`), `app/services/coach_store.py`
(`ROLE_ORDER`), `app/services/coach_records.py` (role-key mapping),
`app/engine/coach_progression.py` (`POSITIONAL_MODIFIER`), `app/main.py`
(role lists), `app/engine/draft.py` (Scouting's own tier-weight table —
previously shared literal constants with `coaching.py`'s now-deleted
blend; replaced with a small local table, identical values, so
Scouting's behavior is numerically unchanged). `scripts/migrate_add_
r13_focus_area.py` deleted — dead now that a schema change needs a full
data rebuild (new/removed Coach columns), not an ALTER-style migration.

## 10. AI Focus Autonomy (`app/services/coach_ai.py`) — scope expanded

R13 only reassigned AI teams' Assistant Coaches. R16 expands this to
EVERY role ("the AI should be making the best decisions they can for
their team," not just its assistants): `run_focus_autonomy()`'s
`_weights_for_coach()` blends real team-need signals (`offense_needs_
help`/new symmetric `defense_needs_help`, `injury_prone`, `rebuilding`)
with each coach's own rating at their available options
(`OWN_RATING_WEIGHT`) — favoring both what the team needs AND what that
coach is personally good at. The user's own team stays excluded,
unchanged from R13.

**Disclosed consequence**: no AI signal specifically biases toward
Special Teams, so K/P boosts default to near-zero league-wide unless a
user (or a future signal) actively picks it. Not silently patched —
flagged for awareness.

## 11. UI (`app/templates/staff.html`, `app/main.py`)

Per-coach `focus_options` (`focus_options_for(coach)`) replaces the
single shared `focus_areas` list. The Trait Effects panel shows real
per-position-group numbers — this week's active boost (compounded) and
this season's accumulated development — alongside the still-real
play-calling rows, so changing a coach's focus and resubmitting visibly
moves the relevant row(s). Coach Card surfaces the 8 granular ratings
(replacing the old Player Dev Off/Def rows) and a `Primary Side` tag.

## 12. Not done in this build (tracked, not silently skipped)

- Part B (`docs/R17_COACHING_MARKET_SPECIFICATION.md`) in full.
- `stamina_recovery_multiplier` → `rotation.py` wiring (§8).
- `tests/test_coaching.py`/`test_coach_hiring.py`/`test_coach_
  contracts.py` rewritten for the new taxonomy (currently fail to
  collect — they reference removed symbols like `CoachRole.ST`/
  `FOCUS_AREAS`).
- Every `[tune]`-marked constant (boost/development magnitudes, Coaching
  Tree drift rate, specialty relabel margin, accumulator reference) is a
  real, disclosed placeholder pending live playtesting, per Brian's own
  "we'll need to mess around and test" expectation.
- A player-facing manual section on the full coaching system, stressing
  the Coaching Tree — requested for after the build is tested.
