# R16: Practice Squad, 53-Man Active Roster & Injured Reserve

**Status:** Design Complete (2026-09-15). Ready for Implementation.
**Roadmap Entry:** ROADMAP.md §4g (originally scoped 2026-09-13, fully locked in 2026-09-15)
**Related:** GDD Sec 8.3 (Contracts & Salary Cap, R4a), Sec 3.8/6.10 (Injuries, R1), R4b (Free Agency), R4c (Trades)
**Dependencies:** R4a/R4b/R4c (Contracts/FA/Trades, DONE), R1 (Injuries, DONE), roster_prep.py's existing gate/auto-fill infrastructure (DONE)

---

## 1. Overview

Today this engine knows `MAX_ROSTER_SIZE = 53` (`app/main.py:129`) but never enforces it — every imported roster carries 54-72 real players (median low-to-mid 60s; ARI is the high outlier at 72), and nothing ever cuts anyone. `Injury.placed_on_ir` already exists and is already computed correctly (`weeks_out >= 4` at the moment of injury, `app/engine/injuries.py:241`) — but it's a display-only flag today, read by nothing.

R16 makes both real:

- A real 53-man active-roster cap, for the first time.
- A 16-slot practice squad, with real weekly protection, a real cross-team poaching market (mirroring the current real-NFL CBA rule), and real unlimited game-day elevation.
- A real Injured Reserve, gated on the injury system's own existing eligibility flag, with a real 4-simulated-week minimum stay before reactivation.
- Every AI team manages all of this autonomously, using the same shared infrastructure the user's own team uses (`free_agency.fill_roster_gaps()`, `roster_prep.prepare_ai_rosters()` — this pattern already exists and already runs for every AI team every season, R16 extends it rather than inventing a parallel system).

This is a large chunk — bigger than the "medium chunk" ROADMAP §4g originally estimated once poaching/protection/elevation were fully scoped. Section 16 below breaks it into a build order.

---

## 2. Settled Decisions (Do Not Reopen)

Locked 2026-09-13 (original session, see HANDOFF.md and ROADMAP §4g):

1. Practice squad size: **16 slots**, on top of the 53-man active roster.
2. **53-man active roster cap enforced for the first time.**
3. **Practice squad salaries count against the salary cap.** (Re-confirmed 2026-09-15 after a brief proposal to make them cap-exempt — rejected; matches both the original decision and the real NFL.)
4. "Place on IR" only works on a player with a **current** injury in the injury system, eligible once `weeks_out >= 4` at time of injury (already computed and stored as `Injury.placed_on_ir` — this spec wires up an existing field, doesn't invent a new eligibility check).
5. A player on IR does **not** count toward the 53.
6. Reactivation: a player must spend **at least 4 simulated weeks** on IR before he can be reactivated.

Locked 2026-09-15 (this session):

7. **No practice-squad eligibility restriction.** Any player not on the active 53 or IR can sit on the practice squad — no experience/age gate, unlike the real NFL's accrued-season limit.
8. **Poaching is in scope**, modeled closely on the real CBA rule (full mechanics in §5).
9. **Game-day elevation is in scope**, but simplified: manual only, user's own team only, no AI equivalent, **no per-game or per-season limit** (this deliberately drops the real NFL's 2-per-game/3-per-season caps — see §6).
10. **Practice squad salary is a flat league minimum, 1-year deal.** Once a player leaves the PS (promoted or re-signed), his contract follows the same market-value logic as any other player. Unsigned at the end of the season, he returns to the free-agent pool. Otherwise he stays on the PS until cut or retired.
11. **AI teams get simple heuristic autonomy** for cuts, PS fill, weekly protection, and opportunistic poaching — reusing the existing rating math (`roster_strength.py`) the AI already uses elsewhere, not a new strategic layer. **AI teams do not use elevation** (§9's "user's team only" rule).
12. **IR salary counts against the cap**, same as an active player's — matches decision #3's spirit and the real NFL.
13. **The $450M salary cap is NOT re-tuned as part of this feature.** It stays as-is; teams end up with more cap room once rosters shrink, which is an acceptable side effect, not a bug to fix here. (See §12 for why the cap is $450M today, for anyone who re-opens this later.)
14. **No waiver-claim system for ordinary roster cuts.** A player cut to make room (including the case where a team is over 53+16=69 combined and has to release outright) goes straight to the free-agent pool, immediately signable by anyone — including the team that just cut him. This is a deliberate simplification from the real NFL's waiver-priority system.
15. **Practice squad players are not tradeable.** Trades only ever involve active-53 and IR players, same as today. The only way a PS player changes teams is the poaching mechanic in §5.
16. **Weekly PS protection carries over by default.** The same 4 players stay protected week to week until the user actively changes the picks — not a forced weekly re-pick.
17. **The anti-restash lock is 3 games**, same number as the poaching team's own mandatory-roster-time rule (§5) — one consistent number, not two.
18. **Gate routing:** a team short of position minimums routes to **GM Desk** (where signing happens); a team over the 53-man limit routes to the **Roster page** (where cutting/demoting happens) with a "trim your roster" banner.
19. **A separate "Auto-Fill Practice Squad" action exists**, alongside the existing active-roster auto-fill button — same best-available-free-agent-first logic, but signs at the flat PS minimum instead of market value.
20. **Release and Send-to-Practice-Squad actions live in two places**: the Player Card modal (gated to the user's own players, same convention Staff page already uses for Fire/Extend) **and** inline row buttons on the Roster page's active-roster table (matching the Extend/Fire pattern already built for Staff's assistant-coach table, R-series 2026-09-15). Both call the same backend routes. Release requires a confirm popup, same convention as every other destructive action in this app (Fire, Delete Save).
21. **The user can poach too** — this isn't purely a defensive mechanic. The user needs a real surface to browse other teams' *unprotected* practice-squad players and sign one, same rules (§5) applying in either direction.

---

## 3. Data Model

### 3.1 New `Player` fields

Following `app/core/db.py::_migrate_schema()`'s existing idempotent pattern (the `_PLAYER_COLUMNS_ADDED_2026_09_14` list-and-loop, not the older one-off `guaranteed_money` special case) — add a new `_PLAYER_COLUMNS_ADDED_2026_09_15` list:

| Column | Type | Default | Purpose |
|---|---|---|---|
| `roster_status` | TEXT | `'ACTIVE'` | `ACTIVE` / `PRACTICE_SQUAD` / `IR` / `ELEVATED`. Existing players all default to `ACTIVE` — deliberately, since every currently-oversized team needs to hit the new over-53 gate on next load (see §7). |
| `roster_lock_until_week` | INTEGER | `NULL` | Set when a player is poached onto a new team's 53, or promoted to block a poach — the week number (relative to the current season) before which he can't move to PS. Covers both directions of the 3-game rule in one field. |
| `poached_from_team_abbr` | TEXT | `NULL` | Set only on a poached player, cleared once his lock expires. If he's released before then, he reverts to this team instead of the free-agent pool. |
| `ps_protected` | INTEGER (bool) | `0` | This week's protection pick. Carries over automatically (decision #16) — nothing resets it; the user (or AI) explicitly flips it. |
| `ir_placed_week` | INTEGER | `NULL` | The week (relative to the current season) a player was placed on IR — the reactivation gate checks `current_week - ir_placed_week >= 4`. |

`roster_status` as a plain TEXT column (not a DB-level enum) matches how `Position`/`CoachRole` etc. are already handled elsewhere in this codebase (Python-side `Enum`, stored as its name). Add a `RosterStatus` enum to `app/models/player.py` alongside the existing `Position`.

### 3.2 Season-rollover cleanup

All of the above are **in-season-only** concepts. At season rollover (`season_state.start_new_season()` / `reset_season()`), every player's `roster_status` other than `IR`... actually **including** `IR` (a season ending doesn't heal anyone) should be reconsidered:

- Clear `roster_lock_until_week` / `poached_from_team_abbr` / `ir_placed_week` for everyone — these are in-season bookkeeping with no meaning across a season boundary.
- A player still on IR when the season ends: return him to `ACTIVE` (or `PRACTICE_SQUAD` if the team is already at 53) for the new league year, same as the real NFL where IR doesn't persist into a new season. His `Injury` row's own healing (`weeks_out`) is a separate, already-existing concern (R1) — not this feature's to change.
- `ps_protected` resets to `False` for everyone at rollover — the *carries-over* rule (decision #16) is a within-season convenience, not a promise across years.

---

## 4. The 53-Man Cap, Practice Squad & Cuts

### 4.1 Enforcement points

The 53-man cap is checked (not just displayed) at every point a player's `roster_status` would become `ACTIVE` on a team that's already full:

- **Free-agent signing** (GM Desk, Free Agency page): the signing UI needs a target (Active vs. Practice Squad) when there's room in both; blocked outright if the chosen bucket is full.
- **Trades**: a trade that would push the receiving team over 53 active (or over 16 PS, though PS isn't tradeable per decision #15, so only the active case applies) is blocked until the user makes room — no automatic restructuring, matching how this engine already just refuses an over-cap offer rather than trying to fix it for you.
- **Draft picks**: a newly drafted rookie needs the same Active-vs-PS choice as a UDFA signing once the 53 is full (rare in practice — a team should usually have room right after final cuts, but not guaranteed if they've been re-signing aggressively).
- **Reactivating from IR** and **promoting from PS**: both require an open active slot; blocked (with a clear message) if the 53 is already full — the user has to cut someone first.

### 4.2 Roster actions (Release / Send to PS / Promote to 53)

New routes, mirroring the existing `/staff/{team}/fire` pattern (POST, confirm-gated on destructive ones):

- **Release**: `team_abbr = None` (straight to the free-agent pool, decision #14). Confirm popup required.
- **Send to Practice Squad**: `roster_status = PRACTICE_SQUAD`, salary drops to the flat PS minimum, contract resets to 1 year (decision #10) — unless he's already under a PS deal (no-op). Blocked if the PS is already full (16).
- **Promote to 53**: `roster_status = ACTIVE`. Blocked if the 53 is already full. If this is blocking a poach (§5), also sets `roster_lock_until_week`.

Surfaced in both locations per decision #20: inline on the Roster page's active/PS tables, and on the Player Card modal (gated to `is_user_team`).

### 4.3 Practice-squad-specific auto-fill

New sibling to `free_agency.fill_roster_gaps()` — same "best-rated fit from the shared FA pool" selection, but:
- Targets open PS slots (up to 16), not position-minimum shortfalls.
- Signs at the flat PS minimum, not `expected_market_value()`.
- No cap-space juggling needed in practice (PS minimums are small relative to $450M), but still deducted from cap room per decision #3/#12.

Reuses the same shared-pool/one-session pattern `roster_prep._fill_teams()` already established, just with this new signing function instead of `fill_roster_gaps()`.

---

## 5. Poaching

### 5.1 The rule, precisely

1. Each team has 16 PS slots; each week, the team designates **4 as protected** (persists per decision #16 — no action needed most weeks).
2. Any **unprotected** PS player is poachable by any other team.
3. The poaching team signs him **straight to their own 53** (never to their own PS) — blocked if they have no open 53 slot.
4. He's **guaranteed 3 weeks of salary** and **must stay on the poaching team's 53 for 3 simulated weeks** (`roster_lock_until_week`).
5. If released before that lock expires, he **reverts to his original team** (`poached_from_team_abbr`) instead of hitting the free-agent pool — landing back on that team's practice squad.
6. A team cannot sign another team's unprotected PS player directly onto their own PS — only through step 3.
7. **Defense**: the original team is notified when a poach is about to happen and can pre-empt it by promoting the player to their own 53 first. If they do, that promotion carries the **same 3-game lock** (`roster_lock_until_week`, decision #17) — closing the loophole where a team could "promote for a week, restash" to dodge the rule.
8. The user can also **initiate** a poach against any other team's unprotected PS player (decision #21) — same rules apply, just user-triggered instead of AI-triggered.

### 5.2 Weekly flow

Poaching evaluation runs as part of the existing weekly simulation pipeline (`season_state.simulate_current_week()`), **before** that week's games simulate — the same point coach-firing rolls and AI resign decisions already happen:

1. Every AI team evaluates every OTHER team's unprotected PS players (simple heuristic per decision #11 — see §8).
2. If any AI team decides to poach one of the **user's** unprotected PS players, this becomes a **pending decision** that gates the rest of "Sim Week" — same UX pattern as the existing preseason roster gate (user is shown "Team X wants to sign [Player] off your practice squad" with two choices: let it happen, or promote him to your own 53 to block it) before the week's games proceed.
3. AI-vs-AI poaching resolves automatically, no user involvement (may be worth a Headlines line — see §10).
4. The user's own poaching of an AI team's PS player is a separate, anytime action (not gated to the weekly sim step) — a new "Browse Practice Squads" or similar surface, since the user should be able to do this whenever, not just react to being poached.

### 5.3 Cap/roster interaction

The poaching team needs an open 53 slot **before** the poach can go through (decision keeps this simple — no forced cut to make room). If an AI team has no room, it just doesn't poach that week (simple heuristic, no cascading cut-to-make-room logic).

---

## 6. Game-Day Elevation

- **Manual only, user's team only, unlimited uses** (decision #9 — deliberately simpler than the real NFL's 2-per-game/3-per-season caps).
- Action available from the Roster or Depth Chart screen: any `PRACTICE_SQUAD` player can be set to `ELEVATED` for the current week.
- While `ELEVATED`, the player is treated as available for that week's depth chart/sim — same eligibility as `ACTIVE` — addressing the exact gap `depth_chart.py`'s own comment already flagged ("this engine has no practice-squad emergency-elevation system to reach for instead").
- **Auto-reverts to `PRACTICE_SQUAD`** immediately after that week's game(s) simulate — a new post-sim step in `simulate_current_week()`, alongside the existing per-week cleanup work that function already does.
- No AI equivalent — AI teams never elevate (their `fill_roster_gaps()`-driven 53 is already built to meet position minimums; elevation is a user convenience for squeezing extra value out of a cap-limited roster, not something the simple-heuristic AI needs).

---

## 7. Injured Reserve

Mostly wiring up what already exists rather than new eligibility logic:

- **Place on IR**: only enabled for a player with a **current** `Injury` row where `injury.placed_on_ir` is already `True` (already computed as `weeks_out >= 4` at injury time, `injuries.py:241` — no new threshold check needed). Sets `roster_status = IR`, `ir_placed_week = season.current_week`.
- **Doesn't count toward 53** — a `roster_status == IR` filter on every active-roster count (`roster_shortfall()`, the depth chart, the new gate).
- **Reactivation**: enabled once `season.current_week - player.ir_placed_week >= 4`. Reactivating sets `roster_status = ACTIVE` if there's room, else `PRACTICE_SQUAD` — surfaced as an explicit user choice if both are open, since which one matters (PS reactivation still needs an open PS slot too).
- **Cap**: IR salary counts against the cap throughout (decision #12) — no change needed to cap-room math beyond making sure the payroll sum still includes IR players (it already does today, since nothing currently excludes anyone; the risk is a NEW active-only payroll helper accidentally excluding IR — call this out explicitly wherever payroll is summed for cap checks).
- **AI**: auto-places any AI player crossing the `weeks_out >= 4` threshold onto IR (same simple-heuristic tier as the rest of AI roster management) — otherwise AI rosters would silently carry phantom long-term-injured bodies against their effective depth, which is exactly the "no practice-squad emergency-elevation system" gap the depth-chart code already flagged.

---

## 8. AI Autonomy (Simple Heuristic Tier)

Reuses `roster_strength.py`'s existing rating math (the same the AI already leans on for depth-chart/needs decisions elsewhere) rather than a new strategic layer:

- **Initial cut to 53** (first time an AI team is found over the limit — almost every team, on this feature's first rollout): keep the 53 best-rated players by position need, per `ROSTER_REQUIREMENTS`; everyone else goes to the practice squad, up to 16, best-rated first; anyone still left over (a team like ARI, 72 total, needs 3 released outright) is released straight to the FA pool (decision #14), worst-rated first.
- **Weekly protection**: auto-protect the 4 highest-rated unprotected PS players.
- **Poaching**: opportunistic only — poach an unprotected PS player only if he's a clear upgrade at a position of real need AND the team has an open 53 slot. No proactive cutting to make room.
- **IR**: auto-place at the `weeks_out >= 4` threshold, no user-style manual judgment call.
- **PS fill**: run the new PS-specific auto-fill (§4.3) as part of the existing `roster_prep.prepare_ai_rosters()` pass, right after the existing active-roster fill.
- **No elevation** (decision #11/#9).

---

## 9. Depth Chart & Cap Accounting Changes

- `depth_chart.py`'s starter-selection and `app/main.py`'s `_depth_chart_groups_for_team()` both need a `roster_status in (ACTIVE, ELEVATED)` filter — today they pull every player on the team regardless of status; PS/IR players must never be selectable as starters (matches the real NFL and the code's own already-stated intent).
- `free_agency.roster_shortfall()` / `ROSTER_REQUIREMENTS` checks must filter to `roster_status == ACTIVE` — today they count every player on the team (§confirmed via code read, 2026-09-15), which would let a full practice squad silently satisfy position minimums without a single active body at that position.
- Every payroll sum used for cap-room checks (`coach_contracts`/`contracts.team_cap_space()` equivalents for players) must include `ACTIVE + IR + PRACTICE_SQUAD` (decision #3/#12) — i.e., everyone except free agents. Since nothing is excluded today, the risk is the *opposite* direction: make sure whatever new "active roster" helper this feature adds for depth-chart/gate purposes is never accidentally reused for cap math too.

---

## 10. UI Changes

- **Two new Roster-page boxes**: Practice Squad (16 slots, showing each player's protection status and any poaching lock) and Injured Reserve (showing weeks remaining until reactivation-eligible).
- **Roster-cut gate** (over 53 active): redirects to `/roster` with a "trim your roster" banner, listing who needs to move (decision #18).
- **Roster-shortfall gate** (under position minimums, active-only now): redirects to **GM Desk** instead of Roster page (decision #18) — a change from today's existing gate, which currently sends this case to `/roster` too.
- **Two auto-fill buttons**: the existing active-roster one (now active-only aware) and the new PS-specific one (decision #19).
- **Release / Send to PS / Promote to 53**: Player Card + inline Roster-page row buttons (decision #20).
- **Weekly protection picker**: pick 4 of 16 on the Roster page's new PS box.
- **Poaching-alert gate**: a new pre-sim-week screen when the user's own PS is targeted (§5.2).
- **"Browse Practice Squads"**: a new surface for the user to poach an AI team's unprotected PS player (decision #21) — likely a league-wide table similar to Staff's Find Coaches (sortable, one row per eligible player across all 32 teams), reusing that page's sort convention.
- Consider a real Headlines line for a notable poaching event (either direction) — optional, not blocking, fits the existing `is_user_team`-aware Headlines pipeline (R9) cleanly if picked up.

---

## 11. What's NOT in Scope (Disclosed)

- Practice-squad eligibility rules (accrued-experience limits) — explicitly decided against (decision #7).
- A real waiver-claim/priority system for ordinary cuts — explicitly decided against (decision #14).
- Practice-squad trades — explicitly decided against (decision #15).
- Elevation limits (2/game, 3/season) — explicitly dropped (decision #9).
- AI elevation — explicitly out (decision #9/#11).
- Salary cap re-tuning toward the real $301.2M figure — explicitly deferred (decision #13).
- A real 46-man game-day-active-vs-53-inactive distinction — this engine has no such concept anywhere today and R16 doesn't add one; "elevated" just means eligible for that week's sim, full stop.

---

## 12. Why the Cap Is $450M Today (Background, Not This Feature's Job to Fix)

For whoever re-opens decision #13 later: `app/engine/contracts.py:56-73` documents that the real 2026 NFL cap ($301.2M) would leave 29 of 32 teams permanently over, because (a) real imported rosters carry 54-72 players, not 53, each on a real (non-inflated) AAV, and (b) this engine's cap hit is simply a player's flat salary with no signing-bonus proration (real NFL cap accounting prorates a bonus's charge across the contract, which usually *lowers* a given year's hit — this engine charges the full AAV every year). $450M was picked as the smallest round number every current oversized roster fits under. Once R16 ships and every team is at 53+16=69 real bodies, both pressures ease considerably on their own — worth revisiting once there's real data on how much cap room opens up, but that's a follow-up decision, not part of this build.

---

## 13. Build Order

1. **Data model**: `RosterStatus` enum, the 5 new `Player` columns, migration, season-rollover cleanup (§3).
2. **Core 53/PS mechanics, no poaching/elevation yet**: enforcement points (§4.1), Release/Send-to-PS/Promote-to-53 actions (§4.2) in both UI locations, PS auto-fill (§4.3), the two new gates + GM Desk routing change (§10), depth-chart and `roster_shortfall()` active-only filtering (§9), the two new Roster-page boxes (§10). AI: initial cut-to-53 + PS fill (§8, first two bullets).
3. **IR**: Place-on-IR/Reactivate actions, `ir_placed_week` gate, AI auto-IR (§7, §8).
4. **Poaching**: weekly protection UI, AI opportunistic poaching, the pre-sim poaching-alert gate, 3-game lock + revert-on-early-cut, the user's own "Browse Practice Squads" poaching surface (§5, §8, §10).
5. **Elevation**: manual elevate/revert, depth-chart `ELEVATED` eligibility, post-sim auto-revert (§6).
6. **Trade box filtering**: exclude `PRACTICE_SQUAD` from `_trade_side_context()`'s tradeable players on both GM Desk and Draft page (decision #15) — small, isolated, touches the shared `_trade_box.html`/`_gm_trade_side.html` partial built this session.

Steps 3-6 are each independently shippable after step 2 lands — step 2 alone (the 53-man cap + basic practice squad, no poaching/elevation) is already a complete, coherent feature if this needs to be split across sessions.

---

## 14. Testing Scenarios (Representative, Not Exhaustive)

- A team with 68 real imported players hits the over-53 gate on first load; auto-cut-to-53 leaves exactly 53 active, up to 16 on PS, and 0 released (68 - 53 - 16 = -1, fits).
- ARI (72) hits the same gate: exactly 3 players released outright to the FA pool (72 - 53 - 16 = 3).
- `roster_shortfall()` no longer counts a PS or IR player toward a position minimum.
- Depth chart / starter selection never selects a PS, IR, or (outside game week) `ELEVATED`-but-not-this-week player.
- Placing a player on IR without a qualifying current injury is rejected.
- Reactivating a player before 4 simulated weeks on IR is rejected; exactly at 4, it's allowed.
- Poaching an unprotected PS player signs him to the poaching team's 53, not their PS; blocked if the poaching team has no open 53 slot.
- Poaching a *protected* PS player is rejected outright.
- Releasing a poached player before his 3-game lock expires reverts him to his original team's PS, not the FA pool.
- Promoting your own player to block a poach applies the same 3-game lock.
- A practice-squad signing always lands at the flat league minimum, 1-year term, regardless of the player's rating.
- Elevating a PS player makes him depth-chart-eligible for the current week only; the week after, he's back to `PRACTICE_SQUAD` with no elevation count ever tracked or capped.
- Cap-room checks include PRACTICE_SQUAD and IR payroll, not just ACTIVE.
- A trade offer including a PRACTICE_SQUAD player is rejected or that player simply never appears as a tradeable asset.
- Season rollover clears every `roster_lock_until_week`/`poached_from_team_abbr`/`ir_placed_week`/`ps_protected`, and returns any still-on-IR player to ACTIVE or PRACTICE_SQUAD for the new league year.

---

## 15. User-Visible Changes Summary

- Rosters shrink to a real 53 active + up to 16 practice squad, for the first time ever.
- New Practice Squad and Injured Reserve boxes on the Roster page.
- Release / Send to Practice Squad / Promote to 53 buttons, on the Player Card and inline on the Roster page.
- A weekly "protect 4 of 16" decision on the practice squad.
- A real cross-league practice-squad poaching market, in both directions, with a pre-sim alert when the user's own PS is targeted.
- Unlimited manual game-day elevation for the user's own team.
- A real IR with a real 4-week-minimum return timer.
- Two roster-readiness gates instead of one: over-53 sends you to the Roster page to trim; under-minimum sends you to GM Desk to sign — each with its own one-click auto-fill.
