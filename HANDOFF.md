# Franchise Football — Handoff

**Read this first in any new session working on this project.**

## Session state right now (2026-09-06)

Working tree is clean. `docs/gdd-v3-2` is up to date with `origin/docs/gdd-v3-2` as of the start of this stretch of work (the box score commit and a HANDOFF.md update from earlier the same day were already pushed). This session then fixed pass-target variety (item 9's "real gap," see below) — that commit is local-only so far; per the established pattern, check with Brian before pushing (every earlier commit this session was pushed only after he explicitly said yes each time — don't assume that carries forward automatically). All 47 tests pass. No server was left running.

**Also this session:** `.claude/settings.local.json` now sets `permissions.defaultMode: "bypassPermissions"` for this project, at Brian's request ("always allow everything") — routine tool calls no longer prompt for confirmation here.

## Where everything lives

- **Local repo:** `C:\FranchiseFootballGame`
- **GitHub:** https://github.com/palmucciforcitycouncil-droid/franchise-football
- **Working branch:** `docs/gdd-v3-2` — **not `main`**. `main` is a thin, stale early snapshot (Sep 24, 2025). Everything described below lives on `docs/gdd-v3-2`, which has been the working branch all session. Nothing has been merged to `main` or opened as a PR yet — that's an open decision, not done by accident.
- **Design doc (authoritative):** `docs/gdd/Franchise_Football_GDD_v4.2.docx` in the repo. This is the single source of truth for scope/formulas — read it before making design calls. It has a Version History section at the top explaining how it got here (synthesized from 9 previously-separate, never-merged GDD exports).
- **Real roster data (committed to the repo as of 2026-09-06):** `data/raw/rosters/players.csv` and `players_with FA.csv`. Madden-derived, real player names/attributes. Originally kept out of the repo entirely (local-Desktop-only) since the repo's visibility was unclear; now committed as a deliberate choice, confirmed with Brian, on the understanding that this repo is **private** — if it's ever made public, these two CSVs should come out first (copyright/licensing exposure on commercial Madden data). `data/franchise_football.db` (gitignored, still a build artifact) is built from these via `scripts/import_players.py`, which now defaults its `--source-dir` to `data/raw/rosters/`; a fresh clone just needs to run the import with no flags (see below).

## Architecture (decided this session, not inherited)

**One Python process. No REST API, no separate frontend.** FastAPI serves server-rendered Jinja2 templates directly. This was a deliberate reversal of what earlier GDD drafts specified (a FastAPI JSON API consumed by a separately-built JS frontend) — the repo's own history (two abandoned React/Vite rebuilds under the now-archived `_legacy/app/ui/figma*`, and a multi-day "revert to golden" cycle on an unmerged dashboard branch) was the deciding evidence that the API+frontend split was pure coordination overhead for a single-player local game. See GDD v4.1's Version History entry for the full reasoning.

- **Web/HTML:** FastAPI + Jinja2 (`app/templates/`). No htmx yet — current pages use plain HTML forms. Dark/blue/gold theme per GDD §10.2.
- **Player data:** SQLModel + SQLite (`app/models/player.py`, `app/core/db.py`), backed by the real roster import.
- **Season/schedule state:** plain dataclasses (`app/services/season_state.py`) persisted as JSON (`app/services/save_service.py`, `data/saves/current_season.json`, gitignored) — not in the SQL DB. This is intentional; season state is simple enough that JSON save/export (GDD §8) is a better fit than a DB table.
- **`_legacy/`** holds the old, pre-this-session `app/` and `tests/` trees, archived not deleted — an earlier audit found 3+ competing, half-broken simulation implementations in there. Most of it isn't worth resurrecting, but some Post-MVP-adjacent pieces (a trade engine, draft logic) might be salvageable later. Don't build on it without re-verifying it actually runs first — that audit's central finding was that a lot of code in there looked done but had never actually been executed.

## Running it

```bash
cd /c/FranchiseFootballGame
python -m venv .venv                    # if .venv doesn't exist yet
./.venv/Scripts/python.exe -m pip install fastapi uvicorn jinja2 python-multipart python-dotenv sqlmodel pytest httpx
```

Create `.env` with `LEAGUE_SEED=2025` (required — the app fails to start without it, by design, per GDD §1.3's "no DEFAULT_SEED fallback" policy).

**If `data/franchise_football.db` doesn't exist yet** (fresh clone), the app will still start but most routes will crash — you need real player data first:
```bash
./.venv/Scripts/python.exe scripts/import_players.py
```
(The roster CSVs now ship in the repo at `data/raw/rosters/`, so no `--source-dir` flag is needed on a fresh clone. Pass `--source-dir` only if importing from a different export.)

**Run the server** (do this directly via Bash/PowerShell, not the Browser pane's `preview_start` — that tool reads `.claude/launch.json` from the *session's original working directory*, which caused it to launch an unrelated project once this session; safer to just run uvicorn directly and `navigate` to it):
```bash
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```
Then open `http://127.0.0.1:8010/` (single-game simulator) or `http://127.0.0.1:8010/season` (full 18-week season with standings).

**Run tests:**
```bash
./.venv/Scripts/python.exe -m pytest tests/ -v
```
47 tests, all passing as of the last commit. Several are `skipif`-guarded on `data/franchise_football.db` existing (though that's less likely to bite now — the roster CSVs it's built from ship in the repo, see above).

## What's actually built and verified (not just claimed)

Every item below was tested (pytest) *and* verified live in a browser render, per this session's working pattern — the whole reason that pattern exists is that a prior audit found a lot of "looks done" code in `_legacy/` that had never actually been run.

1. **Single-game simulator** (`GET /`, `POST /simulate`) — pick two teams, simulate one game.
2. **Full season** (`GET /season`, `POST /season/simulate-week`, `POST /season/reset`) — real GDD schedule formula (§5.1): 6 divisional + 4 intra-conference rotation (3-yr cycle) + 4 inter-conference rotation (4-yr cycle) + 2 standings-based + 1 "17th game." 17 games/team, 18 weeks, verified against the exact 6/4/4/2/1 breakdown. **Known simplification:** bye weeks aren't confined to the GDD's "weeks 5-14 except 6" window — see `app/engine/schedule.py`'s docstring for why (forcing that window turns week-placement into a much harder problem; bye *timing* doesn't affect any gameplay logic, so this was a deliberate, documented scope cut, not an oversight).
3. **Save/load** — a season survives a server restart. `data/saves/current_season.json`.
4. **Down-by-down Drive Engine** (`app/engine/drive_sim.py`) — real down/distance/field-position sequence, not one dice roll per drive. Includes safety detection, real penalty texture (flat-rate, not the full GDD §6.9 type catalog), a simplified 4th-down go/kick/punt heuristic.
5. **Real roster** — 2,365 players, all 32 teams + 71 free agents, ~50 real attributes each (`app/models/player.py`). GDD §3.1 documents the schema and two deliberate naming decisions (`durability` keeps Madden's own polarity rather than being inverted to match the Post-MVP `injury_proneness` framing; `salary`/`signing_bonus` are stored now even though Contracts is Post-MVP).
6. **Player-level play-calling AI** (`app/engine/player_ai.py`, `app/services/depth_chart.py`) — real starting lineups (top overall_rating per position, since there's no coach-assigned depth chart yet), real zone-based run-blocking advantage (GDD §6.6.2's "LT & LG vs. RDE & RDT," mirrored), real pass-target selection by actual route-running-vs-coverage mismatch, real completion odds from the specific QB/receiver/defender's actual attributes. Play-by-play names real players.
7. **Defensive play-calling AI** (`app/engine/defensive_ai.py`, GDD §6.6.3) — the full four-step process: anticipate the offense (situational baseline + a performance layer from the offense's own in-game YPC/YPA, deliberately blind to the offense's true internal matchup_adjustment, which a real DC can't see), decide blitz (real blitzer-vs-weakest-blocker matchup), decide coverage (Man/Zone by situation), and — when Run Defense is called — a run tactic (Plug Gaps/Contain Edge) predicted from the same zone-blocking math the offense's own play-caller uses. Wired into `drive_sim.py` so the call changes real outcomes (pressure/sack rate, completion odds, run yardage), not just narration; `PlayEvent.defensive_call` carries a human-readable description of each play's call (e.g. "Pass Defense, Blitz (P. Mahomes), Man"). 9 new tests in `tests/test_defensive_ai.py`. Verified live: single-game and a full season week both ran clean with no server errors; combined-score average across a mixed sample dropped from the pre-existing ~63-64 (documented as still above NFL norms) to roughly NFL-realistic territory (~48-55 combined, ~22-26% TD/drive) purely as a side effect of the defense now actually pushing back — not a deliberate calibration pass, so treat that number as encouraging but not authoritative until the real Score Fidelity System (item 3 below) exists.
8. **Play-by-play UI** (`app/templates/result.html`, `base.html`) — the single-game result page's Drive-by-Drive section is now a per-drive `<details>`/`<summary>` (native HTML, no JS) that expands into a down-by-down table: down & distance, ball spot, play description (real player names), and the real defensive call from item 7. Touchdown rows gold, turnover rows red, first-down rows bolded. Added `PlayEvent.drive_number` (set in `game_sim.py`, matches the drive's 1-based index in `GameResult.events`) so Jinja's `selectattr` can group the flat play list back into per-drive tables without a template helper. Verified live in the browser (expanded/collapsed correctly, real blitzer names and coverage calls visible, no horizontal overflow at the normal 720px layout width). The season page's per-week games still don't get this treatment — `season_state.py` only keeps final scores/standings per game, not the full `GameResult`/play list, so a week's individual games aren't inspectable this way yet.
   - **Bug found via this UI, fixed same session:** `_resolve_pass`'s interception branch was returning the intended receiver's name, not the intercepting defender's -- every "Interception (name)" in the play log was naming an offensive player (e.g. "Interception (Stefon Diggs)" for the WR who got picked off *against*, not the DB who made the play). Fixed in `drive_sim.py`; `PlayEvent` gained a `receiver_name` field (the real intended target, independent of who the play gets narrated around) since fixing this meant the interception's receiver name would otherwise be lost entirely -- see item 9, which depends on it.
9. **Box Score** (`app/engine/box_score.py`, wired into the `/simulate` route and `result.html`) — real per-player Passing/Rushing/Receiving stat lines, tallied from the play list rather than parsed from narration text. Because this engine has exactly one active passer and one active rusher per team per game (the single starting QB/HB from `get_offensive_starters` -- no backups/scrambles/substitution modeled), the Passing and Rushing tables are always exactly one row; Receiving has one row per WR/TE actually targeted. Stat conventions follow real NFL box scores, not the simpler Team Totals row already on the page: a sack isn't a pass attempt, a passer's yards exclude sack yardage (Team Totals' "Pass Yards" cell does include it -- the two numbers are expected to differ, that's not a bug), and an interception counts as a target + INT for the receiver without counting as a reception. 6 new tests in `tests/test_box_score.py`. Verified live: real player names, numbers internally consistent (receiving totals sum to the passer's line).
   - **Real gap this surfaced, fixed same session:** every pass in a given single-game simulation went to exactly ONE receiver per team, for the entire game -- Miami's Cedrick Wilson Jr had a 30/30 target share, Buffalo's Stefon Diggs 37/37. Not a box-score bug; `player_ai.py`'s `choose_pass_target` was a pure function of static per-game ratings (route-running vs. coverage) with no randomness, so the same (receiver, defender) pair won the mismatch calculation on literally every pass attempt of the game. Invisible before because play-by-play text alone doesn't make total repetition obvious the way an aggregated box score does. **Fixed:** `choose_pass_target` now does weighted-random selection (softmax over mismatch scores, `rng.weighted_choice`) instead of pure argmax -- the best mismatch still wins most often (a real "primary read," per the GDD's own §6.6.2 wording) but not every play; `distance` tightens the distribution (less exploration) on 3rd/4th & 7+, when a QB going through progressions leans harder on his best matchup to convert. Re-verified live: the same BUF/MIA matchup now shows Cedrick Wilson Jr at 36/48 (down from 30/30) with Tyreek Hill (9) and Jaylen Waddle (3) getting real volume; Buffalo spreads across four receivers instead of one. `test_pass_target_is_the_biggest_real_mismatch` (deterministic) replaced with `test_pass_target_favors_the_biggest_real_mismatch_but_varies` (statistical, same pattern as the existing run-point-of-attack test). 47 tests still pass.

## Known, documented gaps (deliberate, not oversights — see each module's docstring)

- **Defensive play-calling has no real personnel-package model or injury signal yet** — the Nickel/Dime/Base labels implied by §6.6.3's Primary call are cosmetic (`DefensiveStarters` is still a fixed 4-3-ish 11), and Step 1's anticipation has no injury input (no injury system exists — Post-MVP). The decision logic itself (blitz assignment, coverage, run tactic) is real and wired into outcomes — see item 7 above.
- **Season-week games have no play-by-play view** — the single-game simulator's result page now shows full down-by-down detail (item 8 above), but a season week's games only ever existed as final scores in the standings; `season_state.py` doesn't retain the `GameResult`/play list per game, so there's nothing to render there yet even if a route were added.
- **No weather** (GDD §6.11 / Part 2).
- **No full penalty-type catalog** (GDD §6.9) — current penalties are a flat-rate yardage nudge for texture, not real type/accept-decline logic.
- **No dedicated kicker in the starting lineup** — field goals use a league-average probability bucket with an optional small nudge if a kicker object is passed in, but `OffensiveStarters` doesn't have a K slot wired up yet.
- **Calibration is rough, not final** — after switching to player-level formulas, initial output was wildly unrealistic (58-57 average games, 67.6% of drives scoring). Retuned by hand against measured output to ~63-64 combined points / ~30% TD rate — better, but still above real NFL norms. Exact calibration is explicitly the Score Fidelity System's job (GDD §6.2) once that exists; don't hand-tune further without a reason.
- **Contracts, Free Agency, Trades, Coaching Staff, Draft** are all Part 2 (Post-MVP) per the GDD's own scope — not built, not stubbed, intentionally.
- **UI is functional, not polished** — plain HTML forms, no htmx yet (GDD's stated plan). Card modals, sortable/filterable tables, and the other 9 of 11 UI screens (Free Agents, Trading Block, Staff, Draft, Depth Chart, Roster, Stats, Calendar, HOF) don't exist yet — only Dashboard-equivalent (`/`) and a bare-bones Season/standings page exist.

## Recommended next steps (pick one, or suggest your own)

1. **Season-week game inspection** — now that single games have a real play-by-play view + box score (items 8-9), the natural follow-on is making a season week's individual games inspectable the same way; needs `season_state.py` to retain each week's `GameResult`s (or at least the play lists), not just final scores.
2. **Depth Chart / Roster UI pages** — now that real player data exists, a page to actually browse it would make the data visible, not just used internally by the engine.
3. **Score Fidelity System** (GDD §6.2) — real calibration against target scoring distributions. Note: adding the defensive AI already moved combined scoring from ~63-64 toward ~48-55 as a side effect, not a deliberate tune, and the pass-target-variety fix (item 9) likely moves it again (fewer 100%-share receivers means the passing game is less exploitative of a single mismatch) — worth re-measuring before doing real calibration work here.
4. **Merge `docs/gdd-v3-2` toward `main`** — at some point this branch should probably become the real main line; hasn't been done yet, no strong reason not to other than nobody's asked.

## Working patterns this session established (worth keeping)

- **Verify by running, not just reading.** Nearly every real bug found this session (tuning-parameter mismatches, distance-to-go not increasing on a loss, an outcome field silently overwritten, the inter-conference rotation formula breaking for odd season numbers) was caught by actually executing code and checking output, not by code review. Several were in code that "looked correct."
- **Test files exist for exactly this reason** — `tests/test_drive_sim.py`, `tests/test_player_ai.py`, `tests/test_season.py`, `tests/test_player_model.py` all check real invariants (not just "does it run"), several written *because* a manual check caught a bug that a shallower test wouldn't have.
- **Document simplifications where you make them**, in the code, not just in chat — every module above has a docstring explaining what it deliberately doesn't do yet and why. Keep that up.
- **Update the GDD when the implementation reveals the spec needs to change**, don't let them drift apart silently (this happened with §3.1 already, once).
