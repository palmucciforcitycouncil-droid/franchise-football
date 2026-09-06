# Franchise Football — Handoff

**Read this first in any new session working on this project.**

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
31 tests, all passing as of the last commit. Several are `skipif`-guarded on `data/franchise_football.db` existing (the roster DB isn't part of the repo).

## What's actually built and verified (not just claimed)

Every item below was tested (pytest) *and* verified live in a browser render, per this session's working pattern — the whole reason that pattern exists is that a prior audit found a lot of "looks done" code in `_legacy/` that had never actually been run.

1. **Single-game simulator** (`GET /`, `POST /simulate`) — pick two teams, simulate one game.
2. **Full season** (`GET /season`, `POST /season/simulate-week`, `POST /season/reset`) — real GDD schedule formula (§5.1): 6 divisional + 4 intra-conference rotation (3-yr cycle) + 4 inter-conference rotation (4-yr cycle) + 2 standings-based + 1 "17th game." 17 games/team, 18 weeks, verified against the exact 6/4/4/2/1 breakdown. **Known simplification:** bye weeks aren't confined to the GDD's "weeks 5-14 except 6" window — see `app/engine/schedule.py`'s docstring for why (forcing that window turns week-placement into a much harder problem; bye *timing* doesn't affect any gameplay logic, so this was a deliberate, documented scope cut, not an oversight).
3. **Save/load** — a season survives a server restart. `data/saves/current_season.json`.
4. **Down-by-down Drive Engine** (`app/engine/drive_sim.py`) — real down/distance/field-position sequence, not one dice roll per drive. Includes safety detection, real penalty texture (flat-rate, not the full GDD §6.9 type catalog), a simplified 4th-down go/kick/punt heuristic.
5. **Real roster** — 2,365 players, all 32 teams + 71 free agents, ~50 real attributes each (`app/models/player.py`). GDD §3.1 documents the schema and two deliberate naming decisions (`durability` keeps Madden's own polarity rather than being inverted to match the Post-MVP `injury_proneness` framing; `salary`/`signing_bonus` are stored now even though Contracts is Post-MVP).
6. **Player-level play-calling AI** (`app/engine/player_ai.py`, `app/services/depth_chart.py`) — real starting lineups (top overall_rating per position, since there's no coach-assigned depth chart yet), real zone-based run-blocking advantage (GDD §6.6.2's "LT & LG vs. RDE & RDT," mirrored), real pass-target selection by actual route-running-vs-coverage mismatch, real completion odds from the specific QB/receiver/defender's actual attributes. Play-by-play names real players.

## Known, documented gaps (deliberate, not oversights — see each module's docstring)

- **Defensive play-calling isn't its own AI yet** (GDD §6.6.3 — anticipate/blitz/coverage as an explicit decision tree). It's currently folded into the offense's matchup math rather than being a symmetric system.
- **No weather** (GDD §6.11 / Part 2).
- **No full penalty-type catalog** (GDD §6.9) — current penalties are a flat-rate yardage nudge for texture, not real type/accept-decline logic.
- **No dedicated kicker in the starting lineup** — field goals use a league-average probability bucket with an optional small nudge if a kicker object is passed in, but `OffensiveStarters` doesn't have a K slot wired up yet.
- **Calibration is rough, not final** — after switching to player-level formulas, initial output was wildly unrealistic (58-57 average games, 67.6% of drives scoring). Retuned by hand against measured output to ~63-64 combined points / ~30% TD rate — better, but still above real NFL norms. Exact calibration is explicitly the Score Fidelity System's job (GDD §6.2) once that exists; don't hand-tune further without a reason.
- **Contracts, Free Agency, Trades, Coaching Staff, Draft** are all Part 2 (Post-MVP) per the GDD's own scope — not built, not stubbed, intentionally.
- **UI is functional, not polished** — plain HTML forms, no htmx yet (GDD's stated plan). Card modals, sortable/filterable tables, and the other 9 of 11 UI screens (Free Agents, Trading Block, Staff, Draft, Depth Chart, Roster, Stats, Calendar, HOF) don't exist yet — only Dashboard-equivalent (`/`) and a bare-bones Season/standings page exist.

## Recommended next steps (pick one, or suggest your own)

1. **Defensive play-calling AI** — the natural next formula-completeness step, mirrors the offensive work just finished.
2. **Depth Chart / Roster UI pages** — now that real player data exists, a page to actually browse it would make the data visible, not just used internally by the engine.
3. **Score Fidelity System** (GDD §6.2) — real calibration against target scoring distributions, replacing the hand-tuned constants.
4. **Merge `docs/gdd-v3-2` toward `main`** — at some point this branch should probably become the real main line; hasn't been done yet, no strong reason not to other than nobody's asked.

## Working patterns this session established (worth keeping)

- **Verify by running, not just reading.** Nearly every real bug found this session (tuning-parameter mismatches, distance-to-go not increasing on a loss, an outcome field silently overwritten, the inter-conference rotation formula breaking for odd season numbers) was caught by actually executing code and checking output, not by code review. Several were in code that "looked correct."
- **Test files exist for exactly this reason** — `tests/test_drive_sim.py`, `tests/test_player_ai.py`, `tests/test_season.py`, `tests/test_player_model.py` all check real invariants (not just "does it run"), several written *because* a manual check caught a bug that a shallower test wouldn't have.
- **Document simplifications where you make them**, in the code, not just in chat — every module above has a docstring explaining what it deliberately doesn't do yet and why. Keep that up.
- **Update the GDD when the implementation reveals the spec needs to change**, don't let them drift apart silently (this happened with §3.1 already, once).
