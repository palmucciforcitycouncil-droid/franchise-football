# Franchise Football — Roadmap & Execution Playbook

**Read this after HANDOFF.md, before starting any new chunk of work.** HANDOFF.md is the detailed "what happened and why" log. This file is the forward-looking "what's left and how to spend tokens efficiently doing it" plan. Update the checkboxes here as chunks land; leave HANDOFF.md's own numbered-item narrative style for the detailed record of *how* each chunk was actually built.

Written 2026-09-09, after item 37 (roster-depth rotation); updated same day after item 38 (M1: Defensive TD), then again after item 39 (M3: Stats page redesign), then again after M2 (Kicking/Punting box score), then again after M6 (Player Card Stats tab), then again after M5 (HOF page redesign). Current state: 247 tests passing (1 skipped), MVP roughly 97% complete by scope, remaining gaps are well-understood and itemized below.

---

## 1. Where things stand

**Solid and real, not stubs:** full sim engine (drive/game sim, play-calling AI, Score Fidelity System), season/schedule/standings/Power Ratings, real playoffs with the full tiebreaker chain, Awards (MVP/OPOY/DPOY/ROY), Progression/Regression, save/load, League History, real Hall of Fame, Player Cards (Overview/Ratings), real NFL data seeding (2002-2025), roster-depth rotation (item 37), and a UI that matches the Figma design tokens with a persistent header on every page.

**What's actually left for MVP** (Part 1 per the GDD) is a short, specific list — not a vague "polish everything":

1. ~~Defensive TD~~ — **done (M1, 2026-09-09)**. See §2's M1 row and HANDOFF.md item 38.
2. ~~Kicking/Punting box-score stats~~ — **done (M2, 2026-09-09)**. See §2's M2 row and HANDOFF.md's M2 session entry.
3. ~~Two UI pages that still don't match the Figma redesign: Roster, HOF~~ — **done (M4 + M5, 2026-09-09)**. ~~Stats (customizable columns)~~ — **done (M3, 2026-09-09)**, see §2's M3/M4/M5 rows and HANDOFF.md items 39/M4/M5.
4. ~~Player Card's Stats tab~~ — **done (M6, 2026-09-09)**, see §2's M6 row. Contract tab is still blocked on a real decision, see M8 below.
5. A handful of disclosed, smaller stat-realism gaps (DEF tackles still ~2-3x real, TFL still elevated) that `tests/test_stat_realism.py` now tracks with deliberate headroom rather than hides.

Everything else — Contracts, Free Agency, Trades, Coaching Staff, Draft, weather, the full penalty catalog, a real injury system, return-game simulation — is Part 2 (R2) per the GDD's own scope line, confirmed multiple times this project: *"Everything in this Part is in scope for the first playable release. Nothing here should expand without an explicit decision to promote content from Part 2."*

---

## 2. MVP chunks (finish Part 1)

Each row is sized to run as its own fresh Claude Code session (or bundled per the Bundling column). "Model" is a recommendation, not a requirement — see §4 for the reasoning.

| # | Chunk | What it actually is | Key files | Size | Model | Bundle with |
|---|---|---|---|---|---|---|
| **M1** | ~~Defensive TD~~ **DONE (2026-09-09)** | New `PlayEvent` outcome (`"defensive_touchdown"`). Scope stayed narrow as written: no open-field return simulation — `drive_sim.py`'s `_defensive_td_probability()` rolls a real, small, distance-based chance at every INT/fumble. Wired into `defensive_box_score.py` (new `defensive_touchdowns` field), `awards.py`'s DPOY weights (rebalanced, +0.10 slice), and season/career stats (`season_stats.py`, `history_store.py`, including its own HOF defensive scoring). Also fixed a real box_score.py stat-corruption bug the new outcome exposed (would have double-counted a pick-six as a real reception) and a `test_stat_realism.py` headroom fragility the new RNG draw exposed at the suite's default seed — see HANDOFF.md item 38 for full detail. | `drive_sim.py`, `game_state.py`, `defensive_box_score.py`, `awards.py`, `game_sim.py`, `box_score.py`, `season_stats.py`, `history_store.py` | M | Sonnet (no Opus session needed — mechanic stayed within the narrow scope as written) | — |
| **M2** | ~~Kicking/Punting box score~~ **DONE (2026-09-09)** | New `KickingLine`/`PuntingLine` in `box_score.py`, keyed by real kicker/punter like `RushingLine` (FG made/attempted by distance bucket via the same desc-text parsing convention `scouting.py`'s `field_goal_accuracy()` already used, since attempt yardage isn't in a structured field; XP made/attempted via a new `extra_point` `PlayEvent` play_type, since PATs used to be folded silently into the touchdown event with no independent per-kicker attribution; punt count + **net** avg (not gross — no return-game sim exists, same disclosed gap as `scouting.py`'s own return-average note) + inside-20). `depth_chart.py`'s `OffensiveStarters` gained a real `p` (punter) field alongside the existing `k`. Wired into `result.html`'s box score tables. One disclosed gap: a Defensive TD's own PAT has no real kicker object available in that code path (it belongs to the defense's team, not the drive's offense), so it's excluded from the Kicking line rather than guessed. Full suite: 239 passed, 1 skipped, run twice. See HANDOFF.md for full detail. | `box_score.py`, `drive_sim.py`, `depth_chart.py`, `game_state.py`, `result.html` | M | Sonnet | — |
| **M3** | ~~Stats page redesign~~ **DONE (2026-09-09)** | Team/Player/Coach tabs, sortable columns, a customizable-column chooser (real Figma source: `docs/figma-export/src/app/components/StatsPage.tsx` + `stats/StatColumnChooser.tsx`), translated into this project's existing GET-query-param + full-page-reload pattern (no htmx/framework) rather than the source's React client state. The stat catalog is deliberately trimmed to only fields this engine actually attributes (`season_stats.py`/`defensive_box_score.py`/`TeamRecord`) — no fabricated air-yards/pressure/snap-count columns. Coach tab renders "Coming Soon" (no Coach entity). Export button is a stub alert, per scope. Old fixed Passing/Rushing/Receiving/Defensive leaderboard tables are gone, replaced by the Player tab; Awards Race (a GDD-original addition, not from the Figma export) is unchanged. See HANDOFF.md item 39. | `app/templates/stats.html`, `app/templates/base.html` (new CSS only), `app/main.py`'s stats route | M | Sonnet (session ran at Sonnet, not Haiku — still mechanical, no redesign beyond scope) | — |
| **M4** | ~~Roster page redesign~~ **DONE (2026-09-09)** | Attributes/Stats view toggle, Team Quota badges, Filter/Export controls, embedded depth-chart widget (§10.4.2). Real source: `docs/figma-export/src/app/components/RosterPage.tsx`/`RosterTable.tsx`. | `app/templates/roster.html`, `depth_chart.html` (for the embed) | M | Sonnet | own session |
| **M5** | ~~HOF page redesign + League Record Book/Super Bowl History~~ **DONE (2026-09-09)** | Real `/hof` redesign per GDD Sec 10.4.8: a "Class of Season N Inductees" highlight (diffed against the prior archived season), an "Eligible Candidates" list (past `MIN_HOF_SEASONS`, below the induction threshold, ranked by a disclosed simplified "how close" proxy), filterable/searchable Hall of Fame Members, a League Record Book (top-10 all-time leaders per category from `career_stats()`; Kicking omitted, not archived at the career level), and a Super Bowl History table (champion + top seeds only — runner-up/score/SB MVP aren't archived per-season, disclosed rather than fabricated or built out, since that would mean extending `archive_season()`'s schema). Deliberately made zero changes to `history_store.py` (a concurrent M6 session was actively editing `career_stats()` there) — built entirely by composing its existing public functions. Found and fixed a real bug via its own new tests: the "new this season" diff was returning the PRIOR season's inductee keys unchanged instead of actually diffing them. See HANDOFF.md's M5 session entry, including its own three-way concurrent-session commit-attribution note (mirroring M6's — most of this chunk's code landed via M4's commit `544cf95b`, not its own). | `app/templates/hof.html`, `app/templates/base.html` (new CSS only), `app/main.py`'s hof route | S–M | Sonnet | — |
| **M6** | ~~Player Card Stats tab~~ **DONE (2026-09-09)** | Wired `history_store.career_stats()` (already real, already tested) into the Player Card's Stats panel via a new `_career_stats_for()` helper, keyed the same `(team_abbr, name)` way `career_stats()` itself is. Also added real caching (`career_stats()` was ~230ms uncached against the real 24-season history file, and the card now calls it once per player render) via the same lru_cache-plus-explicit-clear pattern `depth_chart.py` already uses, invalidated by `season_state.start_new_season()`. See HANDOFF.md's M6 session entry, including a real three-way concurrent-session commit-attribution note (the code landed correctly, but bundled into M4's commit `544cf95b` rather than its own). | `app/main.py`'s `_player_card_json`, `base.html`'s modal JS, `history_store.py`, `season_state.py` | S | Sonnet | — |
| **M7** | *(not an MVP chunk — see note)* | Originally drafted as "further DEF-tackle stat-realism calibration" (the disclosed ~2-3x-real gap from item 37) while writing this roadmap, then cut before the table was finalized because closing it for real needs special-teams tackle simulation, which is R2 scope (§4's R2 row) — not something an MVP-scoped session should attempt. The row got deleted but M8 was never renumbered down, leaving this gap. Left as a placeholder rather than renumbering M8, since HANDOFF.md and earlier commits already cite "M8" by that name. | — | — | — | — |
| **M8** | Player Card Contract tab | **Needs your decision before any session touches this** — see §3. | — | S | Sonnet | after decision |

**Total remaining MVP: M8 alone** (Player Card Contract tab), blocked on the decision in §3 — every other MVP chunk (M1-M6) is done.

**Note on concurrent sessions:** while M3 was being built, a separate concurrent session was independently working on M2 (Kicking/Punting box score) in the same local working directory, per this very playbook's own "one chunk = one fresh session" guidance. M3's session found M2's in-progress, uncommitted changes to `drive_sim.py`/`box_score.py`/`depth_chart.py`/`result.html` sitting in the working tree, confirmed they were unrelated to M3 (git-stash-verified the one test failure they caused was pre-existing on clean HEAD), and committed only its own three files rather than sweeping up someone else's in-flight work. If you're running multiple sessions in parallel like this, expect the same — check `git status` for files outside your chunk's Key Files column before committing.

**Update (M4/M5/M6, same day):** a rougher three-way version of the same situation — M4, M5, and M6 all ran concurrently and all three touched shared files (`app/main.py`, `app/templates/base.html`). File-level separation (M2/M3's fix above) doesn't help when the SAME file is shared; M6's session had to split individual diff hunks by hand (`git apply --cached` on a hand-built partial patch) to stage only its own changes. Even that wasn't enough at commit time: M4's session ran its own `git add`/`git commit` in the few-second gap between M6's staging and its own `git commit` call, and M4's commit (`544cf95b`) ended up including M6's already-staged hunks too (code landed correctly either way — nothing lost or corrupted — but M6's changes are attributed to M4's commit message instead of their own; see HANDOFF.md's M6 entry for the full account). M5's own hof_view/helper code got swept into that same `544cf95b` commit for the identical reason (see HANDOFF.md's M5 entry) — M5's own follow-up commit (`f09a73b6`) is mostly a real bug fix plus the template/test work, not the original feature landing. **If you're about to run several genuinely-concurrent sessions against overlapping Key Files** (not just the same repo), know that there is no way to fully guard against this from a single session's side — the best available mitigation is checking `git log`/`git show --stat` immediately after your own commit to confirm what actually landed, not just trusting that your `git add`/`git commit` sequence was atomic against the rest of the working directory. **Also watch for a stash appearing in `git stash list` that you didn't create** — M5's session hit exactly that mid-session (another concurrent session stashed the whole working tree, then unstashed/committed before M5 could act); it's a coordination move by another session, not a local accident, and `git stash apply` (not `pop`, to keep the entry as a backup) is the safe way to recover your own in-flight changes from it.

---

## 3. One decision needed from you before M8

The Player Card's Contract tab is stubbed because there's no contract data model at all — no salary, no years remaining, nothing. Two honest paths:

- **(a) Leave it stubbed until R2's real Contracts system (R4a below) builds it for real.** Consistent with this project's no-fabricated-data rule. Zero work now.
- **(b) Build a lightweight, clearly-disclosed SYNTHETIC contract generator now** — a formula from `overall_rating`/`age`/position (not a real negotiated contract, labeled as such in the UI) — as an MVP stopgap so the tab isn't empty. Small amount of work, but it's fabricated data by another name, just disclosed.

Recommendation: **(a)**. The project's established discipline this whole build has been "real data or an honest stub, never fabricated," and Contracts is coming in R2 regardless — a throwaway synthetic version now is work that gets deleted later. Flag your call in the opening prompt of whichever session picks up M8 (or skip M8 from the MVP list entirely and let R2's R4a chunk close it for real).

---

## 4. R2 (Post-MVP) chunks

Bigger, more architecturally significant. Each of these is genuinely a multi-session build on its own — don't try to do one in a single sitting.

| # | Chunk | Scope | Size | Model |
|---|---|---|---|---|
| **R1** | Injury system | Real in-season injury events tied to `durability`. **Directly synergizes with item 37's rotation.py** — a player going down should just increase the backup's `reliability_factor`/share for the rest of that game, which the rotation math already supports. Do this AFTER M1-M6, before R2/R4/R5 (it'll change how those get built). | L | **Opus** for design (touches rotation.py, box scores, progression, roster pages all at once), Sonnet for implementation |
| **R2** | Return-game simulation | Punt/kickoff return yardage. Unlocks a real (not scoped-narrow) Defensive TD, real special-teams tackle credit (the biggest reason DEF tackles are still ~2-3x real — see `test_stat_realism.py`'s disclosed gap), and completes M2's punt stats. | L | Opus for design, Sonnet for implementation |
| **R3** | Coaching Staff | New `Coach` entity, hiring/firing, real Staff page. Unlocks Coach of the Year (currently impossible — no Coach entity exists). | L | Opus for design, Sonnet for implementation |
| **R4** | Contracts / Free Agency / Trades | Genuinely the biggest single chunk in R2. **Split into three sessions, in order**: R4a Contracts (salary cap, negotiation — also closes M8 for real), R4b Free Agency, R4c Trades. Unlocks real GM Desk content. | XL (3 sessions) | Opus for each sub-chunk's design, Sonnet for implementation |
| **R5** | Draft | Draft classes, draft-day logic, real Draft page. Depends on R4a (rookie contracts) existing first. | L | Opus for design, Sonnet for implementation |
| **R6** | Full penalty catalog | Expand from 7 to the GDD's full dozen-plus types. Mechanical extension of the existing, well-documented pattern in `drive_sim.py`'s Penalty System section. | S–M | Sonnet |
| **R7** | Weather | Weather modifiers (§6.11). | S | Sonnet |
| **R8** | Awards page (dynamic, weekly MVP/OPOY/DPOY/ROY/COY) | Your idea from earlier this session — overlaps with the existing HOF and Stats Awards Race, needs a real scoping conversation before any code (not a "just build it" chunk). Do this scoping as the FIRST five minutes of whatever session picks it up, not blind. | M | Sonnet, after scoping |

**Recommended R2 order:** R1 (injury, synergizes with what's already built) → R2 (return game, unlocks the disclosed DEF-tackle gap) → R3 (coaching) → R4a→R4b→R4c (contracts/FA/trades) → R5 (draft, depends on R4a) → R6/R7 (small, anytime) → R8 (needs its own scoping first).

---

## 5. How to actually run this efficiently (the token-saving playbook)

This session (the one that produced this file) is enormous — every remaining turn in it re-sends its entire history. That's the single biggest thing to avoid going forward.

1. **One chunk = one fresh Claude Code chat.** Don't continue this session for the next chunk. A new chat starts with an empty context window; it only grows with what that chunk actually needs.

2. **Open each new session with a tight, direct prompt** — not "explore the codebase and figure out what to do." Use this template:

   > Read `HANDOFF.md` and `ROADMAP.md`. Implement chunk **[M1/M2/M3/...]** as scoped in ROADMAP.md §2 (or §4). Relevant files: [copy the "Key files" column]. Follow the existing patterns in those files — don't redesign anything not in scope. Run the test suite before committing.

   Naming the exact chunk ID and files means the fresh session doesn't spend tokens re-discovering what this file already tells it.

3. **Match the model to the chunk** (see the tables above):
   - **Sonnet 5** (this session's model) — the right default for most implementation work. Good capability-to-cost balance.
   - **Haiku 4.5** — for mechanical, low-ambiguity chunks where the hard thinking is already done (M3, M4: a real Figma source file just needs translating into the existing template pattern). Meaningfully cheaper; don't pay Sonnet/Opus prices for a translation job.
   - **Opus** — reserve for chunks with real design risk: a novel mechanic touching multiple systems at once (M1, R1, R2, R3, R4, R5's design phase), or untangling a gnarly bug (like this session's stat-realism investigation, which took real iterative reasoning). Costs more per token, but a chunk like that done wrong in Sonnet often costs MORE overall once you count the rework.

4. **Tier your test-verification effort by risk, don't run the full twice-suite for everything:**
   - Engine/stats-affecting chunks (M1, M2, R1-R5): keep the full "run the suite twice" discipline — these can silently corrupt stats the way the box_score.py rushing bug did this session.
   - Pure UI/template chunks (M3, M4, M5, M6, R8): one test run + one live-browser check via the preview tools is enough. Don't burn tokens re-running an 8-minute full suite twice for a template change that can't touch game state.

5. **Bundle small chunks into an already-warm session.** Once a session has HANDOFF.md/ROADMAP.md loaded, the dev server running, and context established, a second small chunk in the same session is cheaper than a second fresh session's startup cost. M5+M6 and R6+R7 are natural pairs.

6. **Don't re-run the stat-realism scratch-audit scripts from this session.** `tests/test_stat_realism.py` is now a permanent, checked-in regression gate — trust it. Only reach for a fresh one-off audit script if you're investigating a genuinely NEW reported anomaly, the way this session's work started.

7. **Point new sessions at real source, don't make them re-derive it.** The Figma export is already extracted to `docs/figma-export/` in the repo — a fresh session should read the specific `.tsx` file for its page, not re-request the zip or guess at layout from screenshots.

8. **Keep chunks scoped exactly as written here — resist scope creep mid-session.** The reason M1 says "no open-field return simulation" is specifically to stop it from silently ballooning into R2's territory. If a session doing M1 starts wanting to build return yardage too, that's the moment to stop and open a fresh R2 session instead, not push through in the same one.

9. **Use `/loop` or extended autonomous work only for chunks that are already well-scoped** (i.e., anything in the tables above). Open-ended "keep improving things" autonomous sessions are the most expensive mode there is, because most of the token spend goes to self-directed exploration rather than building.
