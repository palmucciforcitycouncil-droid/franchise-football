\*\*Franchise Football: Game Design Document\*\*



\*\*Version:\*\* 3.2 \*\*Date:\*\* 10/16/25



\# 1\\. Vision \& Core Principles



\*\*1.1. Game Vision \& Scope (MVP → R2)\*\*



\*\*MVP Scope:\*\* A 32-team, NFL-style text-based simulation featuring a deterministic, drive-based engine that produces detailed play-by-play text. The initial release will include team and league top performers, basic depth chart management, standings with a Power Rating system, and a JSON-based save/export function.



\*\*R2 Hooks:\*\* Functionality planned for the second major release includes deeper contract negotiations (bonuses, guarantees), player morale and team chemistry, weather effects, practice squads, injuries, a yearly salary cap, and full off-season systems like trades, free agency, and coaching staff management.



\*\*1.2. Architecture \& Technology Stack\*\*



\*\*Stack:\*\* Python 3.11, FastAPI for the local API, SQLModel/SQLite for data persistence, and pytest for testing (target >85% core sim coverage). Jinja2 is an optional component for UI templating.



\*\*Packaging \& Tooling:\*\* uv or Poetry will be used for package management, with a Makefile providing standardized tasks (make init, make test, make run).



\*\*Repository Layout:\*\* The project is structured with a primary /app directory containing domain logic and services (/engine, /models, /data, /ui), alongside top-level directories for /tests and /scripts. The root directory will also contain standard project files such as pyproject.toml, README.md, and LICENSE.



\*\*1.3. Determinism \& Seeding Policy\*\*



\*\*Single Source of Truth:\*\* A global LEAGUE\_SEED (set via environment variable or config file) is the only top-level seed used by the simulation.



\*\*Legacy Fallback:\*\* If LEAGUE\_SEED is not set, the system will fall back to DEFAULT\_SEED for backward compatibility. New code must not introduce references to DEFAULT\_SEED.



\*\*Derived RNGs:\*\* All randomness must be derived from a deterministic RNG instance created via a helper function like make\_rng(season\_year, week, game\_id, subsystem) where subsystem ∈ {"schedule", "engine", "injuries", "negotiations", "sfs", ...}. Direct calls to random.seed() are prohibited.



\- \*\*Sub-seed Derivation:\*\* Use a deterministic 64-bit hash over (LEAGUE\_SEED, season\_year, week, game\_id, subsystem) (e.g., blake2b→int) to initialize a local random.Random instance per site.

\- \*\*Per-game sub-seed:\*\* game\_seed = stable hash(season\_year, week, game\_id, base\_seed) → 31-bit int.

\- \*\*PBP text seed:\*\* pbp\_text\_seed = stable hash(game\_seed, 0xBEEF) → 31-bit int.

\- \*\*Consumption Order (Drive Engine):\*\* The engine must consume randomness in a fixed order: drive selection → play-type → outcome resolution → stat allocation → clock runoff.



\*\*Reproducibility Contract:\*\* Given the same LEAGUE\_SEED, season year, inputs, and ResolvedConfig, simulation results must be perfectly reproducible across all runs and machines. This means bitwise-identical box\_score and event tape. PBP text wording may vary deterministically (e.g., synonym choice), but the underlying event mapping must remain 1:1.



\## 1.4 Global Error Handling



Standard JSON Error Envelope:



{ "error": { "code": "\&lt;UPPER\_SNAKE\&gt;", "message": "Human-readable message", "context": { ...optional... } } }



Common Codes: INVALID\_FIELD, OUT\_OF\_RANGE, UNAUTHORIZED, SIM\_LOCKED, NOT\_FOUND, RATE\_LIMITED, INTERNAL.



UI Mapping: All errors render a toast; when modal-scoped, also show an inline banner.



Never Throw: Diagnostics endpoints return HTTP 200 with status = "error" in body to preserve observability.



Logging: Errors are logged once (structured log) with a stable event name and compact context.



\# 2\\. Configuration \& Diagnostics



\## 2.1 Safe Configuration \& Calibration System



2.1.1 Functional Description



Purpose: Provide a fault-tolerant, deterministic, and transparent configuration \& calibration pipeline that every sim engine consumes. It composes multiple sources into one ResolvedConfig that is safe to use in production and testable in CI.  

Key Properties:



\- No hard crashes from missing/invalid files; system degrades to defaults and logs WARNs.

\- Deterministic: same seed + same resolved config ⇒ identical outputs.

\- Layered deep-merge with explicit precedence and provenance.

\- Validation + clamping + normalization to enforce safe inputs.

\- Versioned via schema\_version for future evolution.

\- Observable via diagnostics endpoints (final values + sources + SFS deltas).



Primary Consumers: Engines: pbp, sim\_v2, sim\_v3, sim\_v4. Systems: SFS, Power Ranking (UI "Power Rank"), awards thresholds, dashboard widgets that require league constants.



2.1.2 User Experience Summary



On boot, the game loads defaults, applies snapshots/overrides, validates, and exposes the final config.  

If a file is missing or a value is out of bounds, the app runs anyway, logging a single-line WARN and listing auto-corrections on /diag/calibration.  

Developers/QA can view the exact merged config and its source layer for each key.



2.1.3 Configuration Model



a) Schema Version  

All JSON configs include "schema\_version": "mvp-1". Unknown versions: soft ERROR (WARN), loader falls back to defaults + best-effort merge and continues.



b) Sources \& Precedence (low → high)



\- Builtin Defaults (in code; always present)

\- Calibration Snapshot (frozen JSON), e.g., ...\\\\data\\\\model\\\\calibration\\\\base\_2025.json

\- Engine Overrides (optional), e.g., ...\\\\data\\\\model\\\\calibration\\\\engine\\\\sim\_v4.json

\- Environment Variables (namespaced), e.g., FF\_\\\_ENGINE\_\\\_SIM\_V4\_\\\_PACE=1.05

\- Runtime Overrides (developer/QA toggles via API; non-persistent unless exported)



Higher wins on conflicts. Provenance maps each final key to its winning layer.



c) Namespacing  

Top-level keys use lower\_snake\_case. Engine-specific values live under engine.\&lt;name\&gt;.\\\* (e.g., engine.sim\_v4.clock.decay\_rate, engine.sim\_v3.play\_composition.run).



d) File Layout (Windows example)



\- Repo root: C:\\\\Users\\\\bpalm\\\\Documents\\\\franchise-football\\\\

\- Calibration: ...\\\\data\\\\model\\\\calibration\\\\\\\*.json

\- Engine overrides: ...\\\\data\\\\model\\\\calibration\\\\engine\\\\sim\_vX.json



2.1.4 Deep-Merge Semantics



a) Dictionaries (objects) - Deep by key; recurse into child dicts. Scalar conflicts: higher layer replaces lower layer.  

b) Arrays (lists) - Replace entire array by default (prevents accidental drift). Opt-in strategies via sibling metadata on the same object:



\- \\\_\_meta.merge\_strategy = "concat" → concatenate arrays.

\- \\\_\_meta.merge\_strategy = "by\_id" → arrays of objects keyed by "id"; merge by id (dict-merge element), append new ids.  

&nbsp;   c) Scalars - Higher replaces lower, then value is validated/clamped.



2.1.5 Validation, Clamping, Normalization



a) Severity Levels



\- INFO: Optional key missing → default applied.

\- WARN: Out-of-range numeric / invalid enum → clamped/coerced; original logged.

\- ERROR (soft): Unknown schema\_version → default+best-effort merge; continue.



b) Canonical Ranges (MVP)



\- Probabilities: \\\[0.0, 1.0\\]

\- Pace multipliers: \\\[0.5, 2.0\\]

\- Aggression sliders: \\\[0, 100\\]

\- Quarter share vector (len=4): each ≥ 0, normalized to 1.0

\- Run/Pass composition: ≥ 0, normalized so run+pass = 1.0

\- Power ranking base (ELO proxy for UI): \\\[1000, 2000\\]



c) Determinism  

rng.seed must be integer; default DEFAULT\_SEED = 2025 if missing. All engines receive the same resolved rng block.



2.1.6 Calibration \& SFS (Score Fidelity System)



a) Snapshots - Frozen, human-readable JSONs in data/model/calibration/. Include schema\_version and date in filename. Used as CI baselines.  

b) SFS Smoke-Check Algorithm - Collect weekly league totals → compute mean\_ppg, quarter\_shares (Q1..Q4 proportion of total points), play\_type\_comp (run vs pass share). Compare each metric to targets (sfs.targets.\\\*) with tolerances in §2.1.6.c. Record pass/fail and deltas; expose under /diag/calibration → sfs.last\_check.  

c) Targets \& Tolerances (MVP)



\- Mean PPG: absolute difference ≤ 0.7.

\- Quarter Shares: relative delta ≤ 10%.

\- Run/Pass Composition: absolute delta ≤ 2 percentage points.



2.1.7 Formulas



\- Normalize Vector v: Let S = sum(v\_i). If S = 0, set v′ uniform; else v′\\\_i = v\_i / S.

\- Relative Delta (shares): Δ\_rel = |x − x\_target| / max(ε, x\_target) with ε = 1e−6; accept if Δ\_rel ≤ 0.10.

\- Absolute Delta (composition, percentage points): Δ\_pp = |x − x\_target|; accept if Δ\_pp ≤ 0.02.

\- Constants: DEFAULT\_SEED = 2025, SCHEMA\_VERSION = "mvp-1", TOL\_PPG = 0.7, TOL\_QTR\_REL = 0.10, TOL\_COMP\_PP = 0.02.



2.1.8 Algorithms \& Pseudocode (inline)



High-Level Load, Merge, Validate Flow



\- Load defaults → try snapshot → apply engine overrides → apply env → apply runtime.

\- Deep-merge in that order with provenance tracking.

\- Validate / Clamp / Normalize (ranges, enums, vectors).

\- Produce ResolvedConfig (immutable) plus provenance map.

\- Expose via diagnostics; inject into engines.



Pseudocode: load\_resolved\_config(paths, env, runtime\_overrides)



Build sources map with keys:



"default" = load\_builtin\_defaults();



"snapshot" = try\_load\_json(paths.snapshot);



"engine" = try\_load\_json(paths.engine\_override);



"env" = load\_from\_env(env);



"runtime" = runtime\_overrides or {}.



Initialize resolved = {}, provenance = {}.



For each layer in order \\\["default","snapshot","engine","env","runtime"\\]:



If cfg exists: (resolved, provenance) = deep\_merge(resolved, cfg, provenance, layer).



resolved = validate\_and\_clamp(resolved).



Ensure resolved\\\["schema\_version"\\] exists; set to "mvp-1" if missing.



Return ResolvedConfig(resolved, provenance).



Pseudocode: deep\_merge(base, overlay, prov, layer)



For each key k, value v in overlay:



If v is dict and base\\\[k\\] is dict:



recursively deep\_merge(base\\\[k\\], v, prov, layer).



Else if v is list and base\\\[k\\] is list:



strategy = overlay.get("\\\_\_meta", {}).get("merge\_strategy", "replace").



base\\\[k\\] = merge\_lists(base\\\[k\\], v, strategy).



prov\\\[k\\] = layer.



Else:



base\\\[k\\] = v



prov\\\[k\\] = layer



Return base, prov.



Pseudocode: validate\_and\_clamp(cfg)



If sfs.targets.quarter\_shares present: normalize to sum 1.0.



If engine.sim\_v4.play\_composition present: normalize run/pass so run+pass=1.0.



Clamp sliders: engine.sim\_v4.off\_aggression, def\_aggression in \\\[0,100\\]; engine.sim\_v4.pace in \\\[0.5,2.0\\].



Seed: set rng.seed to int(rng.seed or 2025).



Return cfg.



2.1.9 Data Exposure \& Diagnostics



\- GET /diag/health: 200 OK + minimal status, including config load summary.

\- GET /diag/calibration:

&nbsp; - resolved\_config (read-only snapshot)

&nbsp; - provenance (key-path → layer)

&nbsp; - sfs.last\_check (deltas + pass/fail for PPG, quarter shares, composition)

&nbsp; - schema\_version, paths\_used (snapshot/override filenames)



2.1.10 Acceptance Tests (CI)



\- Missing Files Robustness: Remove snapshot/overrides → app boots; /diag/health 200; /diag/calibration shows defaults and empty provenance for absent layers.

\- Deep-Merge Correctness: Dicts deep-merge; arrays replace by default; arrays honor concat and by\_id.

\- Validation/Clamping: Feed out-of-range values → clamped; vectors normalized; WARNs logged.

\- Determinism: Same seed + same resolved config ⇒ identical outcomes across two runs for a fixed test fixture.

\- SFS Tolerances: 1-week smoke and 3-week mini-run within tolerance; deviations produce WARNs with numeric deltas.

\- Provenance: For a known overridden key, /diag/calibration shows highest-precedence layer (runtime over env over engine over snapshot over default).



2.1.11 Design Decisions \& Rationale



\- Engine-agnostic core with per-engine overrides keeps shared truth while allowing specialization.

\- Replace-by-default arrays prevent silent, unintended drifts; opt-in strategies cover advanced needs.

\- Clamping and normalization favor continuity (no crashes) while keeping the sim inside sane bounds.

\- Schema versioning provides a stable evolution path.

\- Diagnostics with provenance enable fast debugging and trust in calibration.

\- Frozen snapshots ensure reproducibility across machines and over time.



\## 2.2 Diagnostics, Telemetry \& Testing



2.2.1 Functional Description



Provide a browser-accessible diagnostics surface and local telemetry for developers/QA to verify health, module readiness, and calibration state:  

Endpoints:



\- /diag/health - liveness/readiness + build/version/seed.

\- /diag/modules - per-module readiness with reasons.

\- /diag/calibration - resolved config, provenance, SFS results.  

&nbsp;   Telemetry/Reporting:

\- Structured JSON logs (local-only), rotated by size/time, no PII.

\- Export bundle (zip) containing snapshot diagnostics + recent logs.  

&nbsp;   Goals: determinism, low overhead, stable schemas, and clear pass/fail signals suitable for CI.



2.2.2 User Experience



Visit /diag/health to see green/degraded/error plus details (build, schema, seed, server time, uptime).  

/diag/modules lists each module with status, last-checked time, and reason if degraded/offline.  

/diag/calibration shows the final merged configuration, the source layer for each key, and SFS tolerances/deltas with pass/fail.  

A "Download Diagnostics" control (UI stub) triggers an export bundle with the three JSON payloads and recent log files.



2.2.3 Shared Envelope (All Diagnostics)



Present on every diagnostics response:  

timestamp\_utc (RFC3339), build\_id, sim\_version, schema\_version, sim\_run\_id (UUID per app boot), rng\_seed (int), server\_time\_offset\_ms, instance\_id (short host id), status ("ok", "degraded", "error").  

Status is the worst-of constituent checks: "error" > "degraded" > "ok".



2.2.4 Endpoints \& Payloads



a) /diag/health (GET · always 200; status reflects health)  

Purpose: liveness + readiness snapshot.  

Fields (in addition to the shared envelope):



\- uptime\_s (float since process start), ready (bool)

\- weeks\_simulated (int), current\_week (1-18), games\_simulated (int)

\- db ("ok"|"degraded"|"missing"), storage\_paths\_ok (bool), templates\_ok (bool)

\- notes (array of short strings)  

&nbsp;   Readiness rule (MVP): ready == true iff SQLite is open, required data directories exist and are writable, templates directory is present, and RNG seed is set; otherwise status is "degraded" or "error" with reasons.



b) /diag/modules (GET · 200)  

Purpose: granular module readiness.  

Fields: shared envelope +  

modules: array of { name, version, status, checked\_at\_utc, reason?, extra? }.  

Canonical module list (MVP): engine.sim\_v3, engine.sim\_v4, pbp, db.sqlite, storage.filesystem, api.fastapi, ui.templates, scheduler (if present), telemetry.  

Statuses: "ok", "degraded", "offline".



c) /diag/calibration (GET · 200; never throws)  

Purpose: visibility into ResolvedConfig, provenance, and SFS.  

Fields: shared envelope +



\\- imports (optional): per-file summary { file, rows\_read, inserted, updated, skipped, errors } and a path to the latest rejects CSV (see §3.6.8).



\- resolved\_config (nested JSON; no secrets)

\- provenance (key-path → default|snapshot|engine|env|runtime)

\- paths\_used with snapshot?, engine\_override?

\- sfs:

&nbsp; - targets: { ppg\_mean: float, quarter\_shares: \\\[4\\], composition: { run: float, pass: float } }

&nbsp; - last\_check: { window: "week"|"3weeks", pass: bool, deltas: { ppg\_mean: float, quarter\_shares\_rel: \\\[4\\], composition\_pp: { run: float, pass: float } } }

&nbsp; - tolerances: { ppg\_abs: 0.7, quarter\_rel: 0.10, composition\_pp: 0.02 }

&nbsp; - \\- save\_meta (optional): schema\_version, last\_save\_time\_utc, checksum\_short, and migration\_status (see §3.11).



2.2.5 Modules \& Readiness Criteria



Each module implements a fast self-check:



\- engine.sim\_v4: accepts a minimal fixture and returns a deterministic box score under 200 ms.

\- db.sqlite: file exists; open succeeds; one basic query completes.

\- storage.filesystem: calibration and saves directories exist and are writable.  

&nbsp;   Status mapping:

\- ok: all checks pass within time budget.

\- degraded: running with defaults/fallback or slow but functional.

\- offline: critical resource missing.



2.2.6 SFS Attachment (Rules)



After each weekly simulation, compute and attach to /diag/calibration.sfs.last\_check:



\- Mean PPG: absolute diff ≤ 0.7 passes.

\- Quarter shares: relative delta per quarter ≤ 10% passes.

\- Run/Pass composition: absolute delta per key ≤ 0.02 passes.

\- pass == true only if all three group checks pass.



2.2.7 Telemetry \& Reporting



a) Structured Logs (local-only, MVP)  

Format: one JSON object per line.  

Common fields: ts\_utc, level (INFO|WARN|ERROR), event, sim\_run\_id, req\_id?, game\_id?, team\_id?, module, msg, data (object).  

Rotation: size-based (e.g., 5 MB) and daily; keep last N files (e.g., 7).  

Location: …\\\\data\\\\logs\\\\.  

Privacy: no PII, no OS usernames, no raw paths outside project root.



Retention: keep logs for \*\*7 days\*\*; individual file cap \*\*5 MB\*\*, rotate up to \*\*5\*\* files per stream. /diag/export bundle cap \*\*10 MB\*\*.



b) Event Catalog (MVP)



\- engine.sim\_week\_complete - { week, games\_simulated, duration\_ms, sfs\_pass }

\- engine.game\_simulated - { game\_id, week, duration\_ms, score: { home, away } }

\- config.resolved - { sources: \\\["default","snapshot","engine","env","runtime"\\], keys\_overridden: int }

\- diag.export\_created - { path, size\_bytes, files\_included }



c) Export Bundle  

API: /diag/export (GET) generates a zip with:



\- health.json, modules.json, calibration.json

\- Last K log files (e.g., 3)  

&nbsp;   Rate-limit: at most once per 10 seconds.



2.2.8 Performance \& Limits



\- Endpoint median latency < 20 ms on warm process.

\- /diag/calibration payload ≤ 100 KB uncompressed.

\- Telemetry writes are non-blocking; background flush/rotation.

\- Rate-limit diagnostic endpoints to 5 req/sec per IP (HTTP 429 if exceeded).



2.2.9 Algorithms \& Pseudocode (inline, copy-friendly)



Envelope builder (used by all endpoints)  

Input: array of sub-statuses ("ok"|"degraded"|"error"), versions, seed.  

Compute status as worst-of: "error" > "degraded" > "ok".  

Capture: timestamp\_utc, build\_id, sim\_version, schema\_version, sim\_run\_id, rng\_seed, server\_time\_offset\_ms, instance\_id, and computed status.  

Return the envelope dict.



/diag/health flow  

Run quick checks for DB open, directory existence/writability, template path, RNG seeded.  

Compute uptime, weeks/games from league state.  

Decide readiness per rule; set envelope status.  

Return envelope plus health fields.



2.2.10 CI Acceptance Tests



\- Health baseline: with only defaults, GET /diag/health returns 200 and reports accurate readiness.

\- Modules grid: force missing template path → ui.templates="offline" with reason; envelope becomes "degraded".

\- Calibration visibility: with snapshot + engine override, /diag/calibration shows resolved\_config, correct provenance winners, and real paths\_used.

\- SFS pass/fail: provide an out-of-tolerance fixture week; endpoint shows pass=false with numeric deltas.

\- Logging \& rotation: exceed size threshold; rotation produces multiple files; export bundle contains correct files.

\- Rate limits: hammer /diag/export; receive 429 with Retry-After.



2.2.11 Design Decisions \& Rationale



\- Separate, purpose-built endpoints keep payloads clear, cacheable, and fast.

\- A shared envelope standardizes observability.

\- Local-only telemetry reduces privacy risk and friction.

\- Provenance for calibration keys dramatically shortens root-cause time for config issues.

\- Strict performance budgets ensure diagnostics won't stall gameplay or tests.



\## 2.3 User Role \& Permissions (MVP)



2.3.1 Scope



Single-user, single-team control.



2.3.2 Permissions \& Timing Guardrails



\- Controlled Team: Only the human-controlled team may perform roster/contract actions (sign, release, deactivate, depth-chart edits).

\- Timing: Management actions are allowed only between simulated weeks (i.e., not during an active game tick or game simulation).

\- Locked During Games: While any game is simulating, roster/contract buttons are disabled and show a tooltip: "Locked during live simulation.

\- All confirmation dialogs and destructive actions follow \*\*§7.10 Accessibility and UI Fallbacks\*\*.



2.3.3 Commissioner (Debug) Toggles



Advance Week, Force Injury Off, Reset Stats Cache (hidden behind Dev Mode flag).



2.3.4 Audit Trail (MVP-light)



Every management action logs a timestamp, user team id, and a short description to the save file under admin\_log.



\# 3\\. Data Models \& Schemas



This section is the single source of truth for IDs, data types, and keys used across the simulation, API, and tests.



\## 3.1. Core Entities



\*\*3.1.1. IDs \& Conventions\*\*



\- \*\*IDs:\*\* All primary keys end in "\\\_id" (team\_id, player\_id, game\_id).

\- \*\*Types (conceptual):\*\* integers for IDs and counters; strings for names/enums; whole numbers 0-99 for ratings.

\- \*\*Naming:\*\* Use real NFL team names and locations.

\- \*\*Determinism:\*\* All randomness derives from LEAGUE\_SEED (see Determinism policy).

\- \*\*Ranges:\*\* Ratings 0-99; ages 18-55.

\- \*\*Timestamps:\*\* Not required for MVP.



\*\*3.1.2. Team\*\*



Minimal fields required by schedule, standings, sim, and UI.



\- team\_id (int)

\- location\_name (string) // e.g., "Boston" (no nicknames/logos)

\- conference (string: AFC|NFC)

\- division (string: East|North|South|West)

\- wins (int)

\- losses (int)

\- ties (int, default 0; reserved even if engine forces a winner)

\- points\_for (int)

\- points\_against (int)

\- power\_rating (int) // Elo-like rating exposed in UI as "Power Ranking"



\*\*3.1.3. Player\*\*



Fictional names only; ratings 0-99 unless noted. (No coaches/injury systems in MVP.)



\- player\_id (int)

\- team\_id (int)

\- first\_name (string)

\- last\_name (string)

\- position (string, e.g., QB, RB, WR, …)

\- age (int, 18-55)

\- morale (int, 0-99)

\- stamina (int)

\- injury\_proneness (int) // kept as a static attribute; no injury system in MVP

\- potential (int)

\- awareness (int)

\- speed (int)

\- strength (int)

\- agility (int)

\- throw\_power (int)

\- throw\_accuracy (int)

\- catching (int)

\- tackling (int)

\- contract\_years (int, MVP: 0-3)

\- contract\_salary\_aav (int, yearly salary in \\$)



\*\*3.1.4. Schedule \& Games\*\*



LeagueState holds the season schedule and game results.



\- season\_year (int)

\- weeks: list of Week (18 entries)

\- Week: week\_number (1-18), games: list of GamePairing

\- GamePairing: game\_id (int), week\_number (int), home\_team\_id (int), away\_team\_id (int), date\_hint (string, optional), bye (bool, default false)

\- GameResult (persist when played):

\- game\_id (int), week\_number (int), home\_team\_id (int), away\_team\_id (int)

\- home\_score (int), away\_score (int)

\- score\_by\_quarter\_home: \\\[Q1,Q2,Q3,Q4\\]

\- score\_by\_quarter\_away: \\\[Q1,Q2,Q3,Q4\\]

\- team\_lines: {home: {plays, yards, turnovers}, away: {plays, yards, turnovers}}

\- player\_lines: minimal per-player lines for headline stats (MVP subset)

\- pbp\_log: ordered list of PbpEvent (see 3.2)

\- metadata: rng\_subseed (int), engine\_version (string)



\*\*3.1.5. Standings Snapshot (derived, saved for exports)\*\*



\- team\_id, wins, losses, ties, points\_for, points\_against, power\_rating, conference\_rank, division\_rank



\*\*3.1.6. Awards (MVP scope: season-end only)\*\*



\- award\_id, season\_year, category (MVP, OPOY, DPOY, ROY, COTY, GMOTY), winner\_player\_id or winner\_coach\_id, team\_id



\*\*3.1.7. Alignment Notes\*\*



\- Schedule format matches 18-week/17-game regular season; bye weeks represented as Week entries without a GamePairing for that team.

\- "Power Ranking" is the Elo-like power\_rating used in standings.

\- Contracts are MVP-simplified (AAV + years only).

\- Detailed per-game PBP is part of MVP and drives the UI's 10-line scrolling panel.



\*\*3.1.8. Depth Chart (MVP)\*\*



Purpose: Define a single source of truth for how teams assign starters and backups by position, what counts as an eligible player, how the "Auto Best" button works, how depth is persisted, and what minimums/actives are enforced in the MVP.



Scope: MVP. Deterministic. No scheme-specific sub-roles (e.g., no 3-4 vs 4-3 specialization). Uses the large attribute set. See §9.2.2 for Roster/Depth Chart UI.



Assumptions:



\- Personal use build; real NFL labels permitted locally.

\- Coaches exist in MVP but on-field effects may be zeroed; depth chart logic is not coach-modified in MVP.

\- Salary cap and contracts are simple AAV MVP; depth chart changes do not modify contracts.



3.1.8.1. Position Buckets and Depth Targets (MVP)



Offense



\- QB: 3

\- RB: 3

\- FB: 2

\- WR: 4

\- TE: 3

\- LT: 2

\- LG: 2

\- C: 2

\- RG: 2

\- RT: 2

\- K: 1

\- P: 1



Defense



\- EDGE (outside rushers): 3

\- IDL (interior DL): 3

\- LB (off-ball): 4

\- CB: 4

\- S (FS/SS pooled): 3



Special Teams Roles



\- KR (kick returner): 1

\- PR (punt returner): 1

\- LS (long snapper): 1



Notes



\- OL tracked by true spots (LT/LG/C/RG/RT). Defense uses buckets (EDGE/IDL/LB/CB/S) for MVP simplicity.

\- KR/PR/LS are roles, not roster positions; they are filled from eligible players.



3.1.8.2. Eligibility and Availability Rules



Health and Status



\- Ineligible: suspension = true; injury\_status in {OUT, IR}.

\- Questionable/Probable: eligible for non-starting depth only if healthy options are insufficient; see the fill algorithm.

\- RTP (return-to-play): allowed but de-prioritized after healthy players.



Position Eligibility



\- Primary position is always eligible.

\- Secondary position eligibility allowed with a −3 OVR penalty for ranking.

\- Equivalency map (additive to any explicit "secondary\_positions" on the player):

&nbsp; - T ↔ G; G ↔ C; C ↔ G; T ↔ T (L/R interchangeability treated within the −3 penalty; soft −1 nuance is implied)

&nbsp; - EDGE ↔ LB

&nbsp; - CB ↔ S (penalty applies)

&nbsp; - WR ↔ RB (penalty applies)

\- LS preference: any OL, best by awareness then strength. Non-OL may fill with −4 penalty if no OL available.



3.1.8.3. Sorting and Tie-Breakers (Deterministic)



Primary key



\- Role score (defined below).



General tie-breakers (in order)



\- awareness (descending)

\- stamina (descending)

\- age (ascending)

\- player\_id (ascending, deterministic final key)



Role score by group



\- All positions except KR/PR/LS: role\_score = OVR (apply −3 if not primary position).

\- KR/PR: role\_score = 0.6\_speed + 0.3\_agility + 0.1\\\*awareness (ignore OVR here).

\- LS: role\_score starts from OVR; add +2 if position in {C, G, T}; if non-OL, subtract 4.



3.1.8.4. "Auto Best" Algorithm (Per Position, Deterministic)



Overview: Fills each position's depth from best to worse following eligibility, injuries, and tie-breakers, ensuring players are not double-assigned to two starting roles.



Steps



\- Build candidate list for the position:

&nbsp; - Include players with primary position = this position.

&nbsp; - Include players with explicit secondary\_positions containing this position.

&nbsp; - Include players eligible via the equivalency map.

&nbsp; - Exclude suspended; exclude OUT/IR from starting slots.

\- Compute role\_score for each candidate.

\- Sort candidates by:

&nbsp; - role\_score (desc), then awareness (desc), stamina (desc), age (asc), player\_id (asc).

\- Fill slots up to the target count:

&nbsp; - Prefer healthy (no OUT/IR).

&nbsp; - If insufficient, allow Questionable/Probable to fill remaining slots.

&nbsp; - As last resort, allow OUT/IR only if position would otherwise be empty (mark "Needs Attention").

\- Prevent duplicate starting assignments:

&nbsp; - If a player would start at two positions, keep the assignment with the higher role\_score and refill the other from the next best candidate.

\- Special roles:

&nbsp; - KR and PR rank by the KR/PR role\_score only.

&nbsp; - LS prefers OL by awareness → strength; otherwise penalize non-OL and select best available.



Outputs



\- Updated team depth\_chart structure (see §3.1.8.6).

\- Optional "Needs Attention" list if any starting slot is filled by non-healthy or left empty.



3.1.8.5. UI Behavior and Acceptance Criteria (Roster Page)



Controls



\- "AUTO Depth Chart" button above roster table actions.

\- Optional confirm: "Overwrite current depth chart with best available players?" \\\[Confirm\\] \\\[Cancel\\].

\- States: normal → running (spinner) → success (checkmark) or error (toast).



Acceptance Criteria



\- One click assigns every position's depth per §3.1.8.4.

\- First column and header remain visible while viewing long rosters (sticky header/first column).

\- No player occupies two starting roles after auto-fill.

\- KR/PR/LS show assigned players.

\- If any position cannot reach target depth with healthy players, show a "Needs Attention" list by position.

\- Persist changes immediately; refresh shows the same assignments.



3.1.8.6. Data Model and Persistence



Depth chart shape (per team)



\- Key: position code ("QB", "RB", "WR", etc.) or role ("KR", "PR", "LS").

\- Value: ordered array of player IDs (strings) from starter to backups.



Example JSON  

{  

"QB": \\\["101","245","390"\\],  

"RB": \\\["312","448","229"\\],  

"FB": \\\["517","-"\\],  

"WR": \\\["901","777","654","433"\\],  

"TE": \\\["120","308","441"\\],  

"LT": \\\["210","592"\\],  

"LG": \\\["219","612"\\],  

"C": \\\["221","-"\\],  

"RG": \\\["227","-"\\],  

"RT": \\\["233","-"\\],  

"K": \\\["701"\\],  

"P": \\\["702"\\],  

"EDGE": \\\["320","321","322"\\],  

"IDL": \\\["330","331","332"\\],  

"LB": \\\["340","341","342","343"\\],  

"CB": \\\["350","351","352","353"\\],  

"S": \\\["360","361","362"\\],  

"KR": \\\["901"\\],  

"PR": \\\["777"\\],  

"LS": \\\["221"\\]  

}



Notes



\- Use "-" (or omit) for unfilled backups if necessary; UI renders as empty.

\- Persist deterministically; do not use RNG in Auto Best.



3.1.8.7. API (Optional in MVP; otherwise client-side only)



If wiring server now:



\- POST /api/teams/{teamId}/depth-chart:auto

&nbsp; - Request: { "scheme": null }

&nbsp; - Response: { "depthChart": {…}, "warnings": \\\["Needs Attention: C"\\] }

\- GET /api/teams/{teamId}/depth-chart → current object.

\- PUT /api/teams/{teamId}/depth-chart → save updated object.



3.1.8.8. Roster Limits and Gameday Actives (MVP Enforcement)



Roster size (regular season)



\- Team max roster: 53.



Gameday actives (simple MVP rule)



\- Default: 46 active.

\- Optional 48-active rule: if a team dresses ≥8 OL, allow 48.

\- MVP toggle: "enforce\_gameday\_actives" = false by default (UI may show counts; enforcement can be enabled later).



Minimums (soft guidance; warn if below, don't block in MVP)



\- QB ≥ 2, OL ≥ 8, K = 1, P = 1, CB ≥ 4, S ≥ 3, LB ≥ 4, IDL ≥ 3, EDGE ≥ 3.



3.1.8.9. Validation and Warnings



On save or Auto Best completion



\- Warn if a position's starter is OUT/IR.

\- Warn if KR/PR/LS are unassigned.

\- Warn if team falls below position minimum guidance.

\- Provide a single "Needs Attention" banner listing all issues.



3.1.8.10. Determinism and Seeds



\- Auto Best uses no RNG. Sorting/tie-breakers ensure identical output given identical inputs.

\- Depth chart persistence is part of deterministic league state; save/load reproduces assignments exactly.



\## 3.2. Detailed Play-by-Play (PBP) Schema



\*\*PbpEvent\*\* (appended to GameResult.pbp\_log in order)



\- idx (int, 0-based event index)

\- clock (string, "Q1 12:34")

\- down\_distance (string, e.g., "2nd \& 7 at HOU 43")

\- offense\_team\_id (int), defense\_team\_id (int)

\- description (string, human-readable text line)

\- outcome (string enum: GAIN|LOSS|INCOMPLETE|TD|FG\_GOOD|FG\_MISS|PUNT|TURNOVER|PENALTY|TWO\_PT\_GOOD|TWO\_PT\_FAIL|SAFETY|KNEEL|SPIKE|END\_QTR|END\_GAME)

\- yards (int, may be 0 or negative)

\- new\_spot (string, e.g., "NYG 27")

\- drive\_id (int)

\- scoring\_delta\_home (int), scoring\_delta\_away (int) // event-level scoring impact

\- ep\_before (int), ep\_after (int) // expected points, integer-scaled

\- subs (optional compact changes, e.g., QB change)



\*\*Notes:\*\*



\- The UI PBP panel reads pbp\_log in order, always showing the last 10 lines by default with scroll for history.

\- Scoreboard and score\_by\_quarter are derived live from pbp\_log totals during simulation and stored in GameResult at finalization.



\## 3.3. API Payloads (DTOs)



Data Transfer Objects (DTOs) define the compact shapes returned by the API to the UI.



\- \*\*TeamDTO\*\* (standings/list)

\- team\_id, location\_name, conference, division

\- record: wins, losses, ties

\- pf, pa, power\_rank (int, derived from power\_rating)

\- \*\*PlayerCardDTO\*\* (modal)

\- player\_id, team\_id, name, position, age, morale

\- core\_attributes: speed, strength, agility, awareness

\- role\_attributes: throw\_power, throw\_accuracy, catching, tackling, stamina, injury\_proneness, potential

\- contract: years, aav

\- season\_stats (subset), career\_stats (subset)

\- \*\*ScheduleWeekDTO\*\*

\- week\_number

\- games: \\\[ { game\_id, home\_team\_id, away\_team\_id, has\_result (bool), home\_score?, away\_score? } \\]

\- \*\*GameSummaryDTO\*\*

\- game\_id, week\_number, home\_team\_id, away\_team\_id

\- score\_by\_quarter\_home, score\_by\_quarter\_away

\- team\_lines: plays, yards, turnovers (home/away)

\- leaders: {passing, rushing, receiving, defense} (player\_id + headline stats)

\- \*\*GamePbpDTO\*\*

\- game\_id

\- pbp: list of { idx, clock, down\_distance, description, outcome, yards, new\_spot, scoring\_delta\_home, scoring\_delta\_away }

\- \*\*AwardsDTO\*\*

\- season\_year

\- winners: list of {category, person\_type, person\_id, team\_id}



\## 3.4. Persistence \& Validation



\*\*3.4.1. Serialization \& Save/Load\*\*



\- Saves are JSON; stable keys; integers wherever possible.

\- Derived fields (standings ranks, leaders) can be recomputed but are included for fast UI.

\- JSON export exposes complete LeagueState + standings + awards + latest power\_ratings + full pbp\_log for each completed game.



\*\*3.4.2. Validation \& Ranges (Engineering Guardrails)\*\*



\- Ratings clamp to 0-99; ages to 18-55; salary\_aav non-negative; contract\_years 0-3.

\- Enum checks for conference/division.

\- PBP lines must be strictly ordered (idx increasing), with score deltas summing to the final box score.

\- Integrity check on load: recompute PF/PA from GameResult and reconcile with standings.



\*\*3.4.3. Calibration Files \& Paths (Windows Dev)\*\*



\- Repo root: C:\\\\Users\\\\bpalm\\\\Documents\\\\franchise-football

\- Calibration JSON: C:\\\\Users\\\\bpalm\\\\Documents\\\\franchise-football\\\\data\\\\model\\\\calibration

\- league\_baselines.json

\- teams\_\&lt;season\&gt;.json

\- Reports (QA/metrics): C:\\\\Users\\\\bpalm\\\\Documents\\\\franchise-football\\\\data\\\\reports



\## 3.5. Future Features



The following features are explicitly deferred to R2. Their fields and DTOs will be defined in this subsection to avoid polluting MVP data shapes, while staking stable names for forward compatibility.



\- \*\*Injuries (R2)\*\*

\- Add Injury entity: injury\_id, player\_id, type, severity, start\_week, expected\_return\_week.

\- Player availability derived from injuries; Player.status returned via DTO only (Active|Questionable|Out|IR).

\- Add injury impacts to stamina/awareness in sim pipelines.

\- \*\*Coaches (R2)\*\*

\- Coach entity and CoachCardDTO (all tendency sliders and quality ratings).

\- Team-level strategy defaults if no coach assigned (MVP behavior).

\- \*\*Free Agency \& Trade Block (R2)\*\*

\- Free Agent pool (players without team\_id).

\- TradeBlock flag at player level (trade\_block: bool).

\- FA signing and trade endpoints; contract negotiation loop (simplified in R2).

\- \*\*Draft (R2)\*\*

\- DraftPick entity (team\_id, round, overall).

\- Prospect entity (same attribute schema as Players + draft\_grade).

\- Draft board, selection order, rookie contracts.

\- \*\*Playoffs (R2)\*\*

\- Postseason bracket model (byes, seeds).

\- Postseason GameResult entries share the same schema as regular season with bracket metadata.

\- Awards may include SB MVP in R2.



\## 3.6 Data Seeds \& Imports



Purpose  

Define the authoritative seed datasets used to initialize a brand-new league and to (optionally) rebuild the Hall of Fame and Record Book. Seeds are deterministic and idempotent (safe to re-run) and live in-repo for reproducibility.



3.6.1 Canonical Seed Files (repo-relative)  

Exact filenames and canonical paths, with purpose and target domain tables (primary).



\- Franchise Football NFL Roster.csv - /data/seeds/Franchise Football NFL Roster.csv  

&nbsp;   Purpose: Active player roster at league start  

&nbsp;   Targets: player, contract (MVP simple AAV), team\_player

\- Coach Roster Seed - Sheet1.csv - /data/seeds/Coach Roster Seed - Sheet1.csv  

&nbsp;   Purpose: Active coaches/staff at league start  

&nbsp;   Targets: coach, team\_coach

\- HOF Players Seed - Sheet1.csv - /data/seeds/HOF Players Seed - Sheet1.csv  

&nbsp;   Purpose: Hall of Fame players index  

&nbsp;   Targets: person, hof\_member (role = PLAYER)

\- HOF Coaches Seed - Sheet1.csv - /data/seeds/HOF Coaches Seed - Sheet1.csv  

&nbsp;   Purpose: Hall of Fame coaches index  

&nbsp;   Targets: person, hof\_member (role = COACH)

\- Single Season Records.xlsx - /data/seeds/Single Season Records.xlsx  

&nbsp;   Purpose: Preloaded single-season records  

&nbsp;   Targets: record\_def, record\_entry

\- Career Records.xlsx - /data/seeds/Career Records.xlsx  

&nbsp;   Purpose: Preloaded career records  

&nbsp;   Targets: record\_def, record\_entry



Assumption (MVP)  

We accept these exact filenames and formats. Future releases may normalize to CSV-only; this section will be revised if/when formats change.



3.6.2 Import Order \& Triggers  

Default order (to satisfy foreign keys):



\- Teams \& schedule template (Section 5)

\- Coaches → Coach Roster Seed - Sheet1.csv

\- Players → Franchise Football NFL Roster.csv

\- Hall of Fame → HOF Players…, then HOF Coaches…

\- Record Book → Career Records.xlsx, then Single Season Records.xlsx

\- Derived indexes (search, preseason Power Ranking baseline)



When the seeds run:



\- New League Creation (required) - runs the full order above once, immediately after DB creation/migrations.

\- Developer Bootstrap (make init) - convenience entry point that loads the same sequence locally.

\- Admin Maintenance (Manual, non-destructive) - optional actions exposed in a Maintenance screen:  

&nbsp;   • "Rebuild Record Book from seeds" (upsert only)  

&nbsp;   • "Re-import Hall of Fame from seeds" (upsert only)  

&nbsp;   • "Reload Active Rosters" (disabled by default in live leagues; destructive reset requires explicit confirmation)



What never happens automatically  

No reseeding on routine server start; no destructive deletes unless a dedicated Reset League flow is invoked.



3.6.3 Idempotency, Matching Keys \& Determinism



\- Idempotent upsert: Imports perform upserts (insert new, update existing) based on natural keys; they do not delete rows by default.

\- Natural keys (preferred):  

&nbsp;   • Player: (first\_name, last\_name, birthdate) or provided player\_ext\_id.  

&nbsp;   • Coach: (first\_name, last\_name, birthdate) or coach\_ext\_id.  

&nbsp;   • HOF: person\_ext\_id (if present) or resolved person\_id after dedupe.  

&nbsp;   • Records: record\_key + holder ID (+ season for single-season).

\- Deterministic IDs: Any generated IDs or tie-breaks use the league's global seeded RNG to ensure reproducibility.

\- Stable ordering: Input rows are processed by stable sort (filename, then line number) to keep outcomes identical across machines.



3.6.4 Validation \& Failure Policy



\- Schema checks: required columns present; datatypes parse; team codes exist in team; ages/dates plausible; no duplicate natural keys per file.

\- Cross-file integrity: HOF imports must resolve to existing or newly created person rows; records must link to valid holders (player/coach).

\- Failure mode: On any validation error, abort the current seed step and emit a line-numbered error report; prior successful steps remain committed.



3.6.5 Cross-References



\- League Initialization: Section 5 (where this seeding pipeline is invoked).

\- Stats \& Record Book: Sections 7.6+ (these seeds populate record\_def/record\_entry).

\- Player/Coach Profile UI: Sections 7.7+ (HOF badge and filters read from hof\_member).

\- Admin/Dev Ops: Appendix B (Makefile tasks \& maintenance endpoints).



3.6.6 Field Mapping (examples)



\- Players: first\_name, last\_name, position, age, attributes{…}, salary\_aav, contract\_years

\- Coaches: first\_name, last\_name, role (HC | OC | DC | STC), scheme\_tendencies{run\_pass, aggression, pace}

\- Roster: team\_id, player\_id, depth\_slot

\- Team identifiers: normalize external team codes/names to internal team\_id during import.



3.6.7 Cleaning \& Coercion (MVP specifics)



\- Trim whitespace; coerce numeric fields; clamp attributes to 0-99.

\- Reject rows missing position or team\_id (players) or role (coaches).

\- Continue on error; append one import\_log entry per rejected row (filename, line number, reason).

\- Date handling: parse ISO-like formats; if ambiguous, log and skip row.



3.6.8 Diagnostics \& Logging



\- Diagnostics: /diag/calibration includes an import\_log summary (per file: rows read, inserted, updated, skipped, errors).

\- Artifacts: write a CSV of rejected rows per file to /data/logs/imports/\&lt;timestamp\&gt;\\\_rejects.csv for quick remediation.



\## 3.7 Contract (MVP, Normalized)



Purpose  

Normalize all player contracts into a dedicated entity that supports future contract types and salary-cap logic.  

In the MVP build, each player has only one active deal - a simple yearly salary (AAV) that equals the cap hit.  

All historical deals are preserved for financial and roster history.



3.7.1 Schema



Primary Fields



\- contract\_id - UUID - Primary key

\- player\_id - Foreign Key → Player (owning player)

\- team\_id - Foreign Key → Team (team holding rights)

\- signed\_on - Date of signature

\- start\_season - First active season (integer)

\- end\_season - Last active season inclusive (integer)

\- aav - Annual salary ("Average Annual Value"); equals cap hit in MVP

\- is\_active - Boolean flag (True when current season is within \\\[start,end\\])

\- acquired\_via - Enum (DRAFT, FA, TRADE, EXTENSION) - Origin of contract

\- no\_trade\_clause - Boolean - Reserved for R2

\- notes - Optional text notes



Indexes



\- team\_id + end\_season → for roster and cap lookups

\- player\_id + is\_active → for active deal queries  

&nbsp;   Uniqueness: (player\_id, start\_season) must be unique.



3.7.2 Constraints and Invariants



\- Only one active contract per player at a time.

\- Total active AAV for a team cannot exceed LeagueSettings.salary\_cap.

\- When a player signs a new deal with overlapping seasons, the previous contract is closed and marked inactive.

\- Trades update team\_id but retain all other metadata.

\- Releases set is\_active to False and free cap space immediately.

\- Active rows cannot be deleted; historical rows can.



3.7.3 Business Logic



\- Free Agency Trigger - When end\_season < current season and no extension exists, player becomes a free agent.

\- Cap Computation -  

&nbsp;   team.cap\_space = salary\_cap - sum of AAV for active contracts.

\- Extensions - Allowed only for players currently under contract; creates a new record with updated years.

\- History Retention - All expired contracts remain for reference and career financial views.



3.7.4 DTO Examples



ContractRead



{



"player\_id": "uuid",



"team\_id": "uuid",



"signed\_on": "2025-03-15",



"start\_season": 2025,



"end\_season": 2028,



"aav": 8500000,



"is\_active": true,



"acquired\_via": "FA"



}



ContractUpdate



{



"aav": 9000000,



"end\_season": 2029,



"notes": "Extended through 2029 season"



}



3.7.5 API Endpoints



\- GET /api/v1/contracts - List contracts (filter by team\_id, player\_id, season, is\_active).

\- GET /api/v1/contracts/{id} - Retrieve contract by ID.

\- POST /api/v1/contracts - Create contract; returns 409 if player already has active deal.

\- PATCH /api/v1/contracts/{id} - Modify salary, dates, status, or notes.

\- DELETE /api/v1/contracts/{id} - Delete historical (inactive) contracts only.



3.7.6 Test Scenarios



\- Creating a second active deal for the same player → 409 Conflict.

\- Trading a player changes team\_id but keeps contract ID and salary.

\- Extending a deal creates new row while old row remains archived.

\- Cap overage blocks commit and returns validation error.

\- Deleting inactive deal → success; deleting active deal → 409 blocked.



3.7.7 Cross-References



\- Section 3.8 Injury (MVP) - roster availability and cap logic.

\- Section 8.3 Free Agency - uses contract expiration data.

\- Section 15.x Tests - Cap validation and contract lifecycles.



\## 3.8 Injury (MVP, Persisted Log)



\*\*Purpose\*\*  

Track all player injuries that occur during games or practices and record their effects on performance, availability, and roster management.  

The MVP version implements deterministic injury generation, week-based recovery, and Return-to-Play (RTP) penalties with a simple IR (injured reserve) flag.



\*\*3.8.1 Schema\*\*



\*\*Primary Fields\*\*



\- \*\*injury\_id\*\* - UUID - Primary key

\- \*\*player\_id\*\* - Foreign Key → Player (injured player)

\- \*\*game\_id\*\* - Foreign Key → Game (nullable; null if practice injury)

\- \*\*injury\_type\*\* - Enum: ANKLE, HAMSTRING, ACL, MCL, SHOULDER, CONCUSSION, WRIST, HAND, BACK, NECK, OTHER

\- \*\*severity\*\* - Enum: MINOR, MODERATE, MAJOR

\- \*\*weeks\_out\*\* - Integer - Remaining recovery weeks; decremented weekly

\- \*\*rtp\_penalty\*\* - Float (0-1) - Temporary performance penalty while returning

\- \*\*date\_injured\*\* - Date of occurrence

\- \*\*expected\_return\_week\*\* - Integer (optional estimate)

\- \*\*placed\_on\_ir\*\* - Boolean - True if IR-eligible (≥4 weeks out)

\- \*\*is\_active\*\* - Boolean - True while injury is ongoing or RTP penalty is applied

\- \*\*notes\*\* - Text (optional)



\*\*Indexes\*\*



\- player\_id + is\_active → for active injury lookups

\- game\_id → for game logs and reports



\*\*3.8.2 Constraints and Invariants\*\*



\- Each player can have only one active injury at a time.

\- When weeks\_out ≤ 0 and rtp\_penalty = 0, the record automatically closes (is\_active=false).

\- Injuries lasting 4 or more weeks allow IR placement (placed\_on\_ir=true).

\- A player on IR does not count toward the active 53-man roster.

\- MVP excludes mid-season IR recall; that feature is reserved for R2.



\*\*3.8.3 Business Logic\*\*



\- \*\*Injury Creation\*\*

&nbsp; - Generated deterministically during gameplay or by random draw using injury rate curves (see Section 6.10).

&nbsp; - Severity and duration derived from injury class, player position, and proneness rating.

\- \*\*Weekly Update Loop\*\*

&nbsp; - At each simulated week:

&nbsp;   - Decrease weeks\_out by 1.

&nbsp;   - If weeks\_out = 0, the player enters RTP phase.

&nbsp;   - RTP penalty gradually decays to 0 over successive weeks.

\- \*\*RTP Penalty Effect\*\*

&nbsp; - Effective Attribute = Base Attribute × (1 − rtp\_penalty).

&nbsp; - Example: a 0.12 RTP penalty reduces physical attributes by 12%.

\- \*\*Historical Logging\*\*

&nbsp; - When an injury resolves, its record remains stored for analytics and career durability metrics.



\*\*3.8.4 DTO Examples\*\*



\*\*InjuryRead\*\*



{



"player\_id": "uuid",



"game\_id": "uuid",



"injury\_type": "HAMSTRING",



"severity": "MODERATE",



"weeks\_out": 3,



"rtp\_penalty": 0.12,



"is\_active": true,



"placed\_on\_ir": false



}



\*\*InjuryUpdate\*\*



{



"weeks\_out": 1,



"rtp\_penalty": 0.05,



"is\_active": true



}



\*\*3.8.5 API Endpoints\*\*



\- \*\*GET /api/v1/injuries\*\* - List injuries (filters: player\_id, team\_id, is\_active, severity, injury\_type).

\- \*\*GET /api/v1/injuries/{id}\*\* - Retrieve by ID.

\- \*\*POST /api/v1/injuries\*\* - Create a new injury (returns 409 if player already has an active one).

\- \*\*PATCH /api/v1/injuries/{id}\*\* - Update duration, RTP penalty, IR flag, or status.

\- \*\*DELETE /api/v1/injuries/{id}\*\* - Allowed only for inactive, historical injuries.



\*\*3.8.6 Test Scenarios\*\*



\- Add new injury while another is active → 409 Conflict.

\- Weekly decrement transitions injury into RTP → rtp\_penalty decays → is\_active becomes false.

\- Set IR flag for 4+ week injuries → success; roster slot freed.

\- Delete resolved injury → success.

\- Delete active injury → blocked (409).



\*\*3.8.7 Cross-References\*\*



\- \*\*Section 6.10\*\* - Injury System (probability, severity logic).

\- \*\*Section 7.6\*\* - Player Stats aggregation (durability and games missed).

\- \*\*Section 15.x\*\* - Automated test suite for injury lifecycle verification.



\## 3.9 Record Book (MVP)



\*\*Purpose.\*\*  

\*\*3.9 Record Book (MVP)\*\*



\*\*Purpose\*\*  

Maintain a persistent league-wide repository of all statistical records: single-game, single-season, and career marks for players, teams, and coaches.  

This data feeds the \*\*Stats Page\*\*, \*\*Milestone Tracker\*\*, and \*\*Awards logic\*\*.



\*\*3.9.1 Schema\*\*



\*\*Primary Fields\*\*



\- \*\*record\_id\*\* - UUID - Primary key

\- \*\*scope\*\* - Enum (PLAYER, TEAM, COACH) - Entity type that owns the record

\- \*\*category\*\* - String - Stat name (e.g., PASS\_YARDS, RUSH\_TDS, SACKS, FG\_LONG)

\- \*\*record\_type\*\* - Enum (SINGLE\_GAME, SINGLE\_SEASON, CAREER) - Record level

\- \*\*subject\_id\*\* - Foreign Key → Player/Team/Coach - Record holder

\- \*\*value\*\* - Float or Integer - Result value

\- \*\*season\*\* - Integer (optional, required for seasonal records)

\- \*\*game\_id\*\* - UUID (optional, required for single-game records)

\- \*\*meta\*\* - JSON (optional, stores opponent, week, notes)

\- \*\*achieved\_on\*\* - Date of achievement



\*\*Indexes\*\*



\- record\_type + category + value DESC → fast leaderboards

\- subject\_id + record\_type → career lookups



\*\*3.9.2 Constraints and Invariants\*\*



\- Order records by (record\_type, category, value DESC).

\- Allow ties - identical values sorted by most recent achieved\_on.

\- Insert new row when a value surpasses or ties existing record ("upsert-on-surpass").

\- scope must match the entity type referenced in subject\_id.



\*\*3.9.3 Business Logic\*\*



\- \*\*Game Finalize Hook\*\*

&nbsp; - On game completion, compute candidate record values from aggregated box scores.

&nbsp; - Compare to current top record(s).

&nbsp; - Insert new Record row if value exceeds existing leader.

\- \*\*Season Finalize Hook\*\*

&nbsp; - Aggregate per-season totals.

&nbsp; - Compare against single-season and career records; insert as needed.

\- \*\*Career Roll-Up\*\*

&nbsp; - When a player or coach retires, compare cumulative totals to career records.

\- \*\*Initial Tracked Categories (MVP)\*\*

&nbsp; - \*\*Passing:\*\* Yards, TDs, Completion %, Rating

&nbsp; - \*\*Rushing:\*\* Yards, TDs, Yards Per Carry

&nbsp; - \*\*Receiving:\*\* Yards, TDs, Receptions

&nbsp; - \*\*Defense:\*\* Tackles, Sacks, INTs, TFLs, Pass Deflections

&nbsp; - \*\*Kicking/Punting:\*\* FG Made, FG Long, Punt Yards

&nbsp; - \*\*Team:\*\* Points For, Points Allowed, Yards For, Yards Allowed

&nbsp; - \*\*Coach:\*\* AFC/NFC Titles, Super Bowls Won



\*\*3.9.4 DTO Examples\*\*



\*\*RecordRead\*\*



{



"record\_type": "SINGLE\_SEASON",



"scope": "PLAYER",



"category": "PASS\_YARDS",



"subject\_id": "uuid",



"value": 5245,



"season": 2027,



"meta": {"team": "NYG", "opponent": "DAL"},



"achieved\_on": "2028-01-05"



}



\*\*3.9.5 API Endpoints\*\*



\- \*\*GET /api/v1/records\*\* - List records (filters: record\_type, scope, category, subject\_id, season).

\- \*\*GET /api/v1/records/top\*\* - Return Top N records, e.g. /records/top?category=PASS\_YARDS\&record\_type=SINGLE\_SEASON\&limit=10.

\- \*\*GET /api/v1/records/{id}\*\* - Retrieve by ID.

\- \*\*POST /api/v1/records\*\* - Insert new record (manual admin override).

\- \*\*DELETE /api/v1/records/{id}\*\* - Remove record (admin only).



\*\*3.9.6 Test Scenarios\*\*



\- Player sets a new single-game record → new record row inserted.

\- Player ties an existing record → both records visible (ordered by date).

\- Deleting record → record removed from leaderboard.

\- Re-finalizing same game → no duplicate entries (idempotent).

\- Filtering by scope=TEAM and category=POINTS\_FOR → returns team records only.



\*\*3.9.7 Cross-References\*\*



\- Section 7.6 - Stat Aggregation source.

\- Section 7.7 - Coach Role Titles adds coach-specific categories.

\- Section 15.x - Validation tests for record integrity.



\## 3.10 Hall of Fame (MVP)



\*\*Purpose\*\*  

Maintain a permanent record of players and coaches who have been inducted into the League Hall of Fame.  

Inductions are determined during the offseason based on statistical achievements, awards, and championships.  

This section defines the entity, rules, and scoring model used for HOF selection.



\*\*3.10.1 Schema\*\*



\*\*Primary Fields\*\*



\- \*\*hof\_id\*\* - UUID - Primary key

\- \*\*subject\_type\*\* - Enum (PLAYER, COACH) - Type of inductee

\- \*\*subject\_id\*\* - Foreign Key → Player or Coach

\- \*\*inducted\_season\*\* - Integer - Season of induction

\- \*\*ballot\_number\*\* - Integer - Number of ballot attempts (1 = first ballot)

\- \*\*primary\_team\_id\*\* - Foreign Key → Team (main team affiliation)

\- \*\*career\_war\*\* - Float (optional) - Approximation of career value over replacement

\- \*\*rings\*\* - Integer - Total Super Bowl titles

\- \*\*mvp\*\* - Integer - League MVP awards

\- \*\*all\_pro\*\* - Integer - All-Pro selections

\- \*\*pro\_bowls\*\* - Integer - Pro Bowl selections

\- \*\*career\_yards\*\* - Integer (optional) - Offensive or defensive yardage metric

\- \*\*career\_tds\*\* - Integer (optional) - Total touchdowns or equivalent scoring events

\- \*\*citation\*\* - Text (optional) - Description of induction reasoning



\*\*Indexes\*\*



\- inducted\_season - for annual class sorting

\- subject\_type + subject\_id - must be unique (only one induction per entity)



\*\*3.10.2 Constraints and Invariants\*\*



\- Each player or coach can appear only once in the Hall of Fame.

\- Induction may occur only after retirement (or death in sim terms).

\- Historical records remain immutable once created.

\- Ballot retries (if implemented later) increment ballot\_number but retain the same subject\_id.



\*\*3.10.3 Business Logic\*\*



\- \*\*Eligibility Rules (MVP version)\*\*

&nbsp; - Player or coach must have been retired for at least one full offseason.

&nbsp; - Must meet or exceed base thresholds in at least one of the following:

&nbsp;   - 1+ League MVPs

&nbsp;   - 3+ All-Pro selections

&nbsp;   - 5+ Pro Bowls

&nbsp;   - 2+ Championships (player or HC titles)

&nbsp;   - Top 10 in any major career statistical category

\- \*\*Scoring Model (Weighted)\*\*

\- HOF\_score = 3 × Super Bowl Wins

\- \\+ 1 × (AFC/NFC Titles)

\- \\+ 2 × League MVPs

\- \\+ 1 × All-Pro Selections

\- \\+ 0.5 × Pro Bowl Selections

\- \\+ 0.001 × Career Yards

\- \\+ 0.5 × Career TDs

&nbsp; - Threshold for automatic induction: \*\*HOF\_score ≥ 15\*\*

&nbsp; - Scores below threshold may still qualify via committee (R2 hook).

\- \*\*Selection Timing\*\*

&nbsp; - Inductions occur during the offseason phase after retirements and before the new season seed.

&nbsp; - Inductees are appended to the HallOfFame table and surfaced in the UI under "HOF Class of \&lt;Year\&gt;".

\- \*\*Coach Role Integration\*\*

&nbsp; - Coach records (see Section 7.9) feed directly into rings and conference titles.

&nbsp; - Coaches are evaluated on both head coach and coordinator career totals.



\*\*3.10.4 DTO Examples\*\*



\*\*HOFRead\*\*



{



"subject\_type": "PLAYER",



"subject\_id": "uuid",



"inducted\_season": 2029,



"primary\_team\_id": "uuid",



"rings": 3,



"mvp": 2,



"all\_pro": 5,



"pro\_bowls": 8,



"career\_yards": 55000,



"career\_tds": 410,



"citation": "One of the most prolific QBs of his era."



}



\*\*3.10.5 API Endpoints\*\*



\- \*\*GET /api/v1/hof\*\* - List inductees (filters: subject\_type, inducted\_season, team\_id).

\- \*\*GET /api/v1/hof/{id}\*\* - Retrieve one inductee record.

\- \*\*POST /api/v1/hof\*\* - Create new induction (409 if subject already inducted).

\- \*\*PATCH /api/v1/hof/{id}\*\* - Update citation or metadata (admin only).

\- \*\*DELETE /api/v1/hof/{id}\*\* - Remove entry (admin only).



\*\*3.10.6 Test Scenarios\*\*



\- Induct retired player with qualifying score → record created.

\- Attempt to re-induct same player → 409 Conflict.

\- Create entry for active player → rejected by rule.

\- GET by season → returns correct "Class of \&lt;Year\&gt;."

\- Delete entry → admin only; test soft delete behavior.



\*\*3.10.7 Cross-References\*\*



\- Section 7.9 - Coach Role Titles (supplies championship data).

\- Section 3.9 - Record Book (feeds career stats).

\- Section 15.x - Validation tests for eligibility and duplicate detection.



\## 3.11 Save/Load \& Determinism



\*\*3.11.1 Save Format\*\*



\- Single JSON file with top-level keys: league, season, teams, players, coaches, schedule, standings, awards\_state, admin\_log, schema\_version, checksum.



\*\*3.11.2 Schema Versioning\*\*



\- schema\_version increments on breaking changes. Backward-compatible additions are allowed without bumping major version.

\- Loader performs deterministic migrations for minor versions; major version requires explicit upgrade path.



\*\*3.11.3 Checksum\*\*



\- SHA-256 of the canonicalized save (excluding the checksum field).



\*\*3.11.4 Seeds\*\*



\- Global: LEAGUE\_SEED (int).

\- Derived:

&nbsp; - GAME\_SEED = hash(LEAGUE\_SEED, week, game\_id)

&nbsp; - DRAFT\_SEED = hash(LEAGUE\_SEED, season, "draft")

&nbsp; - AWARDS\_TIE\_SEED = hash(LEAGUE\_SEED, season, "awards")



\*\*3.11.5 RNG Use\*\*



\- Only for non-determinable tie-breaks and cosmetic outputs; never for primary stat assignment when formulas exist.



\*\*3.11.6 Compatibility Policy\*\*



\- Loader migrates previous \*\*minor\*\* versions via deterministic transforms; \*\*major\*\* version requires explicit upgrade path.



\*\*3.11.7 Example Minor Migration (illustrative)\*\*



\- From schema\_version = "mvp-1" to "mvp-1.1" adding players\\\[i\\].stamina (default 70 if missing):

&nbsp; - If players\\\[i\\].stamina is absent, set to 70.

&nbsp; - Recompute team.depth\_valid (no other fields change).

&nbsp; - Write back schema\_version = "mvp-1.1".

\- Determinism: migration ordered by player\_id ascending.



\*\*3.11.8 Acceptance Checks (loader)\*\*



\- Validates checksum before and after write; rejects mismatched checksums.

\- Seeds block present; derived seeds recomputable from LEAGUE\_SEED.

\- Open-and-save round-trip produces identical file byte-for-byte (excluding updated checksum).

\- Minor migration on a known fixture yields exact expected diff (fields added only; no value drift elsewhere).



\# 4\\. Core Game Loop



The game progresses through a standard year-over-year cycle, moving through distinct phases from the pre-season setup to the conclusion of the off-season. This loop forms the foundational structure of the player's experience.



\## 4.1. The Annual Cycle



The cycle is designed to mirror a professional football league's calendar and can be visualized as a continuous loop:



\*\*Pre-Season Setup → Regular Season → Playoffs → Championship → Off-Season → (Repeat)\*\*



\## 4.2. Phase Breakdown



The core game loop is broken down into the following sequential phases:



\- \*\*Pre-Season \& League Setup:\*\* This phase handles all initial setup for the new season, including schedule generation.

\- \*\*Pre-season:\*\* These 4 preseason games will be scheduled randomly across the league, with no team playing a team in their division or playing the same team more than once in the preseason. The preseason is used to create a team history for the simulation logic to use for the rest of the season's games. Stats will not be kept on the player card or in the stats section for preseason games.

\- \*\*Regular Season:\*\* The simulation proceeds through an 18-week, 17-game schedule for all 32 teams.

\- \*\*Playoffs:\*\* A 14-team postseason bracket begins, following the conclusion of the regular season.

\- \*\*Championship:\*\* The final game of the playoffs is played to determine the league champion.

\- \*\*Off-Season:\*\* A multi-stage phase where rosters and the league evolve. This includes:



\- \*\*Awards:\*\* Season-end awards are calculated and distributed. Leaderboards for the completed season are finalized and persisted in the save file.

\- \*\*Progression \& Regression:\*\* All players in the league undergo attribute changes based on the progression system.

\- \*\*Retirements:\*\* Players and coaches may choose to retire from the league.

\- \*\*Free Agency:\*\* Teams can sign players who are not under contract.

\- \*\*Annual Rookie Draft:\*\* A 7-round draft is held to bring new players into the league.



\# 5\\. Pre-Season \& League Setup



This phase handles all initial setup for a new season before the simulation of games begins. The primary component of this phase is the deterministic generation of the regular season schedule.



\## 5.1. Schedule Generation



This section defines the logic for the 18-week, 17-game regular season schedule. It specifies the opponent selection formula, host rotations, home/away parity templates, policies for bye weeks, and data models to ensure the schedule is deterministic and reproducible.



\*\*5.1.1. Scope \& Goals (MVP)\*\*



\- \*\*Mirror the NFL's 17-game opponent selection model,\*\* including year-over-year divisional/conference rotations and standings-based matchups.

\- \*\*Maintain an 18-week structure\*\* with a single bye per team within a defined window.

\- \*\*Enforce deterministic parity\*\* for Home/Away assignments across scheduling cycles without using random number generation.

\- \*\*Defer advanced realism\*\* (e.g., international games, flex scheduling, primetime tuning) until post-MVP.



\*\*5.1.2. Official 17-Game Opponent Formula\*\*



For each team, the 17 opponents are selected in the following order:



\- \*\*Division (DIV) - 6 games:\*\* Home and away games against each of the 3 division opponents.

\- \*\*Intra-Conference Rotation (IC\_ROT) - 4 games:\*\* Games against one full division from the same conference, based on a 3-year rotation.

\- \*\*Inter-Conference Rotation (OC\_ROT) - 4 games:\*\* Games against one full division from the other conference, based on a 4-year rotation.

\- \*\*Standings-Based Intra-Conference (IC\_PLACE) - 2 games:\*\* Games against the same-place finishers from the other two divisions in the same conference that are not part of the current rotation.

\- \*\*17th Game (OC\_PLACE\_17) - 1 game:\*\* A game against the same-place finisher from a non-rotating division in the opposite conference. The host is determined by an annual AFC↔NFC rotation.



All rotation and standings inputs are read from configuration tables and the previous season's final standings. Opponent selection is entirely deterministic.



\*\*5.1.3. Home/Away Assignment \& Rotations\*\*



\- \*\*XVII Host Rotation:\*\* A single global toggle per season determines which conference (AFC or NFC) hosts all 17th inter-conference games. The pattern is defined in a central configuration table (e.g., 2025: AFC hosts, 2026: NFC hosts).

\- \*\*Division Games:\*\* Each of the 3 division opponents is played twice: one home, one away.

\- \*\*Rotational Games (8 total):\*\* Parity templates are used to alternate Home/Away assignments based on year parity (odd/even) to keep the total number of home games near 8 or 9 across multiple years.

\- \_Example Template Pair:\_

\- Template A (even years): H, H, A, A, H, A, H, A

\- Template B (odd years): A, A, H, H, A, H, A, H

\- \*\*Standings-Based Games (2 total):\*\* A two-year flip is used for each opponent pairing to alternate hosting duties when the matchup repeats in future years.



\*\*5.1.4. Bye Weeks \& Week Layout Rails\*\*



\- \*\*Bye Window:\*\* Each team receives one bye week, scheduled between \*\*Week 5 and Week 14\*\*. \*\*Week 6 is excluded\*\* from the bye window. Byes should be staggered to avoid too many teams being off in a single week (soft guardrail).

\- \*\*Division Game Placement:\*\* At least two divisional games must be scheduled in the final three weeks of the season (Weeks 16-18).

\- \*\*Soft Sequencing Constraints (Best Effort):\*\*

\- Prefer to limit home or away streaks to a maximum of three games.

\- Avoid four-game home or away stands (this will only trigger a warning in the MVP build).



\*\*5.1.5. Data Model \& Configuration\*\*



\- \*\*In-Memory Structure (LeagueState.schedule):\*\* A list of 18 weeks, where each week contains a list of games ({homeId, awayId}) and a list of teams on bye (teamId).

\- \*\*Configuration Tables:\*\* All logic is driven by tables located in /data/model/calibration/schedule/:

\- rotation\_ic\_3yr\\\[year\_mod3\\]\\\[division\\] -> opponent\_division

\- rotation\_oc\_4yr\\\[year\_mod4\\]\\\[division\\] -> opponent\_division

\- xvii\_host\_by\_year\\\[season\_year\\] -> "AFC" | "NFC"

\- templates\_rotational = { even: \\\[H/A flags\\], odd: \\\[H/A flags\\] }

\- \*\*Standings Inputs:\*\* Prior-season division placement (1-4) per team, read from standings\_{year-1}.json.

\- templates\_rotational.even and templates\_rotational.odd are fixed-length arrays of \*\*8\*\* entries (the eight non-divisional rotational games) and are applied \*\*in index order\*\* during generation.



\*\*5.1.6. Algorithm \& Tests\*\*



\- \*\*Algorithm (Pure Functions):\*\*



\- compute\_opponents(team\_id, year, last\_year\_standings): Calculates the 17 opponents for a team.

\- assign\_home\_away(team\_id, opponents, year): Applies H/A rules to the opponent list.

\- lay\_out\_weeks(all\_pairings, year): Arranges all 272 games into the 18-week schedule.



\- \*\*Tests \& Acceptance Criteria:\*\*

\- \*\*Unit Tests:\*\* Verify opponent composition counts are exactly {DIV:6, IC\_ROT:4, OC\_ROT:4, IC\_PLACE:2, OC\_PLACE\_17:1} for each team.

\- \*\*League-Wide Tests:\*\* Ensure exactly 272 games are scheduled with no duplicates. Verify every team has exactly one bye within the W5-W14 window (excluding W6).

\- \*\*Determinism Test:\*\* Confirm that re-running the generator with identical inputs yields an identical schedule.



\*\*5\\. Pre-Season \& League Setup\*\*



This phase handles all initial setup for a new season before the simulation of games begins. The primary component of this phase is the deterministic generation of the regular season schedule.



\*\*5.1. Schedule Generation\*\*



This section defines the logic for the 18-week, 17-game regular season schedule. It specifies the opponent selection formula, host rotations, home/away parity templates, policies for bye weeks, and data models to ensure the schedule is deterministic and reproducible.



\*\*5.1.1. Scope \& Goals (MVP)\*\*



\- \*\*Mirror the NFL's 17-game opponent selection model,\*\* including year-over-year divisional/conference rotations and standings-based matchups.

\- \*\*Maintain an 18-week structure\*\* with a single bye per team within a defined window.

\- \*\*Enforce deterministic parity\*\* for Home/Away assignments across scheduling cycles without using random number generation.

\- \*\*Defer advanced realism\*\* (e.g., international games, flex scheduling, primetime tuning) until post-MVP.



\*\*5.1.2. Official 17-Game Opponent Formula\*\*



For each team, the 17 opponents are selected in the following order:



\- \*\*Division (DIV) - 6 games:\*\* Home and away games against each of the 3 division opponents.

\- \*\*Intra-Conference Rotation (IC\_ROT) - 4 games:\*\* Games against one full division from the same conference, based on a 3-year rotation.

\- \*\*Inter-Conference Rotation (OC\_ROT) - 4 games:\*\* Games against one full division from the other conference, based on a 4-year rotation.

\- \*\*Standings-Based Intra-Conference (IC\_PLACE) - 2 games:\*\* Games against the same-place finishers from the other two divisions in the same conference that are not part of the current rotation.

\- \*\*17th Game (OC\_PLACE\_17) - 1 game:\*\* A game against the same-place finisher from a non-rotating division in the opposite conference. The host is determined by an annual AFC↔NFC rotation.



All rotation and standings inputs are read from configuration tables and the previous season's final standings. Opponent selection is entirely deterministic.



\*\*5.1.3. Home/Away Assignment \& Rotations\*\*



\- \*\*XVII Host Rotation:\*\* A single global toggle per season determines which conference (AFC or NFC) hosts all 17th inter-conference games. The pattern is defined in a central configuration table (e.g., 2025: AFC hosts, 2026: NFC hosts).

\- \*\*Division Games:\*\* Each of the 3 division opponents is played twice: one home, one away.

\- \*\*Rotational Games (8 total):\*\* Parity templates are used to alternate Home/Away assignments based on year parity (odd/even) to keep the total number of home games near 8 or 9 across multiple years.

\- \_Example Template Pair:\_

\- Template A (even years): H, H, A, A, H, A, H, A

\- Template B (odd years): A, A, H, H, A, H, A, H

\- \*\*Standings-Based Games (2 total):\*\* A two-year flip is used for each opponent pairing to alternate hosting duties when the matchup repeats in future years.



Configuration



\- xvii\_host\_by\_year (explicit host conference for the 17th game):  

&nbsp;   { 2025: "AFC", 2026: "NFC", 2027: "AFC", 2028: "NFC" }  

&nbsp;   (Extend this map as needed; selection is deterministic from the season year.)



Deterministic Rails



\- Each team's H/A split alternates 9/8 vs 8/9 across seasons in accordance with xvii\_host\_by\_year and existing rotation rules.

\- If multiple H/A placements are valid, choose the lowest game\_id; tie-break by lowest team\_id (deterministic).



\*\*5.1.4. Bye Weeks \& Week Layout Rails\*\*



\- \*\*Bye Window:\*\* Each team receives one bye week, scheduled between \*\*Week 5 and Week 14\*\*. \*\*Week 6 is excluded\*\* from the bye window. Byes should be staggered to avoid too many teams being off in a single week (soft guardrail).

\- \*\*Division Game Placement:\*\* At least two divisional games must be scheduled in the final three weeks of the season (Weeks 16-18).

\- \*\*Soft Sequencing Constraints (Best Effort):\*\*

\- Prefer to limit home or away streaks to a maximum of three games.

\- Avoid four-game home or away stands (this will only trigger a warning in the MVP build).



Bye Window (MVP)



\- Byes may only occur in \*\*Weeks 5-14\*\* (inclusive).

\- No team may receive a bye \*\*before Week 5\*\* or \*\*after Week 14\*\*.



Layout Rails



\- \*\*Max consecutive home games:\*\* 3

\- \*\*Max consecutive away games:\*\* 3

\- \*\*Distribution preference:\*\* minimize variance of bye counts per week (aim for flat weekly totals where possible).



Conflict Handling (deterministic)



\- If soft rails cannot be satisfied under all constraints, \*\*emit WARN\*\* and choose the assignment that:

&nbsp; - Minimizes the offending streak length, then

&nbsp; - Uses the \*\*earliest week\*\* feasible, then

&nbsp; - Breaks ties by \*\*lowest game\_id\*\*, then \*\*lowest team\_id\*\*.

\- All choices are \*\*seeded/deterministic\*\*; the same inputs produce the same schedule.



\*\*5.1.5. Data Model \& Configuration\*\*



\- \*\*In-Memory Structure (LeagueState.schedule):\*\* A list of 18 weeks, where each week contains a list of games ({homeId, awayId}) and a list of teams on bye (teamId).

\- \*\*Configuration Tables:\*\* All logic is driven by tables located in /data/model/calibration/schedule/:

\- rotation\_ic\_3yr\\\[year\_mod3\\]\\\[division\\] -> opponent\_division

\- rotation\_oc\_4yr\\\[year\_mod4\\]\\\[division\\] -> opponent\_division

\- xvii\_host\_by\_year\\\[season\_year\\] -> "AFC" | "NFC"

\- templates\_rotational = { even: \\\[H/A flags\\], odd: \\\[H/A flags\\] }

\- \*\*Standings Inputs:\*\* Prior-season division placement (1-4) per team, read from standings\_{year-1}.json.



\*\*Note:\*\* templates\_rotational.even|odd are fixed-length arrays of \*\*8\*\* entries (covering the 8 rotational non-divisional games) and are applied \*\*in order of index\*\* at generation time.



\*\*5.1.6. Algorithm \& Tests\*\*



\- \*\*Algorithm (Pure Functions):\*\*



\- compute\_opponents(team\_id, year, last\_year\_standings): Calculates the 17 opponents for a team.

\- assign\_home\_away(team\_id, opponents, year): Applies H/A rules to the opponent list.

\- lay\_out\_weeks(all\_pairings, year): Arranges all 272 games into the 18-week schedule.



\- \*\*Tests \& Acceptance Criteria:\*\*

\- \*\*Unit Tests:\*\* Verify opponent composition counts are exactly {DIV:6, IC\_ROT:4, OC\_ROT:4, IC\_PLACE:2, OC\_PLACE\_17:1} for each team.

\- \*\*League-Wide Tests:\*\* Ensure exactly 272 games are scheduled with no duplicates. Verify every team has exactly one bye within the W5-W14 window (excluding W6).

\- \*\*Determinism Test:\*\* Confirm that re-running the generator with identical inputs yields an identical schedule.



Schedule Integrity



\- \*\*Game counts:\*\* each team has \*\*17\*\* games and exactly \*\*1\*\* bye; league total games = \*\*272\*\*.

\- \*\*Bye window:\*\* no byes outside \*\*Weeks 5-14\*\*.

\- \*\*Home/Away split:\*\* teams alternate \*\*9/8 vs 8/9\*\* across seasons consistent with xvii\_host\_by\_year.

\- \*\*Streak rails:\*\* no team exceeds \*\*3\*\* consecutive home or away games; if unavoidable, a \*\*WARN\*\* is logged and the chosen layout matches the deterministic conflict rule in §5.1.4.



Rotation \& Opponents



\- Divisional/home-and-away, intra-conference, inter-conference, and the 17th opponent all match the season's rotation template and host map.

\- Mirror schedule property (where applicable) is preserved across counterpart teams.



Determinism



\- With identical inputs (seed, rotation tables, host map, constraints), the generated schedule is \*\*bit-for-bit identical\*\* across machines and runs.



Diagnostics



\- /diag/calibration (or the schedule diagnostics endpoint) exposes: counts by week (games, byes), per-team H/A streak lengths, and any \*\*WARN\*\* messages emitted during conflict resolution.



\## 5.2 Depth Chart Auto-Fill Rules



Goal: One-click, deterministic assignment of starters and backups per position.



Default Order: Sort eligible players by OVR descending. Tie-breakers: (1) higher stamina, (2) lower age, (3) lower player\_id.



Eligibility:



\\- Must match required position (or allowable secondary positions list).



\\- Injury gating: Players with status OOS cannot occupy starter slots; players listed Q are allowed but flagged.



Safety Rails:



\\- If a position cannot be fully filled, leave slot empty and show a red "Needs Player" badge.



Special Teams:



\\- K: highest kick\_power; tie by kick\_accuracy.



\\- P: highest punt\_power; tie by punt\_accuracy.



\\- KR/PR: highest (speed + agility) composite; exclude players marked "No ST".



Persistence:



\\- Auto-fill writes to the roster state and persists in Save/Load.



\# 6\\. Game Simulation Engine



\*\*Scope \& Dependencies (for this section)\*\*  

\*\*Scope:\*\* Authoritative, engineering-ready specification for the play-level simulator: SFS anchoring, decision logic, outcome pipelines, timing rules, penalties, injuries, weather, seeds/determinism, diagnostics, and calibration artifacts.  

\*\*Depends on:\*\* Ratings \& coaching data (0-99), league calibration files (/data/model/calibration/\\\*), schedule, stadium/weather mapping, seeds, and the Stats Catalog (§7.6).  

\*\*MVP vs R2+ flags:\*\* \*\*All items in §6 are MVP\*\* unless explicitly marked otherwise. (We have promoted items formerly R2-\*\*Penalties\*\*, \*\*Injuries\*\*, \*\*Weather\*\*, and the \*\*Parity/Win-Prob hook\*\*-into MVP.)



\## 6.1. Architecture \& Engine Roles



\- \*\*Drive Engine (Authoritative):\*\* Simulates at \*\*play resolution\*\*, produces final score, team/player stats, and an \*\*immutable PBP event tape\*\* (single source of truth).

\- \*\*PBP Engine (Renderer-only):\*\* Formats Drive events into text. It never simulates or mutates state. May use a \*\*text-only seed\*\* for synonyms; all numbers (yards/clock/score) come from events.



\## 6.2. Score Fidelity System (SFS) \& Game Outcome Model



\*\*Purpose:\*\* Keep league-wide scoring aligned with modern NFL-like averages while preserving per-game unpredictability. Drive Engine \*\*consumes\*\* SFS targets (PPG, run/pass ratio, RZ TD%, etc.) and shapes \*\*probabilities\*\*, never post-edits scores.



\*\*Layers:\*\*



\- \*\*Pre-Sim Anchoring:\*\* Create \*\*matchup-specific EP per quarter\*\* per team.

\- \*\*In-Sim Calibration:\*\* Generate \*\*drive outcome probabilities\*\* that respect EP targets.

\- \*\*Post-Sim Micro-Normalization:\*\* Tiny, bounded nudges that influence \*\*next week's\*\* anchors (never alter completed games).  

&nbsp;   \*\*Season tolerance:\*\* league \*\*PPG ±0.7\*\* (CI).



\*\*6.2.A Inputs \& Data Sources (Pre-Sim Anchoring) \_(MVP)\_\*\*



\- \*\*League targets (CSV/JSON):\*\* league\_ppg, league\_drives\_per\_team, quarter\_share\\\[4\\], red\_zone\_td\_rate, pass\_rate\_neutral, explosive\_play\_rate, st\_fg\_rate\_base, etc.

\- \*\*Team/Unit strength:\*\* ELO-like \*\*Power Rating\*\* (HFA later). Unit 0-99: offense (QB, OL\_run, OL\_pass, WR/TE, RB), defense (DL, LB, DB, pass\_rush, coverage), ST (K, P, ST\_quality).

\- \*\*Coaching:\*\* pace, run\_pass\_tendency, aggression\_off, aggression\_def, st\_quality, fg\_attempt\_bias, punt\_aggression, clock\_management.

\- \*\*Context knobs:\*\* HFA, injury flags, rest/travel (hook), deterministic noise seed.

\- \*\*Files:\*\* /data/model/calibration/sfs\_league.json, /data/model/calibration/sfs\_quarter\_share.csv, /data/model/calibration/hfa.json.



\*\*6.2.B Output (Pre-Sim Anchoring) \_(MVP)\_\*\*



For Team A (home) vs Team B (away): \*\*EP per quarter\*\* vectors EP\_A\\\[q\\], EP\_B\\\[q\\] with constraints  

Σ EP\_A ≈ team\_ppg\_A, Σ EP\_B ≈ team\_ppg\_B, totals ≈ 2×league\_ppg, \*\*non-negative\*\*, \*\*soft cap ≤14\*\* pre-sim.



\*\*6.2.C Algorithm - From League Targets to Matchup EP/Quarter \_(MVP)\_\*\*



Helpers: z(x)=(x−50)/15; clamp(x,lo,hi); softcap(x,cap).



\- \*\*Neutral baselines:\*\* PPG\_neutral = league\_ppg; share\\\[q\\] from quarter\_share.

\- \*\*Pace→Possessions:\*\*  

&nbsp;   drives\_T = league\_drives\_per\_team \\\* (1 + w\_pace\\\*(z(pace\_T)+z(pace\_opp))/2);  

&nbsp;   ppd\_league = league\_ppg/league\_drives\_per\_team;  

&nbsp;   PPG\_pos\_T = PPG\_neutral + clamp((drives\_T−league\_drives\_per\_team)\\\*ppd\_league, ±w\_pos\_cap).

\- \*\*Efficiency matchup (Off vs Def):\*\*  

&nbsp;   O\_eff\_T = w\_qb\\\*z(QB\_T)+w\_olp\\\*z(OL\_pass\_T)+w\_olr\\\*z(OL\_run\_T)+w\_wr\\\*z(WRTE\_T)+w\_rb\\\*z(RB\_T)+w\_schem\\\*(z(run\_pass\_tendency tilt vs opp)+0.5\\\*z(aggression\_off\_T))  

&nbsp;   D\_eff\_opp = w\_pr\\\*z(pass\_rush\_opp)+w\_cov\\\*z(coverage\_opp)+w\_dl\\\*z(DL\_opp)+w\_lb\\\*z(LB\_opp)+w\_db\\\*z(DB\_opp)+w\_plan\\\*z(aggression\_def\_opp)  

&nbsp;   match\_T = clamp((O\_eff\_T − D\_eff\_opp)\\\*w\_match, ±m\_cap); PPG\_eff\_T = PPG\_pos\_T\\\*(1+match\_T).

\- \*\*Style tilt (RZ/explosive):\*\* tilt\_T = clamp(w\_rz\\\*rz\_T + w\_xp\\\*xp\_T, ±t\_cap); PPG\_style\_T = PPG\_eff\_T\\\*(1+tilt\_T).

\- \*\*Special teams:\*\* PPG\_st\_T = PPG\_style\_T + clamp(w\_k\\\*z(K\_T)+w\_st\\\*z(st\_quality\_T), ±s\_cap).

\- \*\*HFA → points:\*\* hfa\_points ≈ 1.6 PPG to home team with quarter shape \\\[0.33,0.20,0.15,0.32\\].

\- \*\*League balance guard:\*\* Move PPG\_ctx\_\\\* toward 2×league\_ppg total by δ/2 each (cap bal\_cap).

\- \*\*Zero-sum quarter tilt:\*\* bounded noise vectors ε\_T with elements in ±ε\_cap.

\- \*\*Per-quarter EP:\*\*  

&nbsp;   EP\_T\\\[q\\] = max(0, (PPG\_bal\_T\\\*share\\\[q\\])\\\*(1+ε\_T\\\[q\\]) + (PPG\_bal\_T\\\*tmw\\\[q\\]\\\*w\_tmw) + (is\_home\_T ? hfa\_points\\\*quarter\_hfa\_share\\\[q\\] : 0)) with tmw=\\\[0.05,0.10,0.00,0.10\\]. Normalize to sums; reconcile rounding.



\*\*6.2.D Targets Handed to Drive Engine \_(MVP)\_\*\*



\- ppd\_T\\\[q\\] = EP\_T\\\[q\\] / expected\_drives\_T\\\[q\\] (Q4 dampener for longer drives).

\- \*\*Per-drive outcome mix:\*\* TD/FG/No-Score from league base rates tilted by rz\_T, st\_T, xp\_T, and \*\*situational aggression\*\* (4th-down go vs opp aggression).

\- \*\*Run/Pass envelope:\*\* from pass\_rate\_neutral ± coach/matchup; \*\*situational model\*\* applies in-sim.



\*\*6.2.E Determinism \& Bounds \_(MVP)\_\*\*



Seeded RNGs {LEAGUE\_SEED, season, week, game\_id, subsystem}. Each adjustment clamped by w\_pos\_cap, m\_cap, t\_cap, s\_cap, bal\_cap, ε\_cap. No post-hoc score edits.



\*\*6.2.F Calibration Knobs (Defaults) \_(MVP)\_\*\*



w\_pace=0.15, w\_pos\_cap=1.2 pts, w\_match=0.035, m\_cap=0.12, w\_rz=0.010, w\_xp=0.008, t\_cap=0.06, w\_k=0.08, w\_st=0.04, s\_cap=0.6 pts, hfa\_points=1.6, bal\_cap=1.0 pt, ε\_cap=0.08, w\_tmw=0.35, quarter\_hfa\_share=\\\[0.33,0.20,0.15,0.32\\]. (CSV/JSON-driven.)



\*\*6.2.G Acceptance Criteria \_(MVP)\_\*\*



PPG within \*\*±0.7\*\* of league\_ppg; quarter shares within \*\*±0.01\*\*; matchup/coach sensitivities monotonic; determinism holds; all per-quarter EP non-negative and ≤ soft cap pre-sim.



\*\*6.2.H Pseudocode \_(MVP)\_\*\*



(unchanged; see prior §6.2.H hand-off function sfs\_anchor(...).)



\*\*6.2.I Pre-Game Win Probability (ELO-Based) \& Parity/Upset Hook \_(MVP; enabled)\_\*\*



\- \*\*WP:\*\* Home\_WP = 1/(1+10^(−( (ParityAdj\_Home + HFA\_ELO) − ParityAdj\_Away )/400)), with HFA\_ELO≈55.

\- \*\*Parity trigger:\*\* After Week 10, undefeated: Power−50; winless: Power+50.

\- \*\*EP modifier (zero-sum, bounded):\*\*  

&nbsp;   Δ = Home\_WP − 0.50; k\_ep=0.08; cap=±0.03.  

&nbsp;   win\_prob\_modifier\_home = clamp(k\_ep\\\*Δ, ±0.03); …\\\_away = −…\\\_home.  

&nbsp;   Apply to PPG\_ctx\_\\\* \*\*after Step 6, before Step 7\*\*. Step 7 rebalance preserves league totals.

\- \*\*Acceptance:\*\* Sum EP shift pre-balance is near-zero; bounds respected; season PPG tolerance still passes.



\*\*2.1.J Team-Adjusted Anchors (SFS refinement, MVP)\*\*



\*\*2.1.J.1 Purpose\*\*



Ensure \*\*strong teams score more and weak teams score less\*\* using \*\*per-team, per-matchup scoring anchors\*\*, while keeping completed games immutable and preserving league-level realism.



\*\*2.1.J.2 Key Definitions\*\*



\- \*\*TSB (Team Scoring Baseline):\*\* Preseason, team-level points target derived from roster strength, coaching tendencies, and health.

\- \*\*MEP (Matchup Expected Points):\*\* Game-specific, team-side points target (separate for home/away) computed from TSB with opponent/context adjustments.

\- \*\*Quarter Shares:\*\* The Q1-Q4 distribution of a team's MEP, shaped by team pace and league priors.

\- \*\*Composition:\*\* Allocation of a team's MEP into TD/FG/XP/2PT and DEF/ST scoring components.



\*\*2.1.J.3 Team Scoring Baseline (TSB)\*\*



TSB\_team = f(offense\_units, defense\_units, special\_teams, coach\_tendencies, depth/health)



\- \*\*Units (weighted):\*\* QB, OL, WR/TE, RB (offense); DL/EDGE, LB, DB (defense); K, P, KR/PR (ST).

\- \*\*Tendencies:\*\* Pace (plays/gm), aggression (4th-down/2-pt), run/pass ratio.

\- \*\*Health gates:\*\* Availability and snap-share expectations for starters vs depth.



\*\*2.1.J.4 Matchup Expected Points (MEP), per team/side\*\*



Compute \*\*separately\*\* for A and B (totals need not be symmetric):  

MEP\_{A@B} = TSB\_A  

 + α·(Off\_A − Def\_B)  

 + β·(QB\_A adj)  

 + γ·(Injury/Depth adj\_A)  

 + δ·(Context: HFA, pace, weather)  

 + ε (small seeded variance; deterministic)



\- \*\*Default rails (MVP starting point):\*\* α≈0.6, β≈0.2, γ≈0.1, δ≈0.1 (tune in calibration).

\- \*\*Clamp per-team per-game MEP:\*\* \\\[9, 38\\] points (configurable).



\*\*2.1.J.5 Quarter Shares (Q1-Q4)\*\*



\- Base on team pace/closing style blended with league priors (e.g., slightly higher Q2/Q4).

\- Apply \*\*game script sensitivity\*\* (small): trailing teams shift shares toward Q2/Q4; leading teams increase run bias and clock bleed late.



\*\*2.1.J.6 Scoring Composition (TD/FG/XP/2PT \& DEF/ST)\*\*



\- Allocate MEP to components using: red-zone efficiency, kicker quality/range, 2-pt tendency, and \*\*DEF/ST splash rates\*\* scaled by unit strength.

\- Ensure per-component caps (e.g., 2-pt attempts do not exceed realistic bounds).



\*\*2.1.J.7 In-Sim Guidance (No Retro Edits)\*\*



\- Drive outcome weights (punt/FG try/TD/TO/4th-down go) are \*\*gently nudged\*\* to track quarter-share targets.

\- Completed games are \*\*immutable\*\*; \*\*only future anchors\*\* (TSB/MEP) learn from results.



\*\*2.1.J.8 Seasonal Learning (Bounded)\*\*



TSB\_{next} = (1 − λ)·TSB\_{prev} + λ·(recent PPG, opponent-adjusted), with \*\*λ ≤ 0.15\*\*.



\- Preserves \*\*spread\*\* between teams (no hard regression to league mean).

\- Apply stabilizers (min/max deltas per week) to avoid oscillation.



\*\*2.1.J.9 Determinism \& Persistence\*\*



\- All random draws derived from namespaced, seed-based RNG; \*\*bit-for-bit reproducible\*\* event tapes under the same inputs/seed.

\- Store TSB/MEP and quarter/composition targets in game state for diagnostics and replay.



\*\*2.1.J.10 Constraints \& Failsafes\*\*



\- \*\*Bounds:\*\* Per-team MEP clamps and per-component caps enforced before sim.

\- \*\*Context rails:\*\* Extreme weather/HFA effects capped to prevent outliers.

\- \*\*Eligibility:\*\* Health/availability feeds role and pace adjustments only; does not retro-edit scores.



\*\*2.1.J.11 Acceptance \& KPIs\*\*



\- \*\*League PPG\*\* within ±0.7 of target (season aggregate).

\- \*\*Team spread:\*\* Top-10 teams typically \*\*+3 to +6 PPG\*\* vs league; bottom-10 \*\*−3 to −6 PPG\*\* (tunable).

\- \*\*No post-sim edits;\*\* reruns under same seed yield identical box scores and PBP.



\*\*2.1.J.12 Tuning Notes (Calibration)\*\*



\- Begin with α/β/γ/δ defaults; fit to target distributions over a rolling 3-week window.

\- Monitor: (a) per-team residuals (Observed − MEP), (b) quarter share drift, (c) composition realism (TD:FG ratio, 2-pt rate), (d) DEF/ST TD rates versus priors.



\*\*2.1.J.13 Cross-References\*\*



\- \*\*Depth/Health:\*\* ties to roster availability and snap expectations.

\- \*\*Schedule/Context:\*\* home field, weather, fatigue inputs.

\- \*\*Diagnostics:\*\* expose TSB/MEP, quarter shares, composition, and residuals via read-only endpoints for transparency.



\## 6.3. Clock, Possession \& Overtime Rules



15:00 quarters, \*\*3 TOs/half\*\*, 2MW in Q2/Q4. Regular-season OT 10:00 (TD ends; FG rebuttal), Playoff OT repeat full 15:00. \*\*Runoff:\*\* Δt = base\_play\_time × pace\_scalar × situational\_factor.



\## 6.4. Core Simulation Flow (Per Play)



\- \*\*Penalty check\*\* (§6.7) → 2) \*\*Choose play\*\* (§6.5) → 3) \*\*Resolve outcome\*\* (weather §6.9; pipelines §6.6) → 4) \*\*Injury check\*\* (§6.10) → 5) \*\*Fatigue \& subs\*\* (§6.11) → 6) \*\*Update state\*\* → 7) \*\*Emit PBP event\*\* (§6.14).  

&nbsp;   \*\*Variability model:\*\* deterministic divergence via coaching, matchups, script, \*\*hot-hand\*\* (§6.12).



\## 6.5. Detailed Decision Logic



\*\*6.5.1 Offensive Play-Calling (Run vs Pass)\*\*



Layered logistic: Base(down, dist, field) + GameState(score, time) + Performance(YPC/YPA, matchup) + Weather\_Modifier\_RunPass.  

Also: calibrated baseline:  

logit(pass\_rate\_base)=θ0+θ1·I(down=2)+θ2·I(down∈{3,4})+θ3·bucket(ydstogo);  

pass\_rate\_play = normalize(pass\_rate\_base × team\_tilt\_live × exp(κ0 − κ1·man + κ2·zone\_wk)).  

\*\*Tests:\*\* 3rd\&short \&lt;0.45; 3rd\&10 \&gt;0.70.



\*\*6.5.2 Tactical Play Selection (Off \& Def)\*\*



Offense: \*\*Run\*\* (Inside/Outside/Power; pick POA via OL.RunBlock vs DL.RunStop). \*\*Pass\*\* (Quick/Std/Deep/Screen) via pressure risk and WR/TE mismatch.  

Defense: Run/Pass call; \*\*Blitz\*\* (target weak protector); \*\*Coverage\*\* (Man/Zone) vs threats; \*\*Run focus\*\* Plug vs Contain.



\*\*6.5.3 Fourth-Down \& FG/Punt Decisions (EP-based)\*\*



EP\_go = p\_conv·EP(conv) + (1−p\_conv)·EP(fail); EP\_kick = max(EP\_FG(distance), EP\_punt(yardline)).  

Go if EP\_go − EP\_kick ≥ go\_margin(yardline, quarter, clock, score\_diff).  

logit(p\_conv)=φ0+φ1·distance+φ2·rush\_opt+φ3·pass\_opt+φ4·OL\_adv−φ5·DL\_adv−φ6·coverage\_adv.  

\*\*Weather\_Penalty\_FG\*\* applies to make%.



\*\*6.5.4 Two-Point vs PAT \_(MVP)\_\*\*



Deterministic chart by score/time/WP delta; success from SFS + matchup tilt.



\*\*6.5.5 Clock Strategy, TOs, Spikes, Kneels \_(MVP)\_\*\*



Hurry-up (trail ≥8 with ≤6:00 Q4 or ≤2:00 any half): pace\_scalar↓, sideline pref↑, \*\*spike\*\* ≤0:25 w/o TOs.  

Milk (lead ≥9 with ≤5:00): pace\_scalar↑, run bias +Δ. Defensive TOs ≤2:30 to prevent kneel-outs; offensive TOs to secure ≥N shots. Kneel when kneel\_out() true.



\*\*6.5.6 Field Position Model \_(MVP)\_\*\*



Kickoffs: TB→25; returns = mean\_return(opp\_coverage) ± deterministic band; TB from SFS + K power.  

Punts: net = mean\_net(punter, field\_pos) ± band; TB/I-20 odds via tables; clamp \\\[1,99\\].  

Turnovers: standard enforcement.



\*\*6.5.7 Red Zone \& Goal-to-Go Shaping \_(MVP)\_\*\*



logit(pass\_RZ)=base+ρ1·coverage\_weak+ρ2·TE\_mismatch−ρ3·front7\_power+ρ4·coach\_pref.  

TD\_bias = clamp(λ0 + λ1·OL\_adv + λ2·RB\_power + λ3·WR\_iso + λ4·QB\_scramble, ±Δmax).



\*\*6.5.8 In-Game Adaptive Play-Calling (MVP)\*\*



\*\*Purpose\*\*  

Introduce deterministic, data-driven play-calling adjustments during live simulation based on team performance, player success rates, and game context.  

This ensures that coordinators adapt to hot streaks, cold streaks, and situational pressures while keeping overall tendencies within each coach's slider profile.



\*\*6.5.8.1 Core Concept\*\*



Every coordinator maintains rolling performance averages for key play outcomes (yards per play, success rate, turnover risk).  

These are tracked through an \*\*Exponential Weighted Moving Average (EWMA)\*\* system that updates after every drive.  

The adjusted values temporarily bias future play-type probabilities without overriding base tendencies.



\*\*6.5.8.2 Performance Inputs\*\*



Each drive updates these metrics:



\- \*\*Offense\*\*

&nbsp; - Yards Per Play (EWMA)

&nbsp; - Third-Down Conversion Rate (EWMA)

&nbsp; - Pass Success Rate (Completion %, Avg Yards)

&nbsp; - Run Success Rate (Yards Gained vs. Expected)

&nbsp; - Turnover Rate (interceptions + fumbles)

\- \*\*Defense\*\*

&nbsp; - Pressure Rate (hurries + sacks / dropbacks)

&nbsp; - Stop Rate (drives ended without points)

&nbsp; - Explosive Plays Allowed (plays > 15 yds)

&nbsp; - Takeaway Rate (INT + fumbles recovered per drive)



All values are stored per team and decay at 0.35 EWMA weighting (recent drives carry greater influence).



\*\*6.5.8.3 Adaptive Logic\*\*



\- \*\*Baseline from Sliders\*\*

&nbsp; - Start with coach's run/pass and aggression sliders.

&nbsp; - Offense: PlayCall\_Weights = Base\_Slider × (1 ± Adjustment\_Factor).

&nbsp; - Defense: modifies blitz %, coverage %, and aggressiveness in same fashion.

\- \*\*Adjustment Factors\*\*

&nbsp; - If Offense Run Success > League Avg × 1.15 → increase run weight by +8%.

&nbsp; - If Offense Pass Success < League Avg × 0.85 → decrease pass weight by −6%.

&nbsp; - If Turnover Rate > League Avg × 1.20 → reduce aggression by −5%.

&nbsp; - If trailing by 10+ points in 2H → force +10% pass bias override.

&nbsp; - On defense:

&nbsp;   - If Explosive Plays Allowed > avg × 1.2 → lower blitz rate by 10%.

&nbsp;   - If Pressure Rate > avg × 1.15 → raise blitz rate by +5%.

\- \*\*Cooldowns \& Caps\*\*

&nbsp; - Changes limited to ±10% of base value within a single quarter.

&nbsp; - After each quarter, deltas decay 50% toward baseline to prevent runaway drift.

&nbsp; - Full reset at game end.



\*\*6.5.8.4 Tactical Overrides\*\*



Special cases override adaptive logic for authenticity:



\- \*\*Two-Minute Drill\*\* - Aggression and tempo forced to max; clock rules govern timeouts.

\- \*\*Goal-Line Situations\*\* - Weight run heavily (+30%) unless trailing late.

\- \*\*Kneel Down Detection\*\* - If winning and < 40 sec left with no timeouts opposing, auto kneel.



\*\*6.5.8.5 Defensive Response\*\*



Defensive coordinators read the offense's current biases each drive:



If offense\_run\_rate > baseline + 10% → raise 8-man front probability by +12%.



If offense\_pass\_rate > baseline + 10% → increase dime coverage probability by +8%.



Counters decay one drive after no longer triggered.



\*\*6.5.8.6 Data Persistence\*\*



Per-drive adaptive values are logged to:  

/data/reports/game\_adaptivity/\&lt;game\_id\&gt;.json  

Fields include team, drive\_no, offense\_weights, defense\_weights, success\_rates, and bias\_deltas.  

These records support post-game analysis and balancing.



\*\*6.5.8.7 Testing\*\*



\- Simulate 100+ games to verify no runaway bias > ±15%.

\- Confirm reset between games.

\- Verify realistic adaptation curves (teams should slightly tilt but not break identity).

\- Stress-test defensive reaction logic for loopback stability.



\*\*6.5.8.8 Cross-References\*\*



\- Section 6.5.9 - Tempo Effects (Clock Bleed / Balanced / Hurry-Up / No Huddle).

\- Section 6.10 - Injury System (usage and fatigue impacts adaptive stats).

\- Section 15.x - Play-Calling Calibration Tests.



\*\*6.5.9 Tempo Effects (Clock Bleed / Balanced / Hurry-Up / No Huddle)\*\*



\*\*Purpose\*\*  

Define how offensive and defensive tempo influences play outcome probabilities, stamina, and clock behavior.  

Each team and coach operates from a base tempo preference (see Coach Attributes → Tempo Preference).  

During a game, tempo may shift dynamically through adaptive logic or manual override for late-game strategy.



\*\*6.5.9.1 Tempo Modes\*\*



\- \*\*Clock Bleed\*\* - Slow, deliberate pace.

&nbsp; - Intended for ball-control offenses or late-lead preservation.

&nbsp; - Uses full play clock before snap.

&nbsp; - Emphasizes stamina recovery but limits big-play rhythm.

\- \*\*Balanced\*\* - Default NFL-like pace.

&nbsp; - Snap typically 12-18 seconds after ready-for-play.

&nbsp; - Neutral fatigue and rhythm profile.

\- \*\*Hurry-Up\*\* - Quickened pace short of no-huddle.

&nbsp; - Snap within 6-10 seconds.

&nbsp; - Adds tempo rhythm bonus and mild stamina drain.

\- \*\*No Huddle\*\* - Continuous high-speed tempo.

&nbsp; - Offense skips huddle; snap within 3-6 seconds.

&nbsp; - Highest rhythm bonus and fatigue penalty.



\*\*6.5.9.2 Game-Clock Impact\*\*



Approximate \*\*Seconds per Play (SPP)\*\*, including snap-to-snap interval:



\- Clock Bleed ≈ 38 - 42 s

\- Balanced ≈ 30 - 34 s

\- Hurry-Up ≈ 22 - 26 s

\- No Huddle ≈ 17 - 20 s



These SPP bands target real-NFL tempo distributions validated in Pace-of-Play testing (see Section 6.18).



\*\*6.5.9.3 Performance Modifiers\*\*



| \*\*Effect\*\* | \*\*Clock Bleed\*\* | \*\*Balanced\*\* | \*\*Hurry-Up\*\* | \*\*No Huddle\*\* |

| --- | --- | --- | --- | --- |

| Offensive Rhythm Bonus | −5 % (tempo penalty) | 0 % | +6 % | +10 % |

| Explosive-Play Chance | −4 % | 0 % | +8 % | +12 % |

| Pass Accuracy Penalty | −2 % | 0 % | −2 % | −4 % |

| Stamina Drain Per Snap | −25 % (base) | 0 % | +30 % | +60 % |

| Defensive Fatigue Effect | Low | Medium | High | Severe |



\_(Negative values = benefit to endurance; positive = extra fatigue.)\_



\*\*6.5.9.4 Stamina Interaction (In-Game Only)\*\*



\- Each player has a per-game stamina\_meter that starts at 100 at kickoff.

\- During plays, stamina\_meter decreases by the mode's Stamina Drain per Snap value from §6.5.9.3; it regenerates between drives using the base recovery curve × (1 − Drain Per Snap multiplier).

\- No persistence: stamina\_meter resets to 100 at the end of each game. There is no offseason or multi-game stamina progression/regression.

\- Minor knob policy: stamina modifiers are tuned to be secondary vs. core attributes; keep total stamina-related outcome impact to a small effect band (≈ ±2-4% on play outcomes before other caps).

\- Conditioning (CON) coach trait reduces in-game drain up to 15%.



\*\*6.5.9.5 Positive and Negative Consequences\*\*



\*\*Positives (Hurry-Up / No Huddle)\*\*



\- Higher offensive rhythm → increased yardage consistency.

\- More explosive plays due to defensive mismatch risk.

\- Forces simpler defensive substitutions.



\*\*Negatives (Hurry-Up / No Huddle)\*\*



\- Elevated fatigue → higher fumble + drop probability.

\- Slightly lower accuracy and blocking efficiency.

\- Higher injury risk (scaled +5 % for No Huddle).



\*\*Positives (Clock Bleed)\*\*



\- Improved clock control and reduced turnovers (−5 % TO probability).

\- Better stamina retention and injury avoidance (−10 % injury risk).



\*\*Negatives (Clock Bleed)\*\*



\- Reduced explosive potential (−4 %) and drive rhythm (−5 %).

\- More predictable play-calling tendencies.



\*\*6.5.9.6 Coach and AI Integration\*\*



\- Each coach has a \*\*tempo\_preference\*\* rating (0-100):

&nbsp; - 0-25 → Clock Bleed

&nbsp; - 26-50 → Balanced

&nbsp; - 51-75 → Hurry-Up

&nbsp; - 76-100 → No Huddle

\- In-game AI may override preference:

&nbsp; - Trailing by ≥ 10 pts in 2H → bump one tier up.

&nbsp; - Leading by ≥ 7 in 4Q → bump one tier down.



\*\*6.5.9.7 Weather Interaction\*\*



\- Heavy rain or snow → force pace to Balanced max.

\- Extreme heat → additional +15 % fatigue modifier.

\- Wind ≥ 20 mph → reduced explosive bonus by half.  

&nbsp;   (See Section 6.9 Weather System.)



\*\*6.5.9.8 Persistence and Telemetry\*\*



Each simulated drive logs:



\- Current tempo mode

\- SPP achieved

\- Average yardage per play

\- Fatigue index pre- and post-drive



Stored in:  

/data/reports/game\_tempo/\&lt;game\_id\&gt;.json  

Used later in Pace-of-Play validation.



\*\*6.5.9.9 Testing\*\*



\- Validate league-wide SPP averages within ±1 second of empirical NFL medians.

\- Ensure total plays/game ≈ 120 ± 10 %.

\- Verify that stamina drain scales logically by mode and is reversible between drives.

\- Confirm adaptive AI switches tempo appropriately by score/time.



\*\*6.5.9.10 Cross-References\*\*



\- Section 4.2 Clock \& Game Flow

\- Section 8.1.4 Stamina Development via Tempo Exposure

\- Section 7.8 Strength \& Conditioning (CON)

\- Section 6.18 Pace-of-Play Validation \& Calibration



\*\*6.5.10 Clock and Restart Rules + Play-Duration Targets\*\*



\*\*Purpose\*\*  

Define precise NFL-accurate game-clock behavior and restart rules that ensure realistic time-of-possession and drive pacing.  

This section governs how the clock runs, stops, and restarts after each play type, and establishes the baseline \*\*Seconds per Play (SPP)\*\* used for pace-of-play calibration.



\*\*6.5.10.1 Core Clock Rules\*\*



\- \*\*Quarter Length\*\* - 15 minutes simulated per quarter.

\- \*\*Halftime\*\* - 12 real-time seconds (simulation skip).

\- \*\*Play Clock\*\* - 40 seconds between plays (25 seconds after administrative stoppages).

\- \*\*End-of-Half/Game Exceptions\*\* - Clock stops automatically on all scoring plays, change of possession, incomplete passes, timeouts, and out-of-bounds results.



\*\*6.5.10.2 Restart Conditions\*\*



\*\*After Each Play:\*\*



\- \*\*Run (In-Bounds):\*\* Clock continues to run.

\- \*\*Run (Out-of-Bounds):\*\*

&nbsp; - Before 2:00 of 2H → restart on \_referee ready-for-play whistle.\_

&nbsp; - After 2:00 of 2H → restart on \_snap.\_

\- \*\*Completed Pass (In-Bounds):\*\* Clock runs.

\- \*\*Incomplete Pass:\*\* Clock stops; restart on snap.

\- \*\*Penalty:\*\*

&nbsp; - Administrative penalties (false start, delay, etc.) → clock restarts per original state.

&nbsp; - Live-ball penalties (holding, DPI, etc.) → stop clock; restart on ready-for-play if accepted.

\- \*\*Timeout:\*\* Clock stops; restart on snap.

\- \*\*First Down (In-Bounds):\*\*

&nbsp; - Clock stops to move chains; restarts on ready-for-play (NCAA rule disabled).

\- \*\*Change of Possession:\*\* Clock stops; restart on snap.

\- \*\*Kickoff / Punt:\*\* Clock starts only on touch; stops on possession or OOB.

\- \*\*PAT / 2-Point Conversion:\*\* Clock stopped throughout sequence.



\*\*6.5.10.3 Special Situations\*\*



\- \*\*Two-Minute Warning:\*\* Automatic stoppage at 2:00 of 2Q and 4Q.

\- \*\*Spike:\*\* Treated as incomplete pass; consumes one down and ~4 seconds.

\- \*\*Kneel:\*\* Consumes one down and ~40 seconds (or game clock remainder).

\- \*\*QB Slide:\*\* Clock continues to run (treated as in-bounds run).

\- \*\*Clock Bleed Mode (see 6.5.9):\*\* Uses full play clock minus 2-3 seconds before snap.



\*\*6.5.10.4 Play-Duration Targets\*\*



Defines average \*\*snap-to-whistle\*\* durations for each result type.  

These are calibrated against the NFL's last five-season averages.



| \*\*Play Type\*\* | \*\*Snap-to-Whistle Duration (Seconds)\*\* |

| --- | --- |

| Incomplete Pass | 5 - 6 s |

| Complete Pass (In-Bounds) | 7 - 9 s |

| Run (In-Bounds) | 6 - 8 s |

| Sack | 7 - 8 s |

| Out-of-Bounds Gain | 7 - 9 s |

| Field Goal Attempt | 5 s |

| Punt | 6 s |

| Kickoff Return | 7 s |



These durations feed the total \*\*Seconds per Play (SPP)\*\* calculation used by the Score Fidelity System and Tempo model.



\*\*6.5.10.5 Average Seconds per Play (SPP) Benchmarks\*\*



\- \*\*League Baseline:\*\* 31.8 seconds per play (2020-2024 NFL mean).

\- \*\*Target Variance:\*\* ±0.8 s leaguewide; ±1.2 s team-level RMSE.

\- \*\*Expected Plays/Game:\*\* 120 ± 10 % across both teams.



SPP is dynamically recomputed each simulation week for testing (see Section 6.18 Pace-of-Play Validation).



\*\*6.5.10.6 Penalty and Timeout Integration\*\*



\- \*\*Timeouts:\*\* Three per half; reset at halftime.

&nbsp; - 60 seconds of real-time drain in sim; stored for analytics.

\- \*\*Delay of Game:\*\* 5-yard penalty; replay down; clock resumes per prior state.

\- \*\*Clock Reset After Accepted Penalty:\*\* Sim engine recalculates elapsed seconds based on the original play type's duration category.



\*\*6.5.10.7 Testing \& Validation\*\*



\- Simulate full 16-minute quarters; verify average plays/game ≈ 120 ± 10 %.

\- Compare mean SPP and restart distribution to NFL data.

\- Confirm that OOB, penalty, and incomplete restart ratios match empirical splits:

&nbsp; - Out-of-Bounds restarts on snap ≈ 55-60 %.

&nbsp; - Penalty restarts on snap ≈ 45 %.

&nbsp; - Incompletes ≈ 12-15 % of all plays.

\- Validate that no restart condition can cause infinite or duplicate ticks.



\*\*6.5.10.8 Data Output\*\*



Each game writes a clock-profile summary:  

/data/reports/clock\_profile/\&lt;game\_id\&gt;.json  

Contains:



\- Total elapsed time per quarter

\- Average play duration per result type

\- Restart type frequencies

\- Timeout and penalty counts



Used during calibration and testing.



\*\*6.5.10.9 Cross-References\*\*



\- Section 4.2 - Clock \& Game Flow overview

\- Section 6.5.9 - Tempo Effects

\- Section 6.7 - Penalty Enforcement Logic

\- Section 6.18 - Pace-of-Play Validation (Pre-Beta Gate)



\## 6.6. Play Outcome Pipelines



\*\*6.6.1 Pass Pipeline\*\*



\*\*Pressure:\*\* P=σ(−0.7−0.05\\\*Advantage + 0.4\\\*Num\_Blitzers) (compact) \*\*or\*\* decomposed logit(pressure)=π0+π1·rush\_adv−π2·pass\_pro+π3·blitz\_rate−π4·QB\_get\_ball\_out.  

\*\*Under pressure:\*\* p\_sack = pressure×σ(σ0+σ1·DL\_finish−σ2·QB\_escape−σ3·get\_ball\_out); p\_scramble = pressure×σ(τ0+τ1·QB\_speed+τ2·man\_cov−τ3·contain); p\_throw = 1−….  

\*\*Completion (given throw):\*\* logit(p\_comp)=χ0+χ1·QB\_acc+χ2·WR\_sep−χ3·coverage−χ4·pressure\_on\_throw.  

\*\*Yards:\*\* Air ~ N(μ\_air(route,down/dist), σ\_air adj); YAC ~ N(μ\_yac(route, leverage), σ\_yac adj); Total = Air+YAC.  

\*\*Interception (given throw):\*\* p\_int = base\_int(depth) × g(bad\_acc, tight\_window, pressure, DB\_ballhawk).



\*\*6.6.2 Run Pipeline \& Ball Security\*\*



Mixture: \*\*Stuff p0 (≤0)\*\*, \*\*Chunk N(μ1≈3-6,σ1)\*\*, \*\*Explosive tail p2 (≥10/15/20)\*\*; shifts with OL\_adv, box count, RB traits, DEF tackling/awareness.  

\*\*Fumbles:\*\* MVP calibrated form (R2+ kept as alt):



\- Simple clamp (legacy): P(Fumble)=clamp(0.005 + Fumble\_Score\\\*0.001 + Team\_Quality\_Modifier\_Fumble, 0.001, 0.1);

\- \*\*Decomposed (active):\*\* p\_fum = base\_by\_pos × exp(ψ1·hit\_power − ψ2·ball\_security − ψ3·awareness) × fatigue\_factor; recovery p\_off\_rec = r0 + r1·off\_near − r2·def\_near (bounded).



\## 6.7. Penalty System



Purpose  

Model realistic NFL-style penalties with authentic yardage enforcement, acceptance and decline logic, offsetting behavior, and game-clock consequences.  

This system ensures drive outcomes, field position, and pacing remain faithful to real-world football.



6.7.1 Core Design



Penalties are generated deterministically using a seeded probability model influenced by:



\- Player discipline and awareness ratings

\- Team aggression and tempo

\- Play type and situation (passing downs, blitz frequency, etc.)

\- Coach discipline rating (future R2 hook)



Each penalty is logged as a structured event with enforcement parameters and resulting clock state.



6.7.2 Penalty Categories



A. Pre-Snap (Dead Ball)



\- False Start - 5 yards, replay down

\- Delay of Game - 5 yards, replay down

\- Offside / Neutral Zone Infraction - 5 yards, automatic restart

\- Encroachment - 5 yards, automatic first down if defense

\- Illegal Formation / Motion / Shift - 5 yards, replay down



B. Live-Ball (During Play)



\- Offensive Holding - 10 yards, repeat down

\- Defensive Holding - 5 yards, automatic first down

\- Pass Interference - Spot foul (max 40 yds), automatic first down

\- Facemask - 15 yards, automatic first down

\- Roughing the Passer / Kicker - 15 yards, automatic first down

\- Block in the Back / Clipping - 10 yards, spot enforcement

\- Chop Block - 15 yards, repeat down

\- Intentional Grounding - 10 yards and loss of down

\- Unnecessary Roughness - 15 yards, automatic first down

\- Unsportsmanlike Conduct - 15 yards, automatic first down



C. Special Teams



\- Kick Catch Interference - 15 yards, spot enforcement

\- Running into Kicker - 5 yards; Roughing = 15 yards

\- Holding / Illegal Block on Return - 10 yards from spot of foul



D. Administrative (Clock / Procedure)



\- Too Many Men - 5 yards, replay down

\- Substitution Infraction - 5 yards, replay down

\- Sideline Interference - Warning → 5 yards after repeat



6.7.3 Enforcement Rules



\- Default Enforcement

&nbsp; - Apply penalty yardage from correct enforcement spot (line of scrimmage, spot of foul, end of run, or previous spot).

&nbsp; - If multiple fouls occur, enforce the most severe (yardage or automatic first down).

\- Offsetting Penalties

&nbsp; - Equal-severity fouls by both teams during a live-ball play → "No Play." Replay down.

&nbsp; - Pre-snap offsetting fouls replay down automatically.

\- Decline Logic

&nbsp; - Offense/defense AI evaluates yardage gained vs. enforcement value and down outcome.

&nbsp; - Decline if the play result is more advantageous than enforcement.

&nbsp; - Example: 3rd \& 20, defense penalized 5 yards → offense gained 25 → AI declines.

\- Automatic First Down Conditions

&nbsp; - Defensive holding, pass interference, roughing passer/kicker, unsportsmanlike conduct, facemask.

\- Loss of Down Conditions

&nbsp; - Intentional grounding, illegal forward pass beyond the line of scrimmage.



6.7.4 Clock Integration



\- Pre-Snap Penalties: Clock remains stopped; restart according to prior state.

\- Live-Ball (Accepted): Clock stops; restart on referee ready-for-play (on snap if inside 2:00 of half).

\- Declined: Clock follows actual play result.

\- Offsetting: Reset to pre-snap time.

\- Automatic 10-Second Runoff Rule: In final 2:00, offensive penalties may trigger 10-second runoff unless timeout used.



6.7.5 Probability Model



Each play type has a baseline penalty probability (p\_base) modified by:



p\_effective = p\_base × TempoMultiplier × Aggression × (1 - Awareness/100) × (1 + Fatigue/100)



TempoMultiplier



\- Clock Bleed = 0.85

\- Balanced = 1.00

\- Hurry-Up = 1.10

\- No Huddle = 1.25



Aggression - Derived from coach slider (0.8-1.2 range)  

Fatigue - Increased likelihood when stamina < 40



Target distribution (accepted penalties per team per game):



\- 5.8 - 7.0 total

\- ~55% offensive, 45% defensive



6.7.6 Simulation Flow



\- Calculate p\_effective for all relevant infractions.

\- Resolve multiple fouls by ranking severity; enforce top result.

\- Apply yardage, down adjustment, and automatic first-down/loss-of-down as required.

\- Update team and player penalty statistics (yards, accepted, declined, offsetting).

\- Apply corresponding clock rule (Section 6.5.10).

\- Store structured penalty object in play log:

\- penalty = {type, yards, accepted, offsetting, auto\_first\_down, loss\_of\_down}



6.7.7 Statistical Output



Each game produces cumulative penalty summaries:



\- Penalties called

\- Penalties accepted

\- Yards penalized

\- Declined penalties

\- Offsetting penalties



Logged to:  

/data/reports/penalties/\&lt;game\_id\&gt;.json



6.7.8 Testing



\- Run 1,000 simulated plays per type; verify acceptance frequency within ±10% of NFL averages.

\- Ensure mean penalty yards ≈ 50 per team/game.

\- Validate auto first-down and loss-of-down behavior.

\- Confirm decline and offset scenarios follow AI logic.

\- Verify clock resets properly under all acceptance outcomes.



6.7.9 Cross-References



\- Section 6.5.10 - Clock and Restart Rules

\- Section 4.1.4 - Aggression Slider Impact

\- Section 15.x - Penalty Calibration Tests



\## 6.8. Special Teams Outcome Pipelines



\*\*FG/XP:\*\* Distance-band \*\*make%\*\* from calibration; P(Block) capped \*\*3.5%\*\*; weather penalties (§6.9).  

\*\*Punts:\*\* Distance model (mean/stdev), TB/I-20 odds; returns via same model as kicks; includes P(Block).  

\*\*Kickoffs:\*\* Touchback from K power + SFS; returns vary starting FP; rare TDs.  

\*\*Onside Kick:\*\* Late, trailing; success ≈ \*\*7%\*\*.



\## 6.9. Weather Effects System



Purpose  

Simulate realistic environmental conditions that affect gameplay, player performance, fatigue, injuries, and crowd atmosphere.  

Weather adds situational variety across stadiums, introduces strategic decisions (kicking, tempo, play-calling), and is reproducible through deterministic seeds.



6.9.1 Generation Model



Weather is generated once per scheduled game using a deterministic RNG seeded by:



seed = hash(home\_team\_id + week\_number + season\_year)



Inputs from each team's stadium profile include:



\- Latitude and region (for seasonal weighting)

\- Stadium type (Open, Retractable, Dome)

\- Turf type (Grass, Turf, Hybrid)



The generation routine selects a weather preset according to month, location, and dome status.



6.9.2 Weather Presets



\- Clear / Mild

&nbsp; - Temperature 55-75°F

&nbsp; - No precipitation

&nbsp; - Wind 0-10 mph

&nbsp; - Baseline performance

\- Hot / Humid

&nbsp; - Temperature 85-100°F

&nbsp; - Increased fatigue (+10-15%)

&nbsp; - Slightly reduced tackling and stamina recovery

&nbsp; - Elevated cramp probability (minor injury risk +3%)

\- Cold / Frigid

&nbsp; - Temperature 10-40°F

&nbsp; - Minor catching and kicking penalties (−3-5%)

&nbsp; - Slight defensive advantage (lower ball velocity, firmer turf)

\- Rain / Light Rain

&nbsp; - Temperature 40-70°F

&nbsp; - Wet ball → completion −5%, fumbles +7%

&nbsp; - Run play success unchanged; pass plays more volatile

\- Heavy Rain / Thunderstorms

&nbsp; - Increased turnover and drop chance (+12%)

&nbsp; - Kicking accuracy −10%

&nbsp; - Aggression slider forced down one tier (more conservative AI)

\- Snow / Heavy Snow

&nbsp; - Ball velocity −10%, player traction −8%

&nbsp; - Run success +5% (defenses slower to react)

&nbsp; - Pass accuracy −10%

&nbsp; - Clock pace effectively slower (average play duration +2s)

\- Windy / Gusty

&nbsp; - Wind 20-35 mph

&nbsp; - Deep pass accuracy −8%

&nbsp; - Field goal accuracy −12%

&nbsp; - Direction bias applied per quarter (wind rotation logic)



6.9.3 Dome / Retractable Stadium Rules



\- Dome: Weather effects disabled except "temperature neutral" (72°F).

\- Retractable: 50% chance roof closed if precipitation probability > 40%.

\- AI adjusts tempo to Balanced when roof open under precipitation.



6.9.4 Gameplay Modifiers



Passing



\- Completion %, velocity, and trajectory affected by wind and precipitation.

\- Max passing distance reduced up to 15% under heavy wind or snow.



Rushing



\- Rain/snow increase run success slightly (defensive footing penalty).

\- Fumble chance rises with rain intensity.



Kicking



\- Accuracy reduced by wind (−0.5% per mph above 15).

\- Distance reduced by temperature (−1 yd per 10°F below 50).



Stamina \& Fatigue



\- Hot conditions: stamina drain +10-15%.

\- Cold conditions: minor fatigue reduction (−5%).

\- Snow: added +5% stamina drain due to heavier exertion.



Injuries



\- Wet or icy surfaces raise soft-tissue injury risk by 5-10%.

\- Heat increases cramp frequency but reduces joint injury probability.



All weather-driven stamina/fatigue effects are \*\*in-game-only\*\* and \*\*reset after the game\*\*.



6.9.5 Clock \& Tempo Integration



\- Heavy Rain or Snow → Tempo capped at Balanced.

\- Heat above 95°F → Fatigue multiplier +15%, coaches with Conditioning trait mitigate by −10%.

\- Wind > 25 mph → Aggression slider −5%; fewer deep throws.

\- Clear or Cold conditions have no tempo restrictions.



6.9.6 Presentation \& Data Persistence



Each weather profile writes to:  

/data/reports/weather/\&lt;game\_id\&gt;.json



Logged fields:



\- Temperature

\- Wind speed/direction

\- Precipitation type \& intensity

\- Surface type

\- Roof state

\- Derived modifiers (catch %, fatigue %, kick penalties, etc.)



These are used for analytics, calibration, and UI display (e.g., "Light Snow - 28°F, 10 mph Wind").



6.9.7 Testing \& Calibration



\- Simulate 1,000 games per stadium; confirm realistic weather frequency by region:

&nbsp; - Rain: 15-20%

&nbsp; - Snow: 5-8% (northern stadiums only)

&nbsp; - Wind > 20 mph: 10-12%

&nbsp; - Hot/Humid: 8-10%

\- Verify league-wide averages align with NOAA distributions (2020-2024).

\- Validate offensive yardage variance ±5% between clear vs. heavy weather sets.



6.9.8 Cross-References



\- Section 4.3 - Stadium Attributes

\- Section 6.5.9 - Tempo Effects

\- Section 6.10 - Injury Model (weather risk integration)

\- Section 7.6 - Player Stats (weather-tagged aggregates)

\- Section 15.x - Weather Validation Tests



\## 6.10. Player Injury System



Purpose  

Simulate realistic injuries during plays and practice, with deterministic generation, severity→duration mapping, Return-to-Play (RTP) effects, roster/IR behavior, and clear hooks to the persistence model (see 3.8).



6.10.1 Injury Generation (In-Game)



Trigger timing



\- Check for injury at end of a play segment that plausibly produces contact or strain:

&nbsp; - Runs, completed passes with YAC, sacks, QB hits, special-teams returns, contested catches, trench short-yardage, and high-tempo sequences.



Baseline probability



\- Start from a base incidence per 100 plays by play type:

&nbsp; - Runs: low

&nbsp; - Pass (QB/WR/TE/DB exposure): medium

&nbsp; - Sacks/QB hits and special teams: elevated

\- Modify by multipliers (all multiplicative):

&nbsp; - Player injury\_proneness (0-100): +0% to +50% risk

&nbsp; - Fatigue (from 4.1.5a): +0% to +30% risk when fatigue > 0.4

&nbsp; - Tempo (6.5.9): +5% Hurry-Up, +10% No Huddle; −5% Clock Bleed

&nbsp; - Weather (6.9): +5-10% in rain/snow (slips), +5-8% in hot/humid (cramps)

&nbsp; - Hit severity proxy: sacks/defensive contact add +10-20%



Determinism



\- Use seed injury\_seed = hash(game\_id + play\_index + player\_id) to draw once per eligible player on the play.



6.10.2 Injury Classification



Type selection



\- Weighted by position and play context:

&nbsp; - RB/WR/CB: hamstring, ankle, knee

&nbsp; - OL/DL/LB: knee (MCL/ACL), shoulder, back

&nbsp; - QB: shoulder, rib, concussion, hand

&nbsp; - ST returners: ankle, concussion, shoulder



Severity



\- MINOR, MODERATE, MAJOR chosen by weighted draw:

&nbsp; - Baseline: 65% minor, 25% moderate, 10% major (tuned by type and context)



Duration buckets (weeks\_out)



\- Minor: 0-2 weeks (0 allows "questionable - returns same game")

\- Moderate: 2-5 weeks

\- Major: 6-16 weeks (ACL/MCL/achilles may exceed; cap at season end for MVP)



When created, immediately persist an entry per 3.8 with is\_active=true.



6.10.3 Same-Game Availability (Questionable/Out)



Return logic



\- If Minor with "stinger/contusion" subtype:

&nbsp; - 50-70% chance to return later in the game after a cooldown of 1-3 drives.

\- Moderate/Major: out for game.



On-return RTP penalty (in-game)



\- Apply a temporary play penalty (−5% to −12% to position-relevant attributes) that lasts the remainder of the game and is recorded as rtp\_penalty.



6.10.4 Return-to-Play (Post-Week) Mechanics



Weekly loop



\- At weekly sim tick:

&nbsp; - Decrement weeks\_out by 1 (min 0).

&nbsp; - When weeks\_out == 0, player switches to RTP status.



RTP taper



\- Start rtp\_penalty at:

&nbsp; - Minor: 0.05

&nbsp; - Moderate: 0.10

&nbsp; - Major: 0.15

\- Decay by 0.05 per week played until 0.

\- Effective attribute formula during RTP:

&nbsp; - effective = base\_attribute × (1 − rtp\_penalty)



Auto-resolution



\- When weeks\_out == 0 and rtp\_penalty == 0, set is\_active=false (injury closed).



6.10.5 Roster and IR Rules (MVP)



\- If weeks\_out ≥ 4, team may set placed\_on\_ir=true (see 3.8).

\- Player on IR:

&nbsp; - Does not count toward 53-man active roster.

&nbsp; - No mid-season return in MVP (R2 can add Designated-to-Return).

\- Depth chart auto-adjust:

&nbsp; - When a starter is injured, promote the next slot; log the change in the game and team reports.



6.10.6 Position-Specific Effects (Examples)



\- QB: throw\_power/accuracy reduced first; sack risk rises with shoulder/rib injuries.

\- RB/WR/CB: speed/agility hit under ankle/hamstring; fumble risk +2-4% on hand/wrist.

\- OL/DL: strength/engage wins reduced on knee/shoulder; stamina loss increases 5-10%.

\- K/P: FG/PU accuracy and max distance reduced on leg/hip/back.



All effects compound with fatigue (4.1.5a) and weather (6.9) but are clamped so total debuff ≤ 20% in MVP.



\*\*Note (Scope):\*\* Stamina impacts from injuries are \*\*in-game-only\*\*. Between games, stamina\_meter resets to 100. Only the injury \*\*RTP penalty\*\* persists across games until resolved (see §6.10.8 lifecycle).



6.10.7 Practice and Non-Game Injuries



\- Weekly background draw per player using lower base rates (about 25-35% of in-game incidence).

\- Types skew to soft-tissue (hamstring, groin, back).

\- Persist identical to in-game injuries with game\_id = null.



6.10.8 Data Flow and Persistence



\- On creation or update, write to Injury table (3.8):

&nbsp; - injury\_type, severity, weeks\_out, rtp\_penalty, is\_active, placed\_on\_ir, date\_injured, expected\_return\_week.

\- All lifecycle transitions (created, weekly decrement, RTP start, closed) are logged to:

&nbsp; - /data/reports/injuries/\&lt;season\&gt;/\&lt;team\_id\&gt;.json



6.10.9 Tuning Targets (League-Level)



\- Games with any injury event: ~18-28%

\- Avg team games missed per season due to injury: target realistic mid-teens

\- Distribution by severity (season totals):

&nbsp; - Minor ~60-70%

&nbsp; - Moderate ~20-30%

&nbsp; - Major ~8-12%

\- Position share:

&nbsp; - RB/WR/CB collectively highest, OL/DL next, QB lowest by count but highest leverage



These targets are validated in Section 15.x tests.



6.10.10 Testing



\- Unit: create → weekly decrement → RTP → resolution; assert persistence fields.

\- Property: injury incidence per 10k plays within tolerance bands (±10%).

\- Scenario: IR eligibility toggles only when weeks\_out ≥ 4; roster count updates.

\- Regression: re-sim same seed reproduces identical injury set and durations.

\- UI: depth chart reshuffles correctly on injury/return events.



6.10.11 Cross-References



\- Section 3.8 Injury (schema, API)

\- Section 4.1.5a Stamina-Fatigue Model (fatigue coupling)

\- Section 6.5.9 Tempo Effects (tempo risk modifiers)

\- Section 6.9 Weather (surface/heat risk)

\- Section 7.6 Stats (games missed, durability)

\- Section 15.x Testing (incidence calibration)



\## 6.11. Player Fatigue \& Stamina



Stamina\_Loss = (Base\_Loss + Exertion\\\*Play\_Impact) \\\* (1 − (stamina − 75)\\\*0.01); penalties to physical attributes as stamina drops; AI subs at thresholds.



Reset \& Scope Policy (Stamina as In-Game-Only Meter)



\- \*\*Reset:\*\* stamina\_meter returns to \*\*100 at the start of each new game\*\*.

\- \*\*Exception:\*\* if a player is under an active \*\*RTP (return-to-play) injury penalty\*\*, stamina\_meter \*\*still starts at 100\*\*, but the \*\*effective stamina impact multiplier\*\* may be reduced by the RTP flag (see §6.10).

\- \*\*Minor factor:\*\* total outcome influence from stamina penalties (drops in physical attributes, substitution patterns) must remain \*\*secondary\*\*; tune cumulative stamina effects to stay within \*\*tight caps\*\* so they do not dominate core attribute or call-selection effects.



\## 6.12. Variability \& Usage Model (Deterministic)



Team expected plays; opponent-aware baseline pass rate; per-drive script tilt (cap ±6 pp/quarter); player share \*\*softmax\*\* (RB carries, WR/TE targets); \*\*hot-hand\*\* when success ≥ threshold; deterministic \*\*jitter\*\* on attempts/carries; safeguards (role caps, asymmetry floor). (Coefficients as prior.)



\## 6.13. Statistical Outputs \& Definitions



Box score, full PBP, and player stat lines. Truth set \& edge rules: sacks subtract from \*\*team passing yards\*\*; QB scrambles as \*\*rushing\*\*; lateral simplification; sack-fumble attribution. Leaders recomputed after each game with qualifiers.



\## 6.14. PBP - Event Schema \& Formatting



Structured fields (event\_id, quarter, clock, down, distance, yardline, play\_type, actors, raw/derived results, scoring, turnover, penalties\\\[\\], timeout, next LOS). Renderer emits consistent lines; TD/XP adjacent; drive summaries at DRIVE\_END. Parsing PBP reproduces box totals.



\## 6.15. Diagnostics, Calibration \& Performance



\- \*\*Consistency:\*\* PBP scoring sums to box; quarters sum to final.

\- \*\*SFS:\*\* PPG ±0.7; quarter shares ±0.01; run/pass ±2 pp window.

\- \*\*Penalties (data-fit):\*\* targets in §6.7 acceptance pass.

\- \*\*Injuries:\*\* incidence \& caps pass.

\- \*\*Weather:\*\* profile frequencies \& wind means within bounds; CLEAR vs RAIN/SNOW FG deltas (≥2/≥4 pp).

\- \*\*Determinism:\*\* identical seeds ⇒ identical event tapes.

\- \*\*Variance \& correlation:\*\* usage variance floors, attribute correlations as specified.

\- \*\*Performance:\*\* per-game median ≤15 ms; PBP render ≤5 ms; season ≤12 s; lookups O(1).



\## 6.16. Data Tables (Implementation Guide)



player\_game\_totals, player\_game\_splits; pressure\_attribution and coverage\_targets supported (can be stubbed light in MVP if needed); participation\_snaps optional to defer.



\## 6.17. Seed Policy \& Determinism



Base seed from Safe Config; game\_seed = hash(season, week, game\_id, base\_seed); pbp\_text\_seed = hash(game\_seed, 0xBEEF). Drive consumption order: \*\*drive selection → play-type → outcome → stats → clock\*\*. Replay with same config is \*\*bitwise-identical\*\*.



\## 6.18. Mini Glossary



EP (Expected Points), PPD (Points/Drive), HFA, Quarter Share, Zero-Sum Tilt, Deterministic Jitter, Advantage Scores, R2P (Return-to-Play).



\*\*Part 2 - Merge Report\*\*



\*\*Coverage Map\*\*



\- \*\*6.1, 6.3-6.6, 6.12-6.17:\*\* From earlier canonical merge (A-E + D) without omission.

\- \*\*6.2.I Parity Hook:\*\* Promoted to \*\*MVP\*\* and integrated at the \*\*end of Step 6\*\* (then Step 7 rebalance).

\- \*\*6.7 Penalties:\*\* Switched from hand-tuned to \*\*data-calibrated Option 1\*\* with bounded GLM fit, acceptance gates, and JSON schema.

\- \*\*6.9 Weather:\*\* Promoted to \*\*MVP\*\* with profiles, monthly mixes, wind bands, and decision/outcome hooks.

\- \*\*6.10 Injuries:\*\* Promoted to \*\*MVP\*\* with buckets/durations/R2P and caps; JSON schema specified.



\*\*Conflicts Resolved\*\*



\- \*\*Feature tiering (MVP vs R2):\*\* Penalties, Injuries, Weather, Parity hook promoted to \*\*MVP\*\*; SFS tolerances unchanged.

\- \*\*Penalty source of truth:\*\* Hand-tuned tables replaced by \*\*bounded data-fit\*\* while preserving rule abstractions for yards/auto-first (keeps engine stability).

\- \*\*Weather scope:\*\* Now affects both \*\*decisions\*\* (slight conservatism) and \*\*outcomes\*\* (comp/kicks/fumbles), not FG-only.



\*\*De-duplications \& Normalizations\*\*



\- Retained one \*\*penalties.json\*\* schema; consolidated rules \& acceptance into §6.7.

\- Kept single \*\*injuries.json\*\* with buckets and R2P; removed prior "OFF in MVP" statements.

\- Weather modifiers centralized in \*\*weather.json\*\*; removed scattered mentions.



\*\*Open Questions\*\*



\- \*\*Target season(s) for penalty fit:\*\* default to latest available season or rolling 3-year blend-confirm choice for the initial penalties.json.

\- \*\*Stadium profile map completeness:\*\* provide final team→stadium→profile mapping list.

\- \*\*Trainer ratings source:\*\* confirm scale or derive from staff data; otherwise use neutral 50 for MVP.



\## 6.19 Pace-of-Play Validation \& Calibration (Pre-Beta Gate)



\*\*Purpose\*\*  

Verify that simulated games produce authentic NFL-level pacing, play totals, and time-of-possession patterns before public testing.  

This subsystem compares aggregate league results to historical NFL benchmarks (five-season average) and auto-adjusts internal tempo multipliers when outside tolerance.



\*\*6.19.1 Data Sources\*\*



\- \*\*In-Sim Telemetry:\*\* Each play and drive writes snap\_time, play\_duration, tempo\_mode, and clock\_state to /data/reports/game\_tempo/\&lt;game\_id\&gt;.json.

\- \*\*League Summary:\*\* A post-week aggregation job merges all telemetry files to tempo\_league\_summary.json.

\- \*\*Benchmark File:\*\* /data/model/calibration/pace\_targets.json contains real-NFL averages (updated annually).



\*\*6.19.2 Validation Targets\*\*



\*\*League-Level Benchmarks (based on 2020-2024 NFL averages)\*\*



\- Mean Seconds per Play (SPP): 31.8 ± 0.8 s

\- Mean Plays per Team per Game: 60 ± 5 plays

\- Mean Plays per League Game: 120 ± 10 plays

\- Time of Possession Variance: ≤ ±2 minutes RMSE

\- Tempo Mode Usage:

&nbsp; - Clock Bleed ≤ 25 %

&nbsp; - Balanced ≈ 55 %

&nbsp; - Hurry-Up ≈ 15 %

&nbsp; - No Huddle ≤ 5 %



\*\*6.19.3 Calibration Algorithm\*\*



\- \*\*Aggregate\*\* SPP and plays/game for all completed games.

\- \*\*Compare\*\* to benchmark tolerances.

\- \*\*Compute Adjustment Factor:\*\*

\- delta = (league\_spp - target\_spp) / target\_spp

\- tempo\_multiplier = 1 - clamp(delta, -0.05, 0.05)

\- \*\*Apply\*\* updated multiplier globally in Tempo Effects (6.5.9) before next sim batch.

\- \*\*Persist\*\* new value to /data/model/calibration/tempo\_calibration.json.



This keeps tempo self-correcting and reproducible via seed.



\*\*6.19.4 Regression Checks\*\*



Each nightly test simulates ≥ 64 games and records:



\- League mean SPP

\- Standard deviation of SPP

\- Plays per game distribution

\- Tempo mode usage frequency

\- Outlier thresholds (> ±15 % from target)



Failures trigger an alert in the log summary.



\*\*6.19.5 Pre-Beta Gate Criteria\*\*



To pass the gate and advance to closed beta:



| \*\*Metric\*\* | \*\*Requirement\*\* |

| --- | --- |

| Avg SPP | 31.0 - 32.6 s |

| Avg Plays/Game | 115 - 125 |

| No team > ±10 % from league SPP avg | Pass |

| Tempo mode ratios within target bands | Pass |

| Time-of-Possession variance ≤ ±2 min | Pass |



If any fail, adjust tempo multipliers and re-run calibration until all thresholds pass three consecutive regression runs.



\*\*6.19.6 Outputs \& Reports\*\*



Generated automatically after each calibration cycle:



\- \*\*league\_tempo\_report.csv\*\* - summary of league/game averages.

\- \*\*tempo\_drift\_chart.png\*\* - plot of week-to-week drift.

\- \*\*tempo\_calibration.json\*\* - latest applied coefficients.

\- \*\*tempo\_anomalies.log\*\* - detailed failures for dev analysis.



All stored under /data/reports/calibration/.



\*\*6.19.7 Cross-References\*\*



\- Section 6.5.9 Tempo Effects

\- Section 6.5.10 Clock and Restart Rules

\- Section 6.10 Injury System (tempo fatigue impact)

\- Section 15.x Automated Regression Suite



\# 7\\. League Systems \& Progression



This section details the core systems that govern how players are rated, how teams are ranked, and how the league structure progresses through the playoffs and awards season.



\## 7.1. Player Ratings \& Overall Formulas



A linear model converts a player's individual attributes into a single \*\*Overall\*\* rating (0-99). Each position has its own set of weights so that attributes are valued appropriately for the role. These Overall ratings are consumed by depth charts, AI roster decisions, simulation, and the UI for quick comparison. \*\*Stamina (rating) vs stamina\_meter (gameplay):\*\* The stamina \*\*rating\*\* is a static attribute used to parameterize \*\*in-game drain/regen\*\*; the \*\*stamina\_meter\*\* is the per-game value that \*\*resets to 100 each new game\*\* (unless modified by an active RTP injury penalty).



\- \*\*Core Principles:\*\*

\- \*\*Deterministic outputs:\*\* Same attributes and weights produce the same Overall.

\- \*\*Position-specific models\*\* are always preferred over a global model.

\- \*\*Final Overall rating is clamped to 0-99.\*\*

\- Core Linear Formula:  

&nbsp;   overall\_rating ≈ intercept + Σ(weight × attribute)



\*\*7.1.1. Position-Specific Player Overall (Intercepts \& Top-15 Weights)\*\*



\_Note: All weights add to the intercept; attributes are ordered by absolute weight (most impactful first).\_



| \*\*Position\*\* | \*\*Intercept\*\* | \*\*Top-15 Weighted Attributes\*\* |

| --- | --- | --- |

| \*\*C\*\* | 26.8034 | pass\_block\_power (0.8478), pass\_block\_finesse (0.8266), run\_block\_power (0.7811), run\_block\_finesse (0.7409), awareness (0.7044), impact\_block (0.6716), strength (0.6252), stamina (0.3157), injury (0.2452), acceleration (0.2325), agility (0.2063), speed (0.1841), balance (0.1769), potential (0.1599) |

| \*\*CB\*\* | 23.0679 | man\_coverage (0.9797), zone\_coverage (0.9188), press (0.7143), awareness (0.6924), speed (0.6534), acceleration (0.6281), agility (0.5857), jumping (0.4742), play\_recognition (0.4339), tackle (0.3471), pursuit (0.3148), catching (0.2144), stamina (0.1981), potential (0.1522) |

| \*\*DT\*\* | 29.4126 | block\_shed (0.9267), power\_moves (0.8821), strength (0.8395), tackle (0.7149), awareness (0.6911), pursuit (0.5447), finesse\_moves (0.3966), stamina (0.2922), acceleration (0.2688), injury (0.2395), agility (0.2116), speed (0.1944), play\_recognition (0.1831), potential (0.1618) |

| \*\*FB\*\* | 24.3881 | lead\_block (0.8735), impact\_block (0.8246), run\_block\_power (0.6982), run\_block\_finesse (0.6641), carry (0.4958), awareness (0.4682), strength (0.4216), acceleration (0.3187), stamina (0.2613), agility (0.2461), speed (0.2237), catching (0.2035), injury (0.1764), potential (0.1492) |

| \*\*FS\*\* | 23.9498 | zone\_coverage (0.9511), man\_coverage (0.7446), pursuit (0.6469), awareness (0.6117), speed (0.5864), acceleration (0.5632), tackle (0.4478), agility (0.4231), play\_recognition (0.3789), jumping (0.2941), stamina (0.2147), catching (0.2024), injury (0.1773), potential (0.1507) |

| \*\*HB\*\* | 22.5814 | speed (0.8949), acceleration (0.8421), agility (0.7154), carry (0.6610), break\_tackle (0.6377), elusiveness (0.6115), trucking (0.5328), awareness (0.4107), stamina (0.3079), catching (0.2551), injury (0.2078), spin\_move (0.1854), juke\_move (0.1762), potential (0.1426) |

| \*\*K\*\* | 21.7743 | kick\_accuracy (1.0739), kick\_power (0.9422), awareness (0.4368), stamina (0.2921), injury (0.1837), potential (0.1479), acceleration (0.1056), speed (0.0821), agility (0.0716), play\_recognition (0.0542), strength (0.0528), balance (0.0497), jumping (0.0385), carry (0.0346) |

| \*\*LE\*\* | 26.1457 | finesse\_moves (0.9024), block\_shed (0.8291), power\_moves (0.7958), strength (0.7235), tackle (0.6022), awareness (0.5696), pursuit (0.4981), stamina (0.3175), acceleration (0.2849), agility (0.2086), injury (0.1938), speed (0.1847), play\_recognition (0.1666), potential (0.1512) |

| \*\*LG\*\* | 26.6079 | pass\_block\_power (0.8615), pass\_block\_finesse (0.8352), run\_block\_power (0.7756), run\_block\_finesse (0.7398), impact\_block (0.6823), awareness (0.6537), strength (0.6154), stamina (0.3219), injury (0.2416), agility (0.2093), acceleration (0.1995), speed (0.1824), balance (0.1717), potential (0.1588) |

| \*\*LOLB\*\* | 24.7132 | block\_shed (0.8124), pursuit (0.7449), tackle (0.6883), awareness (0.6127), finesse\_moves (0.5741), strength (0.4738), play\_recognition (0.3935), acceleration (0.3021), stamina (0.2574), agility (0.2265), speed (0.2126), injury (0.1845), jumping (0.1623), potential (0.1468) |

| \*\*LT\*\* | 26.9055 | pass\_block\_power (0.8724), pass\_block\_finesse (0.8469), run\_block\_power (0.7910), run\_block\_finesse (0.7488), impact\_block (0.6892), awareness (0.6586), strength (0.6135), stamina (0.3244), injury (0.2432), agility (0.2110), acceleration (0.2017), speed (0.1831), balance (0.1735), potential (0.1598) |

| \*\*MLB\*\* | 25.6678 | tackle (0.8387), block\_shed (0.7772), pursuit (0.7245), awareness (0.6683), strength (0.5321), play\_recognition (0.4217), acceleration (0.3099), stamina (0.2664), agility (0.2351), speed (0.2188), injury (0.1866), jumping (0.1712), potential (0.1463), zone\_coverage (0.1325) |

| \*\*P\*\* | 21.5129 | kick\_power (1.0544), kick\_accuracy (0.9281), awareness (0.4215), stamina (0.2867), injury (0.1799), potential (0.1458), acceleration (0.1024), speed (0.0807), agility (0.0691), play\_recognition (0.0531), strength (0.0508), balance (0.0485), jumping (0.0376), carry (0.0334) |

| \*\*QB\*\* | 22.3387 | throw\_accuracy\_short (0.9342), throw\_accuracy\_mid (0.9031), throw\_accuracy\_deep (0.8716), throw\_power (0.7449), awareness (0.7063), play\_action (0.5167), throw\_on\_run (0.4822), acceleration (0.2685), stamina (0.2546), agility (0.2219), speed (0.2034), injury (0.1781), break\_sack (0.1648), potential (0.1499) |

| \*\*RE\*\* | 26.0321 | finesse\_moves (0.8951), block\_shed (0.8223), power\_moves (0.7884), strength (0.7199), tackle (0.5972), awareness (0.5661), pursuit (0.4927), stamina (0.3158), acceleration (0.2830), agility (0.2065), injury (0.1924), speed (0.1829), play\_recognition (0.1653), potential (0.1507) |

| \*\*RG\*\* | 26.5342 | pass\_block\_power (0.8597), pass\_block\_finesse (0.8331), run\_block\_power (0.7739), run\_block\_finesse (0.7379), impact\_block (0.6810), awareness (0.6523), strength (0.6141), stamina (0.3211), injury (0.2407), agility (0.2086), acceleration (0.1989), speed (0.1818), balance (0.1712), potential (0.1582) |

| \*\*ROLB\*\* | 24.6551 | block\_shed (0.8102), pursuit (0.7421), tackle (0.6861), awareness (0.6108), finesse\_moves (0.5716), strength (0.4719), play\_recognition (0.3922), acceleration (0.3012), stamina (0.2566), agility (0.2258), speed (0.2119), injury (0.1839), jumping (0.1618), potential (0.1462) |

| \*\*RT\*\* | 26.8113 | pass\_block\_power (0.8706), pass\_block\_finesse (0.8451), run\_block\_power (0.7891), run\_block\_finesse (0.7467), impact\_block (0.6871), awareness (0.6570), strength (0.6117), stamina (0.3233), injury (0.2424), agility (0.2103), acceleration (0.2009), speed (0.1827), balance (0.1731), potential (0.1593) |

| \*\*SS\*\* | 24.1026 | zone\_coverage (0.9177), man\_coverage (0.7206), pursuit (0.6411), awareness (0.6067), speed (0.5814), acceleration (0.5579), tackle (0.4434), agility (0.4193), play\_recognition (0.3755), jumping (0.2915), stamina (0.2125), catching (0.2004), injury (0.1755), potential (0.1490) |

| \*\*TE\*\* | 24.8894 | catching (0.7841), route\_running\_short (0.7316), route\_running\_mid (0.6849), run\_block\_power (0.5742), run\_block\_finesse (0.5417), awareness (0.5138), strength (0.4694), acceleration (0.3291), stamina (0.2698), agility (0.2477), speed (0.2260), injury (0.1814), jumping (0.1685), potential (0.1475) |

| \*\*WR\*\* | 23.1048 | catching (0.8426), route\_running\_short (0.7897), route\_running\_mid (0.7435), route\_running\_deep (0.7066), release (0.5994), awareness (0.5672), speed (0.5528), acceleration (0.5341), agility (0.4826), jumping (0.3987), stamina (0.2744), catch\_in\_traffic (0.2315), injury (0.1896), potential (0.1518) |



\## 7.2. Team Power Ratings (ELO System)



A weekly ELO-style rating estimates true team strength beyond their win-loss record. The UI label for this is "Power Ranking."



\- \*\*Constants:\*\*

\- League baseline: \*\*1500\*\*

\- K-factor: \*\*20\*\*

\- Home-Field Advantage (HFA): \*\*55 ELO\*\* (applied to home team pre-game only)

\- \*\*Per-Game Update Formula:\*\*



\- \*\*Expected Outcome:\*\*



\- D = (Rating\_H + 55) − Rating\_A

\- P\_H = 1 / (1 + 10^(-D/400))



\- \*\*Actual Result:\*\*



\- S\_H = 1 (home win), 0.5 (tie), 0 (home loss).



\- \*\*Margin of Victory (MOV) Multiplier:\*\*



\- PD = |HomeScore − AwayScore|

\- M = ln(PD + 1) · (2.2 / (((Rating\_Winner − Rating\_Loser) · 0.001) + 2.2))



\- \*\*ELO Change:\*\*



\- Δ = K · M · (S\_H − P\_H)

\- New ratings: Home = Rating\_H + Δ, Away = Rating\_A − Δ.

\- Off-Season Regression: At the start of a new season, all team ratings are regressed toward the league mean of 1500:  

&nbsp;   NewSeasonElo = 0.67 · PreviousFinal + 0.33 · 1500



7.3. Playoffs \& Tie-Breakers



\- \*\*Bracket Size:\*\* 14 teams total (7 per conference). The #1 seed in each conference receives a first-round bye.

\- \*\*Seeding:\*\* The four division winners are seeded 1-4 based on record. The three non-division winners with the best records are seeded 5-7 as Wild Cards.



\*\*7.3.1. Tie-Breaker Procedures (Applied Sequentially)\*\*



\_Stop at the first step that breaks the tie. For 3+ teams, apply the division tie-breaker first to determine the division winner; remaining teams then re-enter the wild card tie-breaker.\_



\*\*A) To Break a Tie Within a Division (Two Teams)\*\*



\- Head-to-head record.

\- Division record (best W-L-T%).

\- Common games record (best W-L-T%).

\- Conference record (best W-L-T%).

\- Strength of victory (combined record of opponents defeated).

\- Strength of schedule (combined record of all opponents).

\- Combined ranking among conference teams in points scored and points allowed.

\- Combined ranking among all teams in points scored and points allowed.

\- Best net points in common games.

\- Best net points in all games.

\- Best net touchdowns in all games.

\- Coin toss.



\*\*B) To Break a Tie For a Wild Card Spot (Two Teams)\*\*



\- Head-to-head, if applicable.

\- Conference record (best W-L-T%).

\- Common games record (min. four).

\- Strength of victory.

\- Strength of schedule.

\- Combined ranking among conference teams in points scored and points allowed.

\- Combined ranking among all teams in points scored and points allowed.

\- Best net points in conference games.

\- Best net points in all games.

\- Best net touchdowns in all games.

\- Coin toss.



\*\*C) Multi-Team Ties (Three or More)\*\*



Use the same category order, but evaluate collective head-to-head among all tied teams where applicable. When one team is separated at any step, eliminate it and re-apply the procedure to the remaining teams. When reduced to two teams, revert to the appropriate two-team tie-breaker.



\## 7.4 Awards



\*\*7.4.1 Principles\*\*



\- \*\*Deterministic, no fan voting.\*\* All honors come from stats + fixed context multipliers.

\- \*\*Transparent.\*\* Inputs/weights live in config; tie-breakers are fixed and seeded.

\- \*\*Stable for rookies.\*\* OROY/DROY exclude Clutch and Team-Wins to avoid usage bias/small-sample noise.

\- \*\*Reproducible.\*\* Seeded RNG only breaks absolute ties after the full chain.



Weekly Snapshot Immutability:



\- Once a week's Awards Top-5 and Leaderboards are computed and displayed, they are immutable snapshots. Later stat corrections do not change published Top-5 for past weeks.



Season-End Awards:



\- \\- Use final audited stats. Ties break via deterministic seed.



\*\*7.4.2 Awards Set \& Scope\*\*



\- \*\*Season-end:\*\* League MVP, OPOY, DPOY, OROY, DROY, COTY, GMOTY, \*\*Pro Bowl\*\* (per-conference starters; no game).

\- \*\*Post-championship:\*\* \*\*Super Bowl MVP\*\* (single game, winner must be from winning team).

\- \*\*Weekly surface:\*\* Live \*\*Top-5 Awards Race\*\* per award (Weeks 1-18) powers Dashboard/Stats widgets.



\*\*7.4.3 Eligibility \& Definitions\*\*



\- \*\*Rookie:\*\* career\_seasons\_played == 0 entering season.

\- \*\*Minimum playing time\*\* (configurable examples):

&nbsp; - QB: ≥10 starts \*\*or\*\* ≥60% team offensive snaps

&nbsp; - RB/WR/TE: ≥8 GP \*\*and\*\* ≥25% offensive snaps

&nbsp; - OL: ≥10 starts \*\*or\*\* ≥60% offensive snaps

&nbsp; - Front-7/DB: ≥8 GP \*\*and\*\* ≥35% defensive snaps

&nbsp; - K/P: ≥12 GP

\- \*\*Rookie floors (OROY/DROY):\*\* ≥8 GP \*\*or\*\* ≥300 side-specific snaps.

\- \*\*Pro Bowl floors:\*\* same as above; \*\*Returner\*\* needs ≥20 returns \*\*or\*\* ≥12 GP with KR/PR snaps.

\- \*\*Conferences:\*\* Two (AFC/NFC or generic) used only for Pro Bowl selection.

\- \*\*Rookie Awards Policy:\*\* No Clutch, no Team-Wins bonus for OROY/DROY.



\*\*7.4.4 Normalization \& Context Primitives\*\*



\- \*\*Rates:\*\* per-game x\_pg = x/GP, per-snap x\_ps = x/Snaps.

\- \*\*Within-position normalization:\*\*

&nbsp; - z(x) = (x − μ) / σ (position cohort)

&nbsp; - percentile p(x) ∈ \\\[0,1\\] (position cohort)

&nbsp; - \*\*Blended normalized metric:\*\* N(x) = 0.6·p(x) + 0.4·Φ(z(x)) (Φ→\\\[0,1\\])

\- \*\*Availability (A):\*\* A = min(1, GP/17)^0.5 (soft durability).

\- \*\*Strength of Schedule (S):\*\* 0.85-1.15 index from opponent W% + unit ranks faced.

\- \*\*Clutch (C):\*\* 0.95-1.05 index from 4Q/OT impact (WPA if tracked; else late-down proxies).

\- \*\*Explosive plays:\*\* Offense: gains ≥20y; Defense: TFL≥3, late/3rd-down sacks, turnovers.



\*\*7.4.5 Position Value Scores (PVS)\*\*



Each player gets a position-aware PVS (weights tunable).



\*\*QB (example composition)\*\*  

PVS\_QB = 0.30 N(EPA\_or\_QBR) + 0.15 N(YPA) + 0.15 N(TD − 0.8·INT) + 0.10 N(RushYD\_pg) + 0.05 N(RushTD) + 0.10 N(FirstDowns) − 0.10 N(SackRate)



\*\*RB / WR / TE\*\*



\- \*\*RB:\*\* rush yards, YPC, TD (rush+rec), receptions/rec yards, 1D, explosives, fumbles−.

\- \*\*WR/TE:\*\* targets, receptions, rec yards, TD, 1D, YAC (if tracked), drops/fumbles−, explosives.



\*\*Offensive Line\*\*  

Pressures−, sacks allowed−, penalties−, run-block wins, pass-block wins; fallback: team on/off deltas (sack rate, rush EPA).



\*\*Front-7 (DE/DT/LB)\*\*  

Sacks, pressures, QB hits, TFL, run stops, FF/FR, tackles, missed tackles−, (if tracked) pressure-win rate, high-leverage stops.



\*\*Secondary (CB/S)\*\*  

INT, PBUs, coverage efficiency (yds/cover snap− or passer rating allowed−), FF, blitz sacks, tackles, missed tackles−.



\*\*Specialists (K/P/Returner)\*\*  

K: distance-weighted FG%, XP%, 50+ makes, GW kicks.  

P: net avg, inside-20, touchbacks−, returnable rate−.  

Returner: return avg, TDs, ball security.



\*\*7.4.6 Candidate Scores (CS) by Award\*\*



Convert PVS to award CS with modest context multipliers. RankNorm(x) maps ranks to \\\[0,1\\].



\- \*\*MVP\*\*  

&nbsp;   CS\_MVP = 0.70·RankNorm(PVS) + 0.10·RankNorm(TeamWins) + 0.05·RankNorm(TeamSideEff) + 0.05·(S−1) + 0.03·(C−1) + 0.07·(A−1)

\- \*\*OPOY / DPOY\*\*  

&nbsp;   CS\_OPOY/DPOY = 0.85·RankNorm(PVS\_side) + 0.05·(S−1) + 0.05·(C−1) + 0.05·(A−1)

\- \*\*OROY / DROY (no Clutch/Team-Wins)\*\*  

&nbsp;   CS\_OROY/DROY = 0.92·RankNorm(PVS\_side) + 0.08·(A−1)

\- \*\*COTY\*\*  

&nbsp;   CS\_COTY = 0.35·RankNorm(Wins) + 0.25·RankNorm(Wins−ExpectedWins) + 0.15·RankNorm(Improvement\_yoy) + 0.10·RankNorm(S) + 0.10·RankNorm(−InjuryLostWAR) + 0.05·PlayoffByeBonus

\- \*\*GMOTY\*\*  

&nbsp;   CS\_GMOTY = 0.30·RankNorm(NetAcquisitionValue) + 0.25·RankNorm(RookieClassWAR) + 0.20·RankNorm(Wins−ExpectedWins) + 0.15·RankNorm(CapHealthIndex) + 0.10·RankNorm(DepthQualityIndex)



\*\*7.4.7 Pro Bowl (Per-Conference Starters)\*\*



\- \*\*Timing:\*\* After Week 18 freeze; announced with season awards. No game is played.

\- \*\*Lineups:\*\*  

&nbsp;   Offense (11): QB1, RB1, WR3, TE1, T2, G2, C1  

&nbsp;   Defense (11): DE2, DT2, LB3, CB2, S2  

&nbsp;   Special Teams (3): K1, P1, Returner1

\- \*\*Scoring (no SoS/Clutch):\*\* PB\_Score = 0.95·RankNorm(PVS\_pos) + 0.05·(A−1)

\- \*\*Selection:\*\* Filter by conference/position/eligibility → rank by PB\_Score → take top N per slot.

\- \*\*Tie-breakers:\*\* §7.4.12.



\*\*7.4.8 Super Bowl MVP (Single-Game)\*\*



\- \*\*Timing:\*\* Immediately after championship; winner must be from the winning team.

\- \*\*Inputs:\*\* Single-game PVS (same families as §7.4.5), \*\*Impact Plays\*\* (TDs, turnovers created, high-leverage sacks/gains), \*\*4Q/OT Clutch\*\*.

\- \*\*Scoring:\*\* CS\_SBMVP = 0.80·RankNorm(PVS\_game) + 0.10·ImpactPlays\_norm + 0.10·Clutch4QOT\_norm

\- \*\*Tie-breakers:\*\* §7.4.12 (game stats).



\*\*7.4.9 Weekly Awards Race (Top-5)\*\*



\- \*\*Cadence:\*\* After each week closes (1-18).

\- \*\*Process:\*\* Recompute season-to-date context → rebuild PVS → compute CS per award → persist Top-5 per award to SeasonAwardRace(week=n).

\- \*\*Pro Bowl preview:\*\* Persist per-conference starters snapshot weekly for UI.



\*\*7.4.10 Tie-Breakers (Global Order)\*\*



\- Higher \*\*raw PVS\*\* (unweighted)

\- Better \*\*last-4-games form\*\* index

\- Higher \*\*Availability (A)\*\*

\- Higher \*\*Team Wins\*\* (skip for OROY/DROY; not used for Pro Bowl)

\- \*\*Younger age\*\* (skip where all are rookies)

\- \*\*Seeded deterministic RNG\*\* (LEAGUE\_SEED + entity\_id)



\*\*7.4.11 Cadence \& Outputs\*\*



\- \*\*Weekly (1-18):\*\* Recompute → PVS → Top-5 per award; publish \*\*Pro Bowl preview\*\* starters per conference; snapshot persisted for UI cache.

\- \*\*Season close:\*\* Finalize all season awards + \*\*Pro Bowl rosters\*\*; write profile \*\*HonorBadges\*\*.

\- \*\*Post-championship:\*\* Compute/persist \*\*Super Bowl MVP\*\*; badge winner.



\*\*7.4.12 Data Model (Additions/Recap)\*\*



\- \*\*SeasonAwardRace:\*\* {award\_type, week, rank, entity\_type, entity\_id, team\_id, pos?, pvs, candidate\_score, context{A,S,C}, explain}

\- \*\*SeasonAwardWinner:\*\* {season, award\_type, winner\_id, runner\_up\_ids\\\[4\\], scores{winner,runners}, meta{ties}}

\- \*\*ProBowlSelection:\*\* {season, conference, position, player\_id, team\_id, pb\_score, rank\_in\_slot}

\- \*\*ProBowlSelectionPreview:\*\* {week, conference, position, player\_id, team\_id, pb\_score, rank\_in\_slot, is\_preview:true}

\- \*\*HonorBadge:\*\* {entity\_type, entity\_id, season, honor\_type, meta{conference?, position?, game\_id?}}

\- \*\*TeamSeasonMeta:\*\* {expected\_wins, sos\_index, injury\_lost\_war, cap\_health\_index, depth\_quality\_index, off\_eff\_rank?, def\_eff\_rank?}

\- \*\*GameImpactMetrics (SB MVP cache):\*\* {game\_id, player\_id, impact\_plays, clutch\_index, pvs\_game\_breakdown}



\*\*7.4.13 API Endpoints (for UI)\*\*



\- GET /awards/race/current → latest week Top-5 per award

\- GET /awards/race?week=INT → specific week snapshot

\- GET /awards/probowl/preview/current → per-conference starters preview

\- GET /awards/final → end-of-season winners + Pro Bowl starters

\- \*\*UI fallback:\*\* cache last good payload in localStorage to avoid blank widgets.



\*\*7.4.14 Calibration Knobs (awards\_config.json)\*\*



\- weights.pvs.{qb,rb,wr,te,ol,f7,db,k,p,ret}

\- multipliers.{sos,clutch,availability}

\- thresholds.{rookie\_gp\_min,snap\_min\_off,snap\_min\_def}

\- mvp.team\_success\_weight, etc.

\- stddev\_floors to stabilize early weeks

\- pro\_bowl.{pvs\_weight,availability\_weight} (default 0.95/0.05)



\*\*7.4.15 UI/UX Hooks\*\*



\- \*\*Dashboard (C1) \& Stats page\*\*

&nbsp; - \*\*Awards Race Carousel:\*\* Top-5 per award with mini stat-lines + 4-week CS spark trend.

&nbsp; - \*\*Pro Bowl Tab:\*\* AFC/NFC toggles, position tiles showing starters.

&nbsp; - \*\*Candidate Modal:\*\* PVS breakdown, context multipliers, last-4 form chart.

&nbsp; - \*\*Profile Badges:\*\* e.g., "MVP (2030)", "Pro Bowl (AFC, WR, 2030)", "SB MVP (2030)".

\- \*\*No-API Fallbacks:\*\* Render last snapshot or seeded demo.



\*\*7.4.16 Pseudocode (Deterministic)\*\*



on\_week\_close(week):



freeze\_stats(week)



ctx = build\_league\_context(season\_to\_date)



for p in eligible\_players(season\_to\_date):



pvs = compute\_pvs(p, ctx)



A,S,C = availability(p), sos(p.team), clutch(p) or 1.0



for award in AWARDS\_REGULAR:



cs = score\_award(award, pvs, A,S,C, team\_meta, player\_meta)



push\_race\_snapshot(award, week, p, pvs, cs, A,S,C)



rank\_and\_persist\_top5\_per\_award(week)



persist\_probowl\_preview(week) # per-conference slots by PB\_Score



on\_regular\_season\_close():



run on\_week\_close(18) if not yet



finalize\_awards\_winners() # MVP, OPOY, DPOY, OROY, DROY, COTY, GMOTY



select\_and\_persist\_probowl() # final per-conference starters



write\_honor\_badges()



on\_championship\_final():



compute\_sb\_mvp\_from\_game()



write\_honor\_badge(sb\_mvp)



\*\*7.4.17 Tests (pytest - required)\*\*



\- \*\*Eligibility:\*\* rookies/non-rookies filtered; floors enforced (edge cases at threshold).

\- \*\*Monotonicity:\*\* boosting a core stat (e.g., sacks) increases PVS and CS with context held constant.

\- \*\*ROY policy:\*\* OROY/DROY exclude Clutch \& Team-Wins; assert config and computed CS terms.

\- \*\*SoS sanity:\*\* identical lines on harder schedule yield slightly higher CS (except ROY/Pro Bowl).

\- \*\*Pro Bowl quotas:\*\* exactly 25 per conference (11 O + 11 D + 3 ST).

\- \*\*Tie-breakers:\*\* synthetic equals resolve in documented order.

\- \*\*Idempotency:\*\* re-running same week/close yields identical results.

\- \*\*Badges:\*\* winners/Pro Bowlers receive correct HonorBadge entries.



\*\*7.4.18 Phase-2 Notes\*\*



\- Weekly awards (Off/Def/Rookie of the Week).

\- Optional conference-specific MVP/OPOY/DPOY variants (toggle).

\- Replace proxies with advanced tracking (EPA, success rate, YPRR, coverage charts) when available.

\- Optional team cap for Pro Bowl selections (e.g., ≤4 per team).



\## 7.5. Player \& Coach Cards



This section defines the unified detail view for players and coaches, available as both a full page and a modal overlay. It includes bio, ratings, comprehensive stats (season, playoffs, career), awards, contract details, and acquisition history.



\- \*\*Layout:\*\* A multi-panel design featuring a sticky header with controls, a bio/contract strip, a ratings rail, and tabbed sections for stats and achievements.

\- \*\*Stats:\*\* All statistical tables for players (Regular Season, Playoffs, Career) must include \*\*Games Played (G)\*\* and \*\*Games Started (GS)\*\*.

\- \*\*Actions:\*\* The card includes controls to initiate \*\*Contract Negotiation\*\* or \*\*Release Player\*\* / \*\*Fire Coach\*\*.

\- \*\*Release Logic (MVP):\*\* In the MVP's simple contract model, releasing a player immediately frees their remaining current-year salary. No dead cap money is calculated.



\## 7.6 Stats Catalog



Defines all player/team statistics tracked by the simulation, how they are computed from PBP events, and how they aggregate per game, season, playoffs, and career. All fields below are MVP.



\*\*7.6.1 Player Stat Catalog\*\*



\*\*Scopes:\*\* Game, Season (regular \& playoffs kept separately), Playoffs, Career (both split and combined views).



\*\*Universal Meta \& Usage\*\*



\- gp, gs (games played/started)

\- snaps\_off, snaps\_def, snaps\_st (offense/defense/special-teams snaps)



\*\*Passing (any passer)\*\*



\- Raw: pass\_att, pass\_cmp, pass\_yds, pass\_td, pass\_int, sacks\_taken, sack\_yds (negative), fumbles, fumbles\_lost

\- Longs: pass\_long

\- Derived: pass\_rating (see 7.6.4), ay/a = (pass\_yds + 20\\\*pass\_td − 45\\\*pass\_int − sack\_yds)/max(1, pass\_att)



\*\*Rushing (incl. QB scrambles)\*\*



\- Raw: rush\_att, rush\_yds, rush\_td, rush\_long

\- Advanced: broken\_tackles, yac\_contact (yards after contact)

\- Derived: rush\_ypc = rush\_yds / max(1, rush\_att)



\*\*Receiving\*\*



\- Raw: rec\_tgt, rec\_rec, rec\_yds, rec\_td, rec\_long, yac, drops

\- Coverage-opponent links (see Coverage below) are recorded on the defender, not here

\- Derived: rec\_ypr = rec\_yds / max(1, rec\_rec)



\*\*Defense - Tackling/Backfield\*\*



\- tackle\_solo, tackle\_asst, tfl, sacks, sack\_yds

\- Pressure family: pressures, hurries, qb\_hits



\*\*Defense - Coverage/Turnovers\*\*



\- Ball disruption: pbu, ints, ff, fr, def\_td

\- Coverage responsibility (per targeted defender):  

&nbsp;   targets\_against, receptions\_allowed, yards\_allowed, tds\_allowed, penalties\_coverage (count), penalty\_yds\_coverage

\- Convenience: pd\_total = pbu + ints



\*\*Offensive Line - Pass Pro (responsibility based)\*\*



\- pressures\_allowed, hits\_allowed, sacks\_allowed, penalties\_ol (count), penalty\_yds\_ol



\*\*Special Teams - Kicking (PK)\*\*



\- fgm, fga, fg\_pct (derived), xp\_made, xp\_att, fg\_long

\- Buckets: fg\_0\_39\_m/a, fg\_40\_49\_m/a, fg\_50p\_m/a



\*\*Special Teams - Punting\*\*



\- punts, punt\_long, punt\_gross\_avg (derived)

\- Advanced: punts\_in20, punt\_tb (touchbacks), punt\_net\_avg (derived)



\*\*Special Teams - Returns\*\*



\- Kick: kr\_att, kr\_yds, kr\_td, kr\_long, kr\_avg (derived)

\- Punt: pr\_att, pr\_yds, pr\_td, pr\_long, pr\_avg (derived)

\- Advanced: fair\_catches\_forced (credit to punter), return\_yac (return yards after first contact)



\*\*Penalties (per player)\*\*



\- penalties\_total, penalty\_yds\_total  

&nbsp;   \_(Sub-categories like coverage/OL are still summarized separately above for analytics.)\_



\*\*Per-Player Efficiency (requires EP model)\*\*



\- pass\_epa, rush\_epa, rec\_epa (sum of EPA deltas on plays where the player is the passer/rusher/targeted receiver)

\- success\_rate\_pass, success\_rate\_rush, success\_rate\_rec (share of plays with EPA > 0; see 7.6.4)



\*\*Career mirrors\*\*



\- career\_\\\* versions of all cumulative counters above.



\*\*7.6.2 Team Stat Catalog (MVP)\*\*



\*\*Scoring \& Record\*\*



\- points\_for, points\_against, point\_diff (derived), record, streak, home\_record, away\_record



\*\*Team Offense\*\*



\- Passing: team\_pass\_att, team\_pass\_cmp, team\_pass\_yds, team\_pass\_td, team\_pass\_int, team\_sacks\_taken, team\_sack\_yds

\- Rushing: team\_rush\_att, team\_rush\_yds, team\_rush\_td, team\_rush\_ypc (derived)

\- Explosives: team\_plays\_20p, team\_plays\_40p

\- Penalties: team\_penalties, team\_penalty\_yds



\*\*Team Defense\*\*



\- Front/pressure: team\_tackles, team\_tfl, team\_sacks, team\_sack\_yds, team\_qb\_hits, team\_pressures, team\_hurries

\- Coverage/TOs: team\_ints, team\_pbu, team\_ff, team\_fr, team\_def\_td



\*\*Situational \& Efficiency\*\*



\- 3rd: third\_down\_made, third\_down\_att, third\_down\_pct

\- 4th: fourth\_down\_made, fourth\_down\_att, fourth\_down\_pct

\- Red Zone: redzone\_td\_made, redzone\_att, redzone\_td\_pct (TD only)

\- Turnovers: turnovers\_committed, turnovers\_gained, turnover\_margin



\*\*Special Teams\*\*



\- Aggregates mirroring player PK/Punt/Return fields; includes team punt\_net\_avg



\*\*Per-Team Efficiency\*\*



\- team\_epa\_off, team\_epa\_def, team\_epa\_st (sums), plus team\_success\_rate\_off, team\_success\_rate\_def



\*\*Power Ranking Inputs\*\*



\- point\_diff, last-N form, team\_epa\_off/def, schedule strength stub (see Schedule module)



\*\*7.6.3 Event → Stat Attribution Rules (Authoritative)\*\*



\*\*General\*\*



\- Every counter comes from a PBP event with deterministic seeds. Game logs are the authority; season/career are rebuildable roll-ups.



\*\*Sacks \& Sack Yards\*\*



\- Passer tackled behind LOS on a called pass:  

&nbsp;   Offense: sacks\_taken (+1), sack\_yds (−N), team passing yards reduced by N.  

&nbsp;   Defense: credit sacks to tackler(s), sack\_yds (N). Half-sacks split as 0.5.



\*\*Scrambles\*\*



\- Called pass that becomes QB run → rush\_att/rush\_yds to QB; no target or reception.



\*\*Targets, Catches, Drops, YAC\*\*



\- On a forward pass to a receiver: rec\_tgt +1.  

&nbsp;   If caught: rec\_rec, rec\_yds, yac (engine provides YAC).  

&nbsp;   If clean drop (engine flag): drops +1.



\*\*Fumbles/Turnovers\*\*



\- Ball carrier fumbles +1 on drop; if defense recovers: fumbles\_lost +1, defender fr +1.

\- Interception: defender ints +1; passer pass\_int +1.



\*\*Defensive TD\*\*



\- Any defensive return for TD → scorer def\_td +1.



\*\*Pressure Family\*\*



\- pressures: each credited defender influencing QB's time/decision per engine flag.

\- hurries: subset where throw is early/altered (distinct count).

\- qb\_hits: legal post-throw hit or as part of sack (primary tackler).

\- Multiple defenders may receive pressure/hurry credit on the same play; qb\_hits is single-credit per instance.



\*\*Coverage Responsibility\*\*



\- On targeted pass, engine assigns primary defender (and optional help).  

&nbsp;   Primary defender gets: targets\_against +1; if completed: receptions\_allowed +1 and yards\_allowed +Y; if TD: tds\_allowed +1.



\*\*OL Pass-Pro Responsibility\*\*



\- Engine assigns blocker(s) responsible when pressure/hit/sack comes via their gap: increment pressures\_allowed, hits\_allowed, sacks\_allowed.



\*\*Special Teams\*\*



\- Punt: record gross punt distance; net = gross − return yards − TB/return penalties.

\- punts\_in20 on dead/return-end inside 20; punt\_tb on touchback.

\- fair\_catches\_forced credited to punter on forced fair catches.



\*\*Penalties\*\*



\- Player: increment penalties\_total, penalty\_yds\_total; sub-buckets (penalties\_ol, penalty\_yds\_ol, penalties\_coverage, etc.) increment as applicable.

\- Team: team\_penalties, team\_penalty\_yds mirror the sum of assessed penalties.



\*\*7.6.4 Derived Metrics \& Formulas\*\*



\*\*Passer Rating (NFL)\*\*  

a=((cmp/att)-0.3)\\\*5, b=((yds/att)-3)\\\*0.25, c=(td/att)\\\*20, d=2.375-((int/att)\\\*25); clamp each to \\\[0,2.375\\].  

pass\_rating=((a+b+c+d)/6)\\\*100; if att==0 → 0.0.



\*\*Yards-Per Metrics\*\*  

rush\_ypc = rush\_yds / max(1, rush\_att)  

rec\_ypr = rec\_yds / max(1, rec\_rec)  

punt\_gross\_avg = gross\_punt\_yds / max(1, punts)  

punt\_net\_avg = net\_punt\_yds / max(1, punts)  

kr\_avg = kr\_yds / max(1, kr\_att)  

pr\_avg = pr\_yds / max(1, pr\_att)  

fg\_pct = fgm / max(1, fga)  

third\_down\_pct = third\_down\_made / max(1, third\_down\_att) (same for 4th, RZ TD%)



\*\*Explosives\*\*  

team\_plays\_20p/40p = count of plays with yards\_gained ≥ 20/40.



\*\*EPA \& Success Rate (engine EP model)\*\*  

Per play: epa = EP\_after − EP\_before.  

Per entity (player/team): sum epa over qualifying plays.  

success = 1 if epa > 0 else 0; success\_rate = successes / max(1, plays).



\*\*Convenience\*\*  

pd\_total = pbu + ints  

point\_diff = points\_for − points\_against



\*\*7.6.5 Aggregation Windows \& Ledgers\*\*



\- \*\*Game logs\*\*: one row per player per game per team; one row per team per game.

\- \*\*Season\*\*: regular and playoffs are separate ledgers.

\- \*\*Career\*\*: cumulative; show split \& combined.

\- Rebuilds: season/career can be recomputed from game logs (idempotent).



\*\*7.6.6 Data Model (Tables \& Rebuild Policy)\*\*



\- player\_game\_stats, team\_game\_stats (authoritative from PBP)

\- player\_season\_stats, team\_season\_stats (materialized views or roll-up tables)

\- player\_career\_stats (roll-up)

\- All counters default 0; rate stats computed with max(1, denom) guards.



\*\*7.6.7 Consistency Rules \& Invariants\*\*



\- \*\*Conservation per game\*\*:

&nbsp; - Team pass yards = player pass yards − sack yards (NFL convention)

&nbsp; - Team rush yards = sum player rush yards

&nbsp; - Points, turnovers, sacks: team totals equal sum of players (respecting half-sacks)

\- \*\*No double-spend\*\*: same penalty cannot credit two players unless flagged as offsetting.

\- \*\*Pressure family\*\*: multi-credit allowed (pressures/hurries) by design; qb\_hit is distinct.

\- Team totals mirror sums of credited players for penalties assessed; offsetting/declined penalties do not alter player or team counters



\*\*7.6.8 Engine Flags Required (so PBP can emit all MVP stats)\*\*



To produce the MVP fields, each PBP play must include:



\- play\_type (pass/run/sack/scramble/kick/punt/return/penalty/turnover)

\- responsibilities: primary\_coverage\_defender, help\_defenders\\\[\\], ol\_blockers\_responsible\\\[\\] (when applicable)

\- pressure\_flags\\\[\\] per defender (pressure, hurry, qb\_hit)

\- yac, yards\_after\_contact (as applicable)

\- broken\_tackles (count)

\- penalty object (fouling player id, yards, category)

\- Special-teams: punt\_gross, return\_yards, fair\_catch, touchback, inside\_20

\- EPA hooks: EP\_before, EP\_after



\*\*7.6.9 API \& UI Contracts\*\*



\*\*Player Stats\*\*  

GET /api/player/{id}/stats?season=YYYY\&scope=\\\[regular|playoffs|career\\]  

Returns meta, usage, offense, defense, OL, ST, penalties, EPA/SR, deriveds.



\*\*Team Stats\*\*  

GET /api/team/{id}/stats?season=YYYY\&scope=\\\[regular|playoffs\\]  

Returns scoring/record, offense/defense/ST, situational, EPA/SR.



\*\*UI\*\*



\- Player Card tabs: Season | Playoffs | Career, with gp, gs, snaps\_\\\* pinned left.

\- Roster grid toggle: \*\*Attributes | Stats\*\*, horizontal scroll with sticky name; sortable columns.



\*\*7.6.10 Dependencies\*\*



\- \*\*Awards (7.4):\*\* consumes pressures/hits/PBUs/sacks/TDs/efficiency.

\- \*\*Power Ranking:\*\* consumes point\_diff, recent form, team EPA.

\- \*\*Injury/Progression:\*\* consumes snaps\_\\\*, usage, and performance totals.

\- \*\*Score Fidelity \& Box/PBP:\*\* rely on conservation and attribution rules herein.



\*\*7.6.11 Assumptions\*\*



\- Coverage and OL responsibilities are assigned by the engine at play time; we do not infer post-hoc from outcomes.

\- EPA model is included in MVP at a basic level (down/distance/field/clock); can be swapped later without schema changes.

\- Penalty yards apply once at the team level and to the fouling player; offsetting/multiple fouls follow league rules simulated elsewhere.



\*\*7.6.12 PBP Event Schema (authoritative, minimal)\*\*



Add this verbatim so the engine, DB writer, and tests share one contract.



{



"game\_id": "YYYYWWTT-TEAM@TEAM",



"season": 2025,



"week": 7,



"phase": "regular", // regular | playoffs



"drive\_id": "gX-dY",



"play\_id": "gX-dY-pZ",



"clock": { "quarter": 2, "mm": 07, "ss": 14 },



"score\_before": { "home": 10, "away": 7 },



"possession\_team\_id": "TEAM\_A",



"defense\_team\_id": "TEAM\_B",



"yardline\_start": { "side": "TEAM\_A", "yard": 43 }, // own 43



"down": 2, "to\_go": 6,



"play\_type": "pass", // pass | run | sack | scramble | punt | field\_goal | kickoff | penalty\_only | spike | kneel | two\_pt



"gain\_yards": 12, // NET yards gained by offense (sign can be negative)



"ep\_before": 1.63, "ep\_after": 3.12, // for EPA



"fumble": { "occurred": false, "lost": false, "caused\_by": null, "recovered\_by": null },



"pass": {



"passer\_id": "P\_QB\_A",



"target\_id": "P\_WR\_A",



"complete": true,



"air\_yards": 9,



"yac": 3,



"intercepted\_by": null



},



"run": {



"rusher\_id": null,



"is\_scramble": false,



"yards\_after\_contact": null,



"broken\_tackles": 0



},



"sack": {



"sacked\_passer\_id": null,



"sack\_yards": null,



"tacklers": \\\[\\] // e.g., \\\[{"id":"P\_EDGE\_B","fraction":1.0}\\]



},



"coverage": {



"primary\_defender\_id": "P\_CB\_B",



"helpers": \\\["P\_S\_B"\\]



},



"pressure": {



"pressures": \\\["P\_EDGE\_B","P\_DT\_B"\\], // defenders credited with pressure



"hurries": \\\["P\_EDGE\_B"\\],



"qb\_hits": \\\["P\_EDGE\_B"\\] // single credit per hit instance



},



"ol\_responsibility": {



"pressures\_allowed": \\\["P\_LT\_A"\\],



"hits\_allowed": \\\["P\_LT\_A"\\],



"sacks\_allowed": \\\[\\]



},



"penalties": \\\[



{



"fouling\_player\_id": "P\_CB\_B",



"team\_id": "TEAM\_B",



"category": "DEF\_HOLD", // see enum in 7.6.13



"yards": 5,



"enforced": true,



"declined": false,



"offsetting": false,



"on\_play": true // true if combined with play, false if pre-snap/dead-ball



}



\\],



"kick": {



"kicker\_id": null,



"result": null, // good | missed | blocked | tb (kickoff touchback)



"distance": null



},



"punt": {



"punter\_id": null,



"gross\_yards": null,



"return\_yards": null,



"touchback": null,



"inside\_20": null,



"fair\_catch\_forced": false,



"returner\_id": null



},



"return": {



"type": null, // kickoff | punt | int | fumble



"returner\_id": null,



"yards": null,



"td": false,



"yac\_after\_contact": null



},



"scoring": {



"td": false,



"safety": false,



"xp": null, // made | missed | blocked | null



"two\_pt\_good": null, // true | false | null



"fg": null // made | missed | blocked | null



},



"score\_after": { "home": 10, "away": 14 }



}



\*\*7.6.13 Enumerations (no guesswork)\*\*



Add these so we never invent strings in code.



\- \*\*phase\*\*: regular, playoffs

\- \*\*play\_type\*\*: pass, run, sack, scramble, punt, field\_goal, kickoff, penalty\_only, spike, kneel, two\_pt

\- \*\*penalty.category\*\* (starter set):

&nbsp; - Offense: OFF\_HOLD, FALSE\_START, ILLEGAL\_FORMATION, OFF\_PI, BLOCK\_BACK, CHOP\_BLOCK, DELAY\_OFFENSE

&nbsp; - Defense: DEF\_HOLD, DEF\_PI, ILLEGAL\_CONTACT, ENCROACH, OFFSIDE, RTP, RTK (roughing kicker), 12\_ON\_FIELD, DELAY\_DEFENSE

&nbsp; - ST generic: KICK\_CATCH\_INT, ILLEGAL\_BLOCK\_ST, FAIR\_CATCH\_INT

\- \*\*kick.result / scoring fields\*\*: made, missed, blocked, tb

\- \*\*return.type\*\*: kickoff, punt, int, fumble



\*\*7.6.14 Data Types \& Units (storage-level)\*\*



\- All \\\*\\\_yds fields: \*\*integer\*\* yards (can be negative on sacks/some penalties).

\- Rates/averages/EP/EPA: \*\*FLOAT(53)\*\* (double).

\- Counts: \*\*INT\*\* (non-negative; half-sacks stored as \*\*DECIMAL(3,1)\*\* or integer halves \_2\_, pick one - recommend \*\*DECIMAL(3,1)\*\*).

\- IDs: game\_id, play\_id, player\_id, team\_id: \*\*TEXT/VARCHAR(36)\*\*.

\- Time: quarter \*\*TINYINT\*\*, mm/ss \*\*TINYINT\*\* (0-59).

\- Enums: stored as \*\*TEXT\*\* constrained to the lists above (or small int codes if you prefer).



\*\*7.6.15 Indexing \& Keys (performance \& rebuilds)\*\*



\- Primary keys:

&nbsp; - player\_game\_stats: (game\_id, team\_id, player\_id)

&nbsp; - team\_game\_stats: (game\_id, team\_id)

\- High-value indexes:

&nbsp; - idx\_play\_by\_game on PBP table: (game\_id, drive\_id, play\_id)

&nbsp; - idx\_player\_season on season tables: (season, team\_id, player\_id)

&nbsp; - idx\_coverage\_targeted on coverage table: (season, player\_id, targets\_against DESC)

&nbsp; - idx\_ol\_resp on OL responsibility table: (season, player\_id, sacks\_allowed DESC)



\*\*7.6.16 Roll-Up Algorithm (deterministic)\*\*



\- \*\*Input\*\*: ordered PBP for game (sorted by (drive\_id, play\_id)).

\- \*\*Process\*\*: fold over plays, apply 7.6.3 attribution, mutate per-player and per-team accumulators.

\- \*\*Output\*\*: write player\_game\_stats/team\_game\_stats.

\- \*\*Season/Playoffs/Career\*\*: aggregate by (season, scope) and sum counters; recompute deriveds with max(1, denom) guards.

\- \*\*Idempotency\*\*: delete-and-rebuild targets within a transaction; checksum game rows to skip unchanged games.



\*\*7.6.17 Invariants \& Validation Tests (must pass)\*\*



\- Team totals == sum of player totals per game for: rush\_yds, pass\_cmp/att, pass\_td/int, sacks (respecting halves), turnovers, points.

\- Sack yards are \*\*subtracted from team passing yards\*\* once (no double hit).

\- Attempt/denominator alignment: fg\_pct uses team fga == sum(player fga).

\- EPA consistency: Σ team\_epa\_off + Σ team\_epa\_def + Σ team\_epa\_st ≈ observed point delta over the season (sanity check, tolerance ±5%).

\- Coverage/OL responsibilities only increment when engine emitted responsibility arrays (no silent inference).



\*\*7.6.18 Minimal DTO Shapes (exact fields)\*\*



\*\*PlayerStatsDTO\*\*



{



"player\_id": "P\_123",



"season": 2025,



"scope": "regular",



"gp": 16, "gs": 16,



"snaps\_off": 980, "snaps\_def": 0, "snaps\_st": 42,



"passing": { "att": 520, "cmp": 340, "yds": 3988, "td": 29, "int": 11, "sacks\_taken": 36, "sack\_yds": -234, "rating": 95.4, "aya": 7.5, "long": 68, "fumbles": 6, "fumbles\_lost": 3 },



"rushing": { "att": 84, "yds": 382, "td": 3, "long": 28, "ypc": 4.5, "broken\_tackles": 6, "yac\_contact": 112 },



"receiving": { "tgt": 0, "rec": 0, "yds": 0, "td": 0, "long": 0, "ypr": 0.0, "yac": 0, "drops": 0 },



"defense": { "solo": 0, "asst": 0, "tfl": 0, "sacks": 0.0, "sack\_yds": 0, "pressures": 0, "hurries": 0, "qb\_hits": 0, "pbu": 0, "ints": 0, "ff": 0, "fr": 0, "def\_td": 0, "pd\_total": 0 },



"coverage": { "targets\_against": 0, "receptions\_allowed": 0, "yards\_allowed": 0, "tds\_allowed": 0, "penalties\_coverage": 0, "penalty\_yds\_coverage": 0 },



"ol": { "pressures\_allowed": 0, "hits\_allowed": 0, "sacks\_allowed": 0, "penalties\_ol": 0, "penalty\_yds\_ol": 0 },



"kicking": { "fgm": 0, "fga": 0, "fg\_pct": 0.0, "xp\_made": 0, "xp\_att": 0, "fg\_long": 0, "buckets": {"0\_39":{"m":0,"a":0},"40\_49":{"m":0,"a":0},"50p":{"m":0,"a":0}} },



"punting": { "punts": 0, "punt\_long": 0, "punt\_gross\_avg": 0.0, "punts\_in20": 0, "punt\_tb": 0, "punt\_net\_avg": 0.0 },



"returns": { "kr\_att": 0, "kr\_yds": 0, "kr\_td": 0, "kr\_long": 0, "kr\_avg": 0.0, "pr\_att": 0, "pr\_yds": 0, "pr\_td": 0, "pr\_long": 0, "pr\_avg": 0.0, "return\_yac": 0, "fair\_catches\_forced": 0 },



"penalties": { "count": 0, "yards": 0 },



"efficiency": { "pass\_epa": 0.0, "rush\_epa": 0.0, "rec\_epa": 0.0, "success\_rate\_pass": 0.0, "success\_rate\_rush": 0.0, "success\_rate\_rec": 0.0 }



}



\*\*TeamStatsDTO\*\* (similar structure; includes situational %s, turnovers, red zone, EPA blocks).



\*\*TeamStatsDTO (MVP shape)\*\*



{



"team\_id": "TEAM\_A",



"season": 2025,



"scope": "regular", // regular | playoffs



"record": { "wins": 11, "losses": 6, "ties": 0, "streak": "W3",



"home": {"w":6,"l":3}, "away": {"w":5,"l":3} },



"scoring": { "points\_for": 413, "points\_against": 372, "point\_diff": 41 },



"offense": {



"pass": { "att": 560, "cmp": 374, "yds": 4275, "td": 30, "int": 13,



"sacks\_taken": 38, "sack\_yds": -247 },



"rush": { "att": 425, "yds": 1894, "td": 16, "ypc": 4.5 },



"explosives": { "plays\_20p": 62, "plays\_40p": 9 },



"penalties": { "count": 88, "yards": 742 }



},



"defense": {



"front": { "tackles": 977, "tfl": 78, "sacks": 44.5, "sack\_yds": 283,



"qb\_hits": 94, "pressures": 211, "hurries": 129 },



"coverage": { "ints": 14, "pbu": 67, "ff": 10, "fr": 8, "def\_td": 3 }



},



"situational": {



"third": { "made": 92, "att": 210, "pct": 0.438 },



"fourth": { "made": 12, "att": 22, "pct": 0.545 },



"redzone": { "td\_made": 41, "att": 66, "td\_pct": 0.621 },



"turnovers": { "committed": 24, "gained": 29, "margin": 5 }



},



"special\_teams": {



"kicking": { "fgm": 28, "fga": 33, "fg\_pct": 0.848, "xp\_made": 41, "xp\_att": 43, "fg\_long": 55 },



"punting": { "punts": 58, "punt\_long": 71, "punt\_gross\_avg": 46.1,



"punts\_in20": 23, "punt\_tb": 7, "punt\_net\_avg": 41.3 },



"returns": { "kr\_att": 29, "kr\_yds": 748, "kr\_td": 1, "kr\_long": 102, "kr\_avg": 25.8,



"pr\_att": 34, "pr\_yds": 329, "pr\_td": 0, "pr\_long": 38, "pr\_avg": 9.7 }



},



"efficiency": {



"team\_epa\_off": 63.4, "team\_epa\_def": -28.9, "team\_epa\_st": 3.1,



"team\_success\_rate\_off": 0.471, "team\_success\_rate\_def": 0.447



}



}



Notes: rate stats use max(1, denom) guards as in §7.6.4; counts default to 0.



\*\*7.6.19 Tackle \& Half-Sack Credit Policy\*\*



\- \*\*Solo vs Assist:\*\* A tackle is solo when exactly one defender is credited; otherwise each additional credited defender on a stop increments tackle\_asst by 1 (no fractional assists).

\- \*\*Half-Sacks:\*\* When two defenders share a sack, each gets sacks += 0.5. If more than two are credited by the engine, divide 1.0 evenly to the credited group, rounded to the nearest 0.5 for storage.

\- \*\*TFL:\*\* Any solo/assist tackle with yards gained < 0 on a designed run/receiver carry increments tfl for each credited tackler (multi-credit allowed).



\*\*7.6.20 Two-Point, Spike, Kneel Accounting\*\*



\- \*\*Two-Point Try:\*\* add team fields two\_pt\_att, two\_pt\_good; on success, add points\_for += 2. Player attribution: passer/rusher/receiver gets standard credit (e.g., pass\_td\_2pt is \*\*not\*\* kept; the points are in team scoring only).

\- \*\*Spike:\*\* record a pass\_att to the QB (incomplete) with spike=true (flag only; excludes from AYA/EPA if you prefer later).

\- \*\*Kneel:\*\* counts as a rushing attempt and negative rush yards for QB; excluded from success rate by rule (engine flag kneel=true).



\*\*7.6.21 Search/Leaders API Contract (indexes implied in 7.6.15)\*\*



\- \*\*Leaders:\*\* GET /api/stats/leaders?season=YYYY\&scope=regular\&stat= sacks | pass\_yds | rec\_yds | rush\_yds | ... \&pos=ALL|QB|RB|WR|TE|DL|LB|DB\&limit=50  

&nbsp;   Returns: sorted list with player meta and stat value (server-side sort).

\- \*\*Search:\*\* GET /api/stats/search?season=YYYY\&filters=JSON where filters supports operators: gte/lte/eq/in.  

&nbsp;   Example: {"pos":\\\["EDGE","DL"\\],"sacks":{"gte":10},"pressures":{"gte":40}}.

\- \*\*Full-text (optional):\*\* q param matches player name/team short code; numeric filters still enforced.



\*\*7.6.22 Award/PR Derived Inputs (exact names)\*\*



To avoid "what field name was that?" during awards/PR coding:



\- \*\*Awards\*\* consume: pressures, qb\_hits, pbu, ints, tfl, sacks, rush\_yds, rec\_yds, pass\_yds, total\_td (sum: rush+rec+def; exclude 2-pt), success\_rate\_\\\*, pass\_rating, fg\_pct, punt\_net\_avg.

\- \*\*Coach/GM awards\*\* also consume: points\_for, points\_against, point\_diff, record, injury\_burden (from injury module), and wins\_delta (vs preseason baseline; computed outside 7.6).

\- \*\*Power Ranking\*\* consumes: point\_diff, team\_epa\_off, team\_epa\_def, team\_epa\_st, and last-N form (computed from team\_game\_stats).

\- Power Ranking recalculates \*\*weekly on Advance Week\*\* using the same deterministic seed window as standings.



\*\*Assumption call-outs (keeps coding friction-free)\*\*



\- \*\*EPA model\*\*: included at a basic level (down/distance/yardline/clock); exact coefficients live in the Score Fidelity/Engine section, not here. Our fields just store results.

\- \*\*Coverage/OL responsibility\*\*: always engine-assigned at play time; we never infer post-hoc.

\- \*\*Penalties taxonomy\*\*: starter set is enough for MVP stats. If the penalties module expands, 7.6.13 grows but stats schema is unchanged.

\- \*\*Schedule strength/PR injury adj.\*\*: consumed by PR/Awards but computed elsewhere; 7.6 just exposes required raw stats.



7.6.23 Team Meta Indices (CHI, DQI, iWAR)



Purpose  

Provide numeric team-level context for Awards, Power Ranking, and UI commentary.



Cap Health Index (CHI, 0-1)  

CHI = 0.5 \\\* clamp01(cap\_space / league\_cap)  

  + 0.3 \\\* (1 − clamp01(weighted\_avg\_years\_remaining / 5))  

  + 0.2 \\\* clamp01(starter\_value\_ratio)  

Notes:



\- weighted\_avg\_years\_remaining = contract years weighted by starter snap share.

\- starter\_value\_ratio = fraction of starters whose AAV is below the league-median AAV for their position (snap-weighted).

\- Cadence: recompute on Advance Week.



Depth Quality Index (DQI, 0-1)  

DQI = clamp01( Σ\_pos \\\[ w\_pos \\\* avg(backup\_OVR\_pos) / 90 \\] / Σ\_pos w\_pos )  

Notes:



\- Scarcity weights (MVP): QB=3.0, LT=2.0, CB=2.0, EDGE=2.0, iDL=1.5, WR=1.5, S=1.5, LB=1.2, RB=1.0, TE=1.0, IOL=1.0, K/P=0.5.

\- Backups = non-starters (depth slots 2-3). Cap each backup OVR contribution at 90.



Injury Lost WAR (iWAR, ≥ 0)  

For each injured starter:  

replacement\_delta = max(0, starter\_OVR − replacement\_OVR) / 10.0  

snap\_penalty = replacement\_delta \\\* snaps\_missed\_this\_week  

iWAR\_week = Σ snap\_penalty; iWAR\_season = Σ iWAR\_week across weeks  

Notes:



\- Replacement = "next up" per depth chart at time of injury.

\- Used for Coach-of-the-Year relief and broadcast notes.



7.6.24 Stats Search - UX and Validation Rules



Server Behavior



\- Pagination: limit default 50, max 200; offset default 0.

\- Sorting: default per endpoint (e.g., leaders by stat desc); supports sort=field and order=asc|desc.

\- Validation:

&nbsp; - Reject unknown fields with 400 and include fields\_supported list.

&nbsp; - Reject mixed units (e.g., percentage operator on integer field).

&nbsp; - Clamp numeric ranges to field bounds (e.g., sacks ≥ 0).

&nbsp; - Empty results return an empty array with meta.total = 0.



UI Behavior



\- Empty state: "No results. Adjust filters or clear search."

\- Loading: row skeletons in the results pane.

\- Saved presets (examples):

&nbsp; - EDGE/DL: sacks ≥ 10 AND pressures ≥ 40

&nbsp; - WR: rec\_yds ≥ 1000 AND rec\_td ≥ 8

\- Index note: "Search is optimized for season and career aggregates; play-level queries are not supported."



Standard Error Envelope  

{ "error": { "code": "\&lt;UPPER\_SNAKE\&gt;", "message": "Human-readable message", "fields\_supported": \\\[...\\] } }



\## 7.7 Player \& Coach Attribute Catalog



\*\*Scope keys: \_(MVP)\_ = required now; \_(Optional)\_ = flavor/UX only.  

Policy: All ratings below are active in MVP and may be referenced by OVR and the sim. If a rating is not yet heavily used, treat its weight as near-zero until tuning ramps up.\*\*



\*\*7.7.1 Player Attributes\*\*



\*\*7.7.1.1 Identity \& Contract\*\*



\- \*\*player\_id (int), team\_id (int)\*\*

\- \*\*first\_name, last\_name (str)\*\*

\- \*\*position (enum: QB, RB, WR, TE, OL, DL, LB, CB, S, K, P)\*\*

\- \*\*age (int, 18-55)\*\*

\- \*\*contract\_salary\_aav (int, \\$/yr), contract\_years (int)\*\*



\*\*7.7.1.2 Core Ratings (0-99 unless noted)\*\*



\- \*\*Physical: speed (SPD), acceleration (ACC), agility (AGI), strength (STR), jumping (JMP), stamina (STA)\*\*

\- \*\*Skill: throw\_power (THP), throw\_accuracy (THA), catching (CTH), tackling (TKL)\*\*

\- \*\*Mental: awareness (AWR)\*\*

\- \*\*Development/Health propensity: potential (POT), injury\_proneness (INJ)\*\*

\- \*\*Psych: morale (MOR)\*\*

\- \*\*Discipline: penalty\_tendency (PEN) \_(lower = fewer penalties; used for holds/DPI/offside, countered by coach discipline)\_\*\*



\*\*7.7.1.3 Position-Specific Ratings (All active in MVP; 0-99)\*\*



\*\*QB - throw\_accuracy\_short, throw\_accuracy\_mid, throw\_accuracy\_deep, throw\_on\_run, play\_action, break\_sack  

(reuse: SPD, ACC, AGI, AWR)\*\*



\*\*RB/HB - carry, break\_tackle, trucking, elusiveness, spin\_move, juke\_move  

(reuse: SPD, ACC, AGI, CTH)\*\*



\*\*WR/TE - route\_running\_short, route\_running\_mid, route\_running\_deep, catch\_in\_traffic, release, jumping \_(JMP from core)\_  

(reuse: SPD, AGI, AWR, CTH)\*\*



\*\*OL (C/G/T) - pass\_block\_power, pass\_block\_finesse, run\_block\_power, run\_block\_finesse, impact\_block, lead\_block, balance  

(reuse: STR, AWR, PEN)\*\*



\*\*DL/EDGE (DT/DE) - power\_moves, finesse\_moves, block\_shed, pursuit, play\_recognition, tackle  

(reuse: STR, SPD, ACC, AGI)\*\*



\*\*LB (MLB/OLB) - tackle, block\_shed, pursuit, play\_recognition, zone\_coverage  

(reuse: core physical/mental as needed)\*\*



\*\*DB (CB/S) - man\_coverage, zone\_coverage, press, play\_recognition, jumping, catching  

(reuse: SPD, ACC, AGI, AWR, PEN)\*\*



\*\*Specialists (K/P) - kick\_power, kick\_accuracy\*\*



\*\*Return Specialists (applies to any WR/RB/DB assigned as returner) - kick\_return (KR), punt\_return (PR)  

(reuse: SPD, ACC, AGI, CTH, JMP)\*\*



\*\*7.7.1.4 Injury System Hooks \_(Schema-present; gameplay-optional in MVP)\_\*\*



\*\*Keep the fields available so you can enable the feature later without a migration.\*\*



\- \*\*status (enum: Active | Questionable | Out | IR)\*\*

\- \*\*injury\_type (str key), severity\_class (Minor | Moderate | Major | Severe | SeasonEnding)\*\*

\- \*\*weeks\_remaining (int ≥ 0)\*\*

\- \*\*RTP dampeners (temporary floats 0.80-1.00): e.g., rtp\_speed\_mult, rtp\_agility\_mult, …\*\*



\*\*7.7.1.5 Optional Bio \_(Optional/Flavor)\_\*\*



\- \*\*years\_pro (int), college (str), handedness (enum), hometown (str)\*\*

\- \*\*scheme\_fit (tags; for later scheme systems)\*\*

\- \*\*leadership (LEAD) \_(Optional; single dial to support future morale/chemistry/composure hooks - weight can be ~0 in MVP)\_\*\*



\*\*7.7.2 Coach Attributes \_(MVP)\_\*\*



\*\*7.7.2.1 Identity \& Contract\*\*



\- \*\*coach\_id (int), team\_id (int | null if FA)\*\*

\- \*\*role (enum: HC | OC | DC | AC)\*\*

\- \*\*first\_name, last\_name (str)\*\*

\- \*\*age (int)\*\*

\- \*\*salary\_aav (int, \\$/yr), contract\_years (int)\*\*

\- \*\*experience\_years (int)\*\*

\- \*\*offensive\_profile (enum/tag: WestCoast | AirRaid | Vertical | GroundNPound | RPO | Balanced)\*\*

\- \*\*defensive\_profile (enum/tag: Man | Zone | BlitzHeavy | TwoHigh | StopRun | Balanced)\*\*



\*\*7.7.2.2 Strategic Tendencies (0-100 sliders)\*\*



\*\*Offense:\*\*



\- \*\*run\_pass\_tendency (higher = more pass)\*\*

\- \*\*offensive\_aggression (4th-down, shot plays)\*\*

\- \*\*pace (tempo)\*\*

\- \*\*red\_zone\_offense\_bias (pass vs run lean)\*\*

\- \*\*two\_point\_tendency\*\*



\*\*Defense:\*\*



\- \*\*blitz\_rate\*\*

\- \*\*coverage\_mix (0 = man heavy, 100 = zone heavy)\*\*

\- \*\*fourth\_down\_defense (short-yardage aggressiveness)\*\*

\- \*\*red\_zone\_defense\_bias (sell-out run vs pass)\*\*



\*\*Special Teams:\*\*



\- \*\*special\_teams\_focus \_(affects KR/PR usage, average FG try distances, fake rates, and ST discipline tuning)\_\*\*



\*\*7.7.2.3 Performance \& Management Ratings (0-99)\*\*



\- \*\*Development: player\_dev\_offense, player\_dev\_defense\*\*

\- \*\*Team mgmt: discipline (penalties), motivation\_chemistry\*\*

\- \*\*In-game: clock\_management, challenge\_sense\*\*

\- \*\*Situational: red\_zone\_offense, red\_zone\_defense\*\*



\*\*7.7.2.4 Lifecycle \& Outcomes (Computed/UX counters)\*\*



\- \*\*job\_security\_score (derived each offseason)\*\*

\- \*\*owner\_patience (team-level factor)\*\*

\- \*\*Achievements counters: career\_wins, playoff\_wins, sb\_titles, coach\_awards\*\*



\*\*7.7.3 Derived \& Temporary Engine Flags \_(Runtime; not user-editable)\_\*\*



\*\*Players:\*\*



\- \*\*ovr (0-99; per-position derived composite)\*\*

\- \*\*Role/usage: depth\_role (e.g., QB1/QB2/3RDRB/NickelCB), snap\_share (%), fatigue\_pct, hot\_hand (bool/score), active (gameday)\*\*



\*\*Team/Coach:\*\*



\- \*\*script\_pass\_rate, live\_aggression\_adj, endgame\_bias (derived from tendencies + game state)\*\*

\- \*\*Weekly "strategy profile" (Off + Def + ST) locked at kickoff\*\*



\*\*7.7.4 Notes on MVP Implementation\*\*



\- \*\*All ratings listed in §7.7 are available in MVP. If a rating is not immediately central to gameplay, set its tuning weight ≈0 and increase later.\*\*

\- \*\*Injury hooks (§7.7.1.4) and bios (§7.7.1.5) are schema-present but gameplay-optional in MVP, enabling a future switch-on without database changes.\*\*

\- \*\*penalty\_tendency (PEN) is designed as a single global dial per player; coach discipline modulates team-level penalty rates.\*\*

\- \*\*special\_teams\_focus plus KR/PR ensure return leaderboards and ST realism without a separate coordinator system.\*\*



\*\*Assumption: OVR remains a position-aware derived composite that only reads the attributes enumerated in §7.7 and respects current tuning weights.\*\*



\## 7.8 Weekly Awards



\*\*Scope:\*\* Post-week recognition for top performers with deterministic tie-breakers; no gameplay effects in MVP.  

\*\*Categories:\*\* Offensive POTW (AFC, NFC), Defensive POTW (AFC, NFC), Special Teams POTW (AFC, NFC).  

\*\*Eligibility:\*\* Regular-season weeks only; player must have ≥10 snaps (off/def) or ≥1 ST event (for ST POTW).  

\*\*Selection Algorithm (deterministic):\*\*



\- Compute candidate scores:

&nbsp; - \*\*Offense:\*\* EPA/play (w=0.7) + total yards Z (0.2) + TD Z (0.1).

&nbsp; - \*\*Defense:\*\* EPA saved Z (0.5) + sacks Z (0.2) + INTs Z (0.2) + TFL Z (0.1).

&nbsp; - \*\*Special Teams:\*\* FG value-added Z (0.4) + punt value-added Z (0.3) + return TD bonus + net field-position swing Z (0.3).

\- Normalize within conference; choose top per category.

\- \*\*Tie-breakers:\*\* team win → opponent strength (Power Ranking) → player snap share → younger player wins.  

&nbsp;   \*\*Data Model:\*\* weekly\_awards(season\_year, week, conference, category, player\_id, team\_id, score\_components\_json)  

&nbsp;   \*\*UI:\*\* Dashboard ribbon + Awards page filter "Week X".  

&nbsp;   \*\*Acceptance:\*\* Recompute after the week's final game; deterministic with seeds; no duplicates per category.



\## 7.9 Coach Role Titles (HC/OC/DC/AC) - Season \& Career Accounting



\*\*Purpose\*\*  

Credit coaches for conference championships and Super Bowls \*\*by the role they held\*\* that season/game (Head Coach, Offensive Coordinator, Defensive Coordinator, Assistant Coach). These credits appear on season logs and roll up to career totals on the coach profile, and they feed Records and Hall of Fame.



\*\*7.9.1 Data Elements\*\*



\*\*CoachSeasonStats (per coach, per season, per role)\*\*



\- coach\_id (FK → Coach)

\- season (int)

\- team\_id (FK → Team)

\- role (enum: HC, OC, DC, AC)

\- made\_playoffs (bool)

\- conference\_title (enum: NONE, AFC, NFC)

\- super\_bowl\_result (enum: NONE, LOSS, WIN)



\*\*Career Rollups (stored on Coach)\*\*



\- hc\_afc\_championships, hc\_nfc\_championships, hc\_super\_bowl\_wins

\- oc\_afc\_championships, oc\_nfc\_championships, oc\_super\_bowl\_wins

\- dc\_afc\_championships, dc\_nfc\_championships, dc\_super\_bowl\_wins

\- ac\_afc\_championships, ac\_nfc\_championships, ac\_super\_bowl\_wins



\*\*StaffAssignment (role history for snapshot at kickoff)\*\*



\- coach\_id, team\_id, role (HC/OC/DC/AC/S\&C), effective\_from (date), effective\_to (date?)



\*\*7.9.2 When Credits Are Awarded\*\*



\- \*\*Conference Championships (AFCCG/NFCCG)\*\*

&nbsp; - On game finalize, find the \*\*winning team\*\* and its staff \*\*at kickoff\*\* using StaffAssignment.

&nbsp; - For each of HC, OC, DC, and all ACs on the winning team:

&nbsp;   - Upsert CoachSeasonStats with conference\_title = AFC or NFC.

&nbsp;   - Increment the coach's corresponding career counter for that role.

\- \*\*Super Bowl\*\*

&nbsp; - On finalize, mark super\_bowl\_result = WIN for winner, LOSS for loser for each staff role on those teams.

&nbsp; - Increment the winning staff's \*\*super\_bowl\_wins\*\* for their respective roles.

\- \*\*Idempotency\*\*

&nbsp; - Re-finalizing the same game must not double-count (check existing CoachSeasonStats first).



\*\*7.9.3 Edge Cases\*\*



\- \*\*Mid-season role change\*\*: Use the role \*\*at kickoff\*\* of the championship/Super Bowl for credit.

\- \*\*Multiple ACs\*\*: All ACs on the winning team receive the same season credit and career increment.

\- \*\*Interim HC\*\*: If promoted before the Super Bowl, the interim receives HC credit.



\*\*7.9.4 UI / Profile Display\*\*



\*\*Coach Profile → Career Summary\*\*



\- Show totals by role (e.g., "Super Bowls - HC: 1, OC: 2, DC: 0, AC: 1").

\- Show conference titles by role (e.g., "AFC Titles - HC: 1, OC: 1").



\*\*Coach Profile → Season History\*\*



\- One row per season per role with columns: Team, Role, Playoffs, Conference Title, Super Bowl Result.



\*\*7.9.5 Records \& HOF Integration\*\*



\- Record Book categories added (career, scope=COACH):

&nbsp; - MOST\_AFC\_TITLES\_HC / OC / DC / AC

&nbsp; - MOST\_NFC\_TITLES\_HC / OC / DC / AC

&nbsp; - MOST\_SUPER\_BOWL\_WINS\_HC / OC / DC / AC

\- Hall of Fame scoring (see 3.10):

&nbsp; - Heavier weight for HC rings; OC/DC rings weighted moderately; AC lightly.



\*\*7.9.6 API (Summary)\*\*



\- GET /api/v1/coach-stats?coach\_id=\&season=\&role= → returns CoachSeasonStats rows

\- GET /api/v1/coaches/{id} → includes the role-specific career counters

\- GET /api/v1/staff-assignments?team\_id=\&season=\&role= → role snapshots used for credit



\*\*7.9.7 Testing\*\*



\- AFCCG + SB simulation with staff {HC, OC, DC, 2×AC}: verify winners receive season and career increments by role; losers get SB=LOSS only.

\- Interim HC promotion before SB: credit as HC (not OC).

\- Multiple ACs: each receives credit.

\- Re-finalize same game: no duplicates.



\## 7.10 Accessibility and UI Fallbacks



\*\*Accessibility\*\*



\- Modal focus trapping; ESC to close; all actions must be keyboard-reachable.

\- Minimum text contrast 4.5:1; do not use color alone to convey meaning.

\- Provide text alternatives for icons (aria-labels); predictable tab order.



\*\*Fallbacks\*\*



\- If a widget errors, show last known good data from localStorage with a "stale" badge and a \*\*Retry\*\* button.

\- Global error toast uses the standard envelope (see 1.7).



\# 8\\. Off-Season Systems



This section details the full suite of systems that govern the league's off-season, including player development, coaching changes, and all forms of player acquisition.



\## 8.1. Player Progression \& Regression



An end-of-season system that deterministically updates every player's attributes to reflect realistic development and aging. It combines position-specific age curves, dynamic potential, and a usage multiplier.



\- Core Logic: The final attribute delta is a combination of a baseline age curve change, multipliers for potential and usage, and a small amount of deterministic noise. The system includes strict caps to prevent unrealistic changes.  

&nbsp;   Δ\_attr = (Δ\_base × F\_pot × F\_use) + ε\_attr

\- \*\*Stamina is excluded from offseason Δ\_attr.\*\* It does not progress or regress; it only functions as an in-game meter (reset each game).



\*\*8.1.1. Position Groups, Attribute Groups, and Peak Windows\*\*



\- \*\*Position Groups:\*\* QB, RB, WR, TE, OL, DL, LB, DB, K, P.

\- \*\*Attribute Groups:\*\* Physical {speed, strength, agility}; Stamina is an in-game meter only (see §6.11). Skill {throw\_power, throw\_accuracy, catching, tackling}; Mental {awareness}.

\- \*\*Authoritative Peak Windows and Baseline Slopes:\*\* Each position has a peak window (\\\[a\_min, a\_max\\]). Baseline change is zero inside the window. For ages below a\_min, apply pre-peak growth (g\_pre > 0); for ages above a\_max, apply post-peak decline (g\_post < 0).



| \*\*Position\*\* | \*\*Peak Window\*\* | \*\*Physical (pre/post)\*\* | \*\*Skill (pre/post)\*\* | \*\*Mental (pre/post)\*\* |

| --- | --- | --- | --- | --- |

| \*\*QB\*\* | 28-31 | +0.6 / -0.8 | +0.8 / -0.6 | +0.5 / -0.2 |

| \*\*RB\*\* | 24-26 | +1.2 / -2.0 | +0.8 / -1.0 | +0.2 / -0.2 |

| \*\*WR\*\* | 25-28 | +0.9 / -1.4 | +0.9 / -0.7 | +0.3 / -0.2 |

| \*\*TE\*\* | 26-29 | +0.7 / -1.0 | +0.9 / -0.7 | +0.3 / -0.2 |

| \*\*OL\*\* | 28-31 | +0.5 / -0.7 | +0.9 / -0.4 | +0.5 / -0.2 |

| \*\*DL\*\* | 26-29 | +0.8 / -1.2 | +0.7 / -0.6 | +0.3 / -0.2 |

| \*\*LB\*\* | 26-28 | +0.9 / -1.3 | +0.7 / -0.7 | +0.3 / -0.2 |

| \*\*DB\*\* | 25-28 | +1.0 / -1.6 | +0.7 / -0.7 | +0.3 / -0.2 |

| \*\*K/P\*\* | 30-34 | +0.2 / -0.3 | +0.8 / -0.4 | +0.4 / -0.2 |



\*\*8.1.2. Dynamic Potential (P) - Age- and Performance-Responsive\*\*



\- A player's potential rating P (clamped 40-99) evolves based on their age relative to their peak (F\_age) and their on-field performance percentile π (F\_perf).

\- ΔP\_raw = 2.0 × (F\_age × F\_perf − 1). The result is then capped by age-banded limits (e.g., a young player can gain up to +3, while an older player can lose up to -3).



\*\*8.1.3. Usage Model (U ∈\*\*



)



\- U is calculated based on snaps or touches relative to a league-average baseline for the position.

\- \*\*QB:\*\* U = min(1, 0.6 + 0.4 × dropbacks/650)

\- \*\*RB:\*\* U = min(1, 0.5 + 0.5 × touches/300)

\- \*\*WR/TE:\*\* U = min(1, 0.5 + 0.5 × routes\_run/600)

\- \*\*OL/DL/LB/DB:\*\* U = min(1, snaps/1100)



\*\*8.1.4. Attribute Delta Construction\*\*



\- \*\*Baseline Piecewise Delta (Δ\_base):\*\* Set from the age zone and attribute group slope.

\- \*\*Potential-Proximity Multiplier (F\_pot):\*\* F\_pot = 1 + k\_pot × clamp((P − Overall\_pos)/50, −1, 1). This factor increases attribute gains for players who are far below their potential.

\- \*\*Usage Multiplier (F\_use):\*\* F\_use = 1 + k\_use × (2U − 1). High usage accelerates development.

\- \*\*Noise and Determinism (ε\_attr):\*\* A small, truncated normal noise value is added, seeded by hash(player\_id, season\_year, attribute\_name, LEAGUE\_SEED) for reproducibility.

\- \*\*Caps and Clamps:\*\* Strict per-attribute annual caps (e.g., Physical ±3) and lifetime clamps (e.g., 20-99) are applied.

\- \*\*Potential-Respecting Coupling:\*\* After updates, if a player's new overall rating exceeds their potential (P + 3), all positive deltas are scaled back proportionally.



\## 8.2. Coaching Staff System



A league of dynamic coaches (Head Coach, OC, DC) who define a team's strategic identity and evolve over time.



\*\*8.2.1. Coach Attributes \& Data Model\*\*



\- \*\*Static Strategic Tendencies (do not change):\*\* run\_pass\_tendency, offensive\_aggression, pace, blitz\_rate, coverage\_mix, fourth\_down\_tendency, etc.

\- \*\*Dynamic Performance Ratings (evolve yearly):\*\* player\_dev\_offense, player\_dev\_defense, discipline, motivation\_chemistry, clock\_management, challenge\_sense, red\_zone\_offense, red\_zone\_defense.



\*\*8.2.2. Dynamic Coach Progression\*\*



\- At the end of each season, dynamic ratings progress or regress based on the team's statistical rank in relevant categories.

\- \*\*Algorithm:\*\* For each dynamic rating R, the change is calculated as: ΔR = (PerfScore\_R × Volatility × PositionalModifier).

\- \*\*Performance Score Example:\*\* The discipline rating changes based on the team's league rank in Penalties Per Game: PerfScore = (16.5 - Rank) \\\* 0.2.



\*\*8.2.3. Coach Lifecycle Management (Hiring, Firing, Retirement)\*\*



\- \*\*Firing Logic (Job Security Score):\*\*

\- A Job\_Security\_Score is calculated for each Head Coach. If the score falls below a set threshold (e.g., 30), they are fired.

\- JSS = 0.55×WinPct + 0.20×PreseasonPowerRankΔ + 0.15×PlayoffResultScore + 0.10×OwnerPatience − 0.10×BlowoutLosses%.

\- \*\*Hiring Process:\*\*

\- A multi-round system where teams make offers. Coaches evaluate offers using a Coach\_Offer\_Score that weights salary, team prestige, and scheme/personnel fit (e.g., QB potential for an OC).

\- \*\*Retirement Logic:\*\*

\- Coaches aged 65 or older have a deterministic, age-based probability of retiring each offseason.

\- Retirement % = (Coach Age - 64) × 3



\## 8.3. Contracts, Salary Cap \& Negotiations



The complete financial framework for player and coach compensation.



\- \*\*Player Salary Cap:\*\* A \*\*hard ceiling\*\* on team spending for player contracts.

\- \*\*Initial Cap (2025):\*\* \*\*\\$279.2M\*\*

\- \*\*Annual Growth:\*\* \*\*+11.2%\*\* (compounded annually)



\*\*8.3.1. Player Market Value (Dual-Anchor Formula)\*\*



A player's expected salary is a weighted blend of two anchors:



\- \*\*Market Anchor:\*\* Calculated based on AAV% salary bands for a player's position and talent tier (A-F), derived from their OVR percentile. Tiers and bands are defined in calibration CSV files.

\- \*\*Rating \& Performance Anchor:\*\* Calculated from a player's individual ratings, age, and past awards, independent of market-wide percentages. RatingAnchor\\$ = BaseSalary × (1 + PerformanceScore).



\- Reconciliation: The two anchors are combined:  

&nbsp;   ExpectedPlayerSalary\\$ = max(Floor\\$, (w\_market × MarketAnchor\\$) + (w\_rating × RatingAnchor\\$))



\*\*8.3.2. Foundational Salaries (Minimums \& Rookie Scale)\*\*



\- \*\*Veteran Minimums:\*\* An experience-based ladder starting at \\$0.84M for 0 years of service (in 2025), growing annually.

\- \*\*Rookie Scale:\*\* A slotted AAV% is assigned to each draft pick.

\- \*\*Salary Floor:\*\* A player's salary cannot be lower than the maximum of the veteran minimum or their rookie scale slot value.



\*\*8.3.3. Negotiation System\*\*



\- \*\*Flow:\*\* An instantaneous, feedback-driven system. The user submits an offer (AAV and years). It is evaluated via an Offer Score against a hidden "Minimum Acceptance Score" and competing AI offers. The player will accept, reject, or provide a counter-offer.

\- \*\*Offer Score Algorithm:\*\* Final\_Offer\_Score = \\\[(w\_AAV \\\* AAV\_Points) + (w\_Years \\\* Years\_Points) + (w\_Team \\\* Team\_Quality\_Points)\\] \\\* Starter\_Multiplier

\- \*\*Mood Meter:\*\* Tracks the player's patience. Drains on rejections and empties on "insulting" lowball offers, locking the negotiation.



\## 8.4. Free Agency



A multi-team open market where players evaluate offers based on a weighted score.



\- \*\*Offer Evaluation (deterministic):\*\* Score = w\_aav \\\* (AAV / AAV\_anchor) + w\_role \\\* RoleFit + w\_team \\\* TeamQuality + w\_coach \\\* CoachDev.

\- RoleFit ∈ {Starter=1.0, Rotational=0.8, Depth=0.6}.

\- TeamQuality from prior-year power ranking (0.6-1.1).

\- \*\*Acceptance Logic (Tick Logic):\*\* In each "tick" of free agency, a player reviews their top 3 offers. If the best Score >= Threshold, they accept it. The Threshold starts at 1.00 and drops by 0.03 per tick if the player receives no acceptable offers (floor 0.85).

\- \*\*Guardrails:\*\* The system automatically rejects any offer that would put the offering team over the salary cap.



\## 8.5. Player Trades



A system for two-sided trade proposals involving players and draft picks.



\- \*\*Valuation Model (Surplus Value):\*\*

\- For each asset (player or pick), a trade value is calculated.

\- \*\*Player Value:\*\* Calculated based on the Net Present Value (NPV) of the player's contract surplus (their on-field value vs. their salary), discounted over the life of the contract.

\- \*\*Pick Value:\*\* A fixed value for each draft pick is read from a calibration table (pick\_value\_chart.csv).

\- \*\*AI Acceptance Logic (Tolerance Band):\*\*

\- An AI team calculates the total value received vs. the total value sent.

\- It accepts if the net value is positive or within a small negative tolerance band (e.g., -10%). The tolerance is adjustable based on difficulty settings.

\- The AI will reject offers that are imbalanced beyond this tolerance.

\- \*\*Operational Rules:\*\* Trades are allowed from the offseason through the Week 8 trade deadline. Assets can include players and picks from the current draft and the next two drafts.



\## 8.6. Annual Rookie Draft



A 7-round player draft to inject a balanced rookie class into the league.



\- \*\*Class Generation:\*\* The system deterministically generates a draft class by sampling positions according to quotas defined in calibration. It then assigns attributes and potential, and applies a team-specific "scouting noise" to create uncertainty in how different teams grade the same player.

\- \*\*Draft Order:\*\* The order is determined from worst-to-best based on the prior season's record. Tiebreakers are Strength of Schedule, followed by Conference Record, and finally a seeded coin-flip.

\- \*\*On-Clock Timer (Simulation):\*\* If a team's on-clock timer expires, an auto-pick is made. The selection is based on a board ranking calculated as: (team\_need\_weight \\\* scheme\_fit) + best\_available\_grade.

\- \*\*Rookie Contracts (MVP):\*\* Prospects are signed to slotted rookie-scale contracts. This is a fixed yearly salary by round, with a contract length of 4 years for Round 1 and 3 years for Rounds 2-7.



\## 8.7 Waivers \& Claims (R2+)



\*\*Scope:\*\* Simple waiver priority after roster cuts and in-season releases; contracts remain MVP-simple (AAV only).  

\*\*Windows:\*\* Preseason→Week 1: 48-hour waiver; In-season: 24-hour waiver after release.  

\*\*Priority:\*\* Reverse \*\*Power Ranking\*\* at claim time (lower rank = higher priority). Ties → worse record → conference record → seeded coin flip.  

\*\*Flow:\*\* release → enters waiver\_wire (with deadline\_ts) → teams may submit claim(max\_aav) → at deadline, winner by priority (AAV ignored in MVP) → player signs 1-yr at current AAV.  

\*\*Data:\*\*



\- waiver\_wire(id, player\_id, releasing\_team\_id, created\_ts, deadline\_ts)

\- waiver\_claims(waiver\_id, team\_id, ts)  

&nbsp;   \*\*Acceptance:\*\* Deterministic resolution; winner must fit 53-man \& cap; UI surfaces a "Waiver Claims" widget.



\# 9\\. User Interface \& Experience (UI/UX)



This section defines the global rules for the user interface and the specific layouts for all MVP screens.



\## 9.1. Global UI Rules \& Navigation



\- \*\*Theme:\*\* Dark mode with blue and gold accents. Team primary colors may tint page headers where applicable.

\- \*\*Layout:\*\* Every screen uses a responsive three-column grid system with equal-width columns: C1 (left), C2 (middle), and C3 (right). All content appears in "Boxes" (cards) that can span 1, 2, or 3 columns, as defined per page.

\- \*\*Sticky Header \& Controls:\*\* A persistent top header shows the active team (name + record) and primary simulation controls (e.g., Sim Week, Next). The main navigation bar sits directly beneath it.

\- \*\*Canonical Navigation Order:\*\* The main navigation bar is always visible in this exact order: \*\*Dashboard | Roster | Staff | GM Desk | Draft | Playoffs | Stats | HOF\*\*.

\- \*\*"Coming Soon" Behavior (MVP):\*\* Non-MVP pages (Staff, GM Desk, Draft, HOF) remain in the navigation bar. Clicking a non-MVP link routes to the page (e.g., /staff) and renders a standard page shell with a clear "Coming Soon" message and no functional widgets.

\- \*\*Interactive Elements:\*\*

\- \*\*Player/Coach Card Modal:\*\* Clicking on a player or coach name opens a detailed modal view showing attributes, contract details, and stats.

\- \*\*Tables \& Carousels:\*\* All tables are sortable and filterable. Carousels are used to cycle through ranked content (e.g., top performers, power rankings).



\## 9.2. Screen Layouts (MVP)



\*\*Assumptions (minimal):\*\*  

• Theme/grid inherit from §9.1.  

• MVP renders a uniform "Coming Soon" shell where a page is R2 (still shows cards with placeholder copy).  

• All "Name click" opens the standard modal pattern (Player/Coach cards).  

• All endpoints support ?demo=true to return mock data during UI development.



\### 9.2.1 Dashboard - League Overview (MVP)



\*\*Purpose\*\*  

Give a high-level league/team snapshot and quick links into deeper pages. Always loads on app start.



\*\*9.2.1.1 Layout (3-col desktop; responsive to 2/1 col)\*\*



\- \*\*C1 (Left)\*\*:

&nbsp; - Division Standings (team logos, W-L, GB, streak)

&nbsp; - League Power Rankings (carousel)

&nbsp; - League Top Performers (carousel: QB/RB/WR + DEF leaders)

\- \*\*C2 (Middle)\*\*:  

&nbsp;   4) Team Schedule (current team; scroll list by week)  

&nbsp;   5) Box Score (spans C2-C3; shows last/active game)  

&nbsp;   6) Play-by-Play panel (for active/last game)

\- \*\*C3 (Right)\*\*:  

&nbsp;   7) Scouting Box (team needs \& upcoming opponent snapshot)  

&nbsp;   8) Box Score continuation (expanded team stats)  

&nbsp;   9) Team Top Performers (season-to-date)



\*\*9.2.1.2 Interactions\*\*



\- Click team/player names → open modal.

\- Power Rankings scroll; hover shows ELO/Power metric.

\- Schedule row click → loads game detail in Box Score/PBP.



\*\*9.2.1.3 DTOs\*\*  

StandingsRow{team\_id, div, w, l, pct, gb, streak}  

PowerRow{team\_id, rank, power\_rating, delta}  

LeaderRow{player\_id, team\_id, pos, stat\_key, stat\_val}  

ScheduleItem{week, opponent\_id, home\_away, result?, score?}  

BoxScore{game\_id, home\_id, away\_id, linescore\\\[\\], team\_stats, leaders\\\[\\]}  

PBPEvent{clock, quarter, down\_dist, desc}  

Scouting{opponent\_id, strengths\\\[\\], weaknesses\\\[\\], team\_needs\\\[\\]}



\*\*9.2.1.4 Endpoints\*\*  

GET /api/standings?division= → StandingsRow\\\[\\]  

GET /api/power → PowerRow\\\[\\]  

GET /api/leaders?scope=league\&bucket=season → LeaderRow\\\[\\]  

GET /api/schedule?team\_id= → ScheduleItem\\\[\\]  

GET /api/box?game\_id=|latest=true → BoxScore  

GET /api/pbp?game\_id=|latest=true → PBPEvent\\\[\\]  

GET /api/scouting?team\_id= → Scouting



\*\*9.2.1.5 Acceptance\*\*  

No blank panes; Box Score spans correctly; mobile stacks C1→C2→C3.



\*\*9.2.1.6 Error/Accessibility\*\*  

Inline error per card; ARIA labels; tab order follows visual order.



\*\*9.2.1.7 Cross-Refs\*\*  

§6 Score Fidelity, §7 Stats, §11 Awards widgets.



\### 9.2.2 Roster - Players, Depth Chart \& Contracts (MVP)



\*\*Purpose\*\*  

Manage roster, depth chart, and see contract basics.



\*\*9.2.2.1 Layout\*\*



\- \*\*C1\*\*:

&nbsp; - Roster Table (filters: POS, OVR, contract flags; actions)

&nbsp; - Depth Chart Mini (QB/RB/WR/TE/OL; DL/LB/DB; ST)

\- \*\*C2\*\*:  

&nbsp;   3) Player Card Panel (selected player summary + tabs: Attributes, Recent Games, Contract)  

&nbsp;   4) Auto-Depth Assign (button + preview diff)

\- \*\*C3\*\*:  

&nbsp;   5) Contract Snapshot (cap space, top 5 AAV, expiring list)  

&nbsp;   6) Injury Report (status, ETA, RTP penalty preview)



\*\*9.2.2.2 Interactions\*\*



\- Click player → modal (full card).

\- Drag-and-drop depth slots (R2), MVP uses "Promote/Demote" buttons.

\- Auto-Depth runs deterministic rule (see §6.x depth rules) and shows diff before apply.



\*\*9.2.2.3 DTOs\*\*  

PlayerRow{player\_id, name, pos, age, ovr, pot, contract{years,aav,exp}, status{injury?, eta?}}  

DepthSlot{unit, pos, slot, player\_id}  

ContractSummary{cap\_space, top\_contracts\\\[\\], expiring\\\[\\]}  

InjuryRow{player\_id, type, severity, weeks\_remaining, rtp\_penalty}



\*\*9.2.2.4 Endpoints\*\*  

GET /api/roster?team\_id= → PlayerRow\\\[\\]  

GET /api/depth?team\_id= → DepthSlot\\\[\\]  

POST /api/depth/auto?team\_id= → DepthSlot\\\[\\] (preview if ?apply=false)  

GET /api/contracts?team\_id= → ContractSummary  

GET /api/injuries?team\_id= → InjuryRow\\\[\\]



\*\*9.2.2.5 Acceptance\*\*  

Filters work; Auto-Depth shows reversible preview; injury ETA renders.



\*\*9.2.2.6 Error/Access.\*\*  

Conflicts (duplicate slot) show inline warnings; ARIA grid for roster table.



\*\*9.2.2.7 Cross-Refs\*\*  

§6 Depth \& Sub rules, §10 Injuries, §8 Contracts.



\### 9.2.3 Playoffs - Bracket \& Results (MVP)



\*\*Purpose\*\*  

Show the 14-team bracket, seeds, matchups, and results.



\*\*9.2.3.1 Layout\*\*



\- \*\*C1\*\*:

&nbsp; - Bracket Overview (AFC/NFC, seeds, lines)

&nbsp; - Tie-in Legend (seed rules, tiebreak quick ref)

\- \*\*C2\*\*:  

&nbsp;   3) Round Panel (Wildcard → Divisional → Champ → SB) with matchups and game times/results  

&nbsp;   4) Game Detail (selected game Box mini, leaders)

\- \*\*C3\*\*:  

&nbsp;   5) Team Path Card (selected team path to SB)  

&nbsp;   6) Records \& Milestones (postseason leaders)



\*\*9.2.3.2 Interactions\*\*



\- Click team → highlight path; click game → load Game Detail.



\*\*9.2.3.3 DTOs\*\*  

TeamSeed{team\_id, conf, seed, w, l, power\_rating}  

Matchup{game\_id, round\_name, conf\_side, higher\_seed, lower\_seed, date, status, score?}  

PSLeaders{category, rows\\\[\\]}



\*\*9.2.3.4 Endpoints\*\*  

GET /api/playoffs/seeds → TeamSeed\\\[\\]  

GET /api/playoffs/matchups?round= → Matchup\\\[\\]  

GET /api/box?game\_id= → BoxScore  

GET /api/leaders?scope=postseason → PSLeaders



\*\*9.2.3.5 Acceptance\*\*  

Bracket draws correctly; path highlight persists selection; mobile stacks.



\*\*9.2.3.6 Error/Access.\*\*  

Graceful when a round not generated yet; ARIA roles for bracket nodes.



\*\*9.2.3.7 Cross-Refs\*\*  

§4 Season Loop, §6 SFS, §7 Stats.



\*\*9.2.4 Stats - League/Team/Player (MVP)\*\*



\*\*Purpose\*\*  

Browse/search all stats; power the Awards/Records widgets.



\*\*9.2.4.1 Layout\*\*



\- \*\*C1\*\*:

&nbsp; - Search \& Filters (season vs career; qualifiers; position)

&nbsp; - League Leaders (sortable table; paginated)

\- \*\*C2\*\*:  

&nbsp;   3) Player Finder (attribute/stat queries; saved searches later)  

&nbsp;   4) Team Stats (off/def splits; advanced rates)

\- \*\*C3\*\*:  

&nbsp;   5) Milestones Tracker  

&nbsp;   6) Records Tracker (single-season, career, game)



\*\*9.2.4.2 Interactions\*\*



\- Query builder (>=, <=, in-pos, team, min snaps).

\- Click rows → open Player/Team modal.



\*\*9.2.4.3 DTOs\*\*  

StatRow{entity\_id, entity\_type:"player"|"team", keys:{...}}  

RecordRow{scope:"career"|"season"|"game", stat\_key, holder\_id, value, season?, team\_id?}  

Milestone{stat\_key, target, current, pct\_to\_goal}



\*\*9.2.4.4 Endpoints\*\*  

POST /api/stats/query (body = filter DSL) → StatRow\\\[\\]  

GET /api/records?scope= → RecordRow\\\[\\]  

GET /api/milestones?team\_id=|player\_id= → Milestone\\\[\\]



\*\*9.2.4.5 Acceptance\*\*  

Queries return within 500ms on demo data; CSV export icon shows (R2).



\*\*9.2.4.6 Error/Access.\*\*  

Invalid filters return human-readable message; tables are keyboard friendly.



\*\*9.2.4.7 Cross-Refs\*\*  

§7 Stats Catalog, §11 Awards, §6 SFS.



\### 9.2.5 Staff - Coaching Roster \& Modifiers (R2 target; MVP = Shell)



\*\*Purpose\*\*  

View staff, schemes, and trait effects on sim. MVP shows shell text.



\*\*9.2.5.1 Layout\*\*



\- \*\*C1\*\*: Head Coach Card; Coordinator Cards; Staff Discipline/Conditioning meter

\- \*\*C2\*\*: Scheme \& Sliders (read-only in MVP); Trait Effects Matrix

\- \*\*C3\*\*: Player Impact Preview; Practice \& Conditioning Policy (read-only in MVP)



\*\*9.2.5.2 Interactions\*\*  

Name click → Coach modal; scheme changes R2; tooltips explain trait hooks.



\*\*9.2.5.3 DTOs\*\*  

CoachSummary{coach\_id, role, ovr, scheme\_tag, contract{years,aav}, traits\\\[\\], team\_id}  

SchemeState{off\_scheme, def\_scheme, global{tempo,aggression}, effective\_from\_week}  

TraitEffect{trait\_key, system\_hook, magnitude\_range, stacking\_rule}  

PlayerImpactPreview{player\_id, pos, deltas{tendency%, success%, stamina%, penalty%, rtp%}}



\*\*9.2.5.4 Endpoints\*\*  

GET /api/staff/summary?team\_id=  

GET /api/staff/schemes?team\_id=  

GET /api/staff/traits?team\_id=  

GET /api/staff/impacts?team\_id=



\*\*9.2.5.5 Acceptance\*\*  

No blank panes; clean mobile stack; deltas hidden if inputs missing.



\*\*9.2.5.6 Error/Access.\*\*  

Inline card errors; ARIA card headers; focus-trapped modals.



\*\*9.2.5.7 Cross-Refs\*\*  

§10 Strategy Profiles, §6 Weather-conditioning tie-ins, §11 Awards (COTY/GMOTY hooks).



\*\*9.2.6 GM Desk - Transactions, Cap, Trades (R2 target; MVP = Shell)\*\*



\*\*Purpose\*\*  

Front office actions: signings, waivers, trades, cap planning. MVP shows shell text and read-only summaries.



\*\*9.2.6.1 Layout\*\*



\- \*\*C1\*\*:

&nbsp; - Cap Overview (space, penalties, projected next year)

&nbsp; - Expiring Contracts (sortable list)

&nbsp; - Trade Block (your players flagged)

\- \*\*C2\*\*:  

&nbsp;   4) Free Agents Board (filters; sort by OVR/age/ask)  

&nbsp;   5) Offer Composer (R2): terms, guarantees, bonuses; likelihood meter

\- \*\*C3\*\*:  

&nbsp;   6) Trade Builder (R2): you ↔ other team assets; value delta meter  

&nbsp;   7) Transaction Log (recent league moves)



\*\*9.2.6.2 Interactions\*\*



\- Add FA to short-list; compose offers (R2); propose trades (R2).

\- Offer likelihood uses deterministic negotiation model (§8).



\*\*9.2.6.3 DTOs\*\*  

CapSummary{year, cap\_space, dead\_cap, proj\_next}  

ExpiringRow{player\_id, pos, age, ovr, aav, exp\_year}  

FAPlayer{player\_id, pos, age, ovr, demand{years,aav,bonus}}  

Offer{player\_id, years, aav, bonus, clauses\\\[\\]}  

TradePackage{from\_team\_id, to\_team\_id, players\\\[\\], picks\\\[\\]}



\*\*9.2.6.4 Endpoints\*\*  

GET /api/cap?team\_id= → CapSummary  

GET /api/contracts/expiring?team\_id= → ExpiringRow\\\[\\]  

GET /api/free\_agents?pos=|min\_ovr= → FAPlayer\\\[\\]  

POST /api/offers/eval (R2) → {likelihood, notes}  

POST /api/trades/eval (R2) → {value\_delta, veto\_risk}



\*\*9.2.6.5 Acceptance\*\*  

Read-only cards populate in MVP; R2 actions gated behind disabled buttons with tooltips.



\*\*9.2.6.6 Error/Access.\*\*  

Human-readable validation; ARIA forms; keyboard navigation for tables.



\*\*9.2.6.7 Cross-Refs\*\*  

§8 Contracts/Negotiations, §3.6 Data Seeds (roster/FA pools).



\### 9.2.7 Draft - Scouting \& Selection (R2 target; MVP = Shell)



\*\*Purpose\*\*  

Manage draft board, view prospects, run the draft day experience. MVP: shell + read-only board preview if data exists.



\*\*9.2.7.1 Layout\*\*



\- \*\*C1\*\*:

&nbsp; - Your Picks (by round; via trades)

&nbsp; - Team Needs Meter (by position tiers)

\- \*\*C2\*\*:  

&nbsp;   3) Prospects Board (filters: position, grade, age; columns: OVR est, potential, scheme fit)  

&nbsp;   4) Player Profile (selected prospect: measurables, comps, risk flags)

\- \*\*C3\*\*:  

&nbsp;   5) Draft Queue (your shortlist; reorder)  

&nbsp;   6) Draft Day Panel (R2): live ticker, on-clock timer, best available



\*\*9.2.7.2 Interactions\*\*



\- Add/remove to queue; reorder (R2); pick when on clock (R2).



\*\*9.2.7.3 DTOs\*\*  

Pick{round, pick\_overall, team\_id}  

NeedRow{pos, tier, urgency}  

Prospect{prospect\_id, pos, age, grade, ovrest, potential, scheme\_fit, flags\\\[\\]}  

Comp{player\_archetype, similarity}



\*\*9.2.7.4 Endpoints\*\*  

GET /api/draft/picks?team\_id= → Pick\\\[\\]  

GET /api/draft/needs?team\_id= → NeedRow\\\[\\]  

GET /api/draft/prospects?filters= → Prospect\\\[\\]  

GET /api/draft/prospect/{id} → Prospect+Comp  

POST /api/draft/pick (R2) → confirmation



\*\*9.2.7.5 Acceptance\*\*  

Prospect list paginates; profile loads; shell copy explains R2 actions.



\*\*9.2.7.6 Error/Access.\*\*  

Clear filter validation; ARIA for lists and "on-clock" announcements (R2).



\*\*9.2.7.7 Cross-Refs\*\*  

§8 Offseason Loop, §7 Attributes, §3.6 Seeds (prospects).



\### 9.2.8 Hall of Fame (HOF) - Legends \& Records (R2 target; MVP = Shell)



\*\*Purpose\*\*  

Browse HOF players/coaches, view inductions, and link to career records. MVP: shell + read-only if seeds are present.



\*\*9.2.8.1 Layout\*\*



\- \*\*C1\*\*:

&nbsp; - Inductees by Year (timeline)

&nbsp; - Eligibility \& Ballot (R2)

\- \*\*C2\*\*:  

&nbsp;   3) HOF Directory (filters: player/coach, position, team history)  

&nbsp;   4) Profile Panel (selected inductee: bio, peak seasons, awards)

\- \*\*C3\*\*:  

&nbsp;   5) Career Records Spotlight (top 10 lists, clickable)  

&nbsp;   6) Milestone Map (teams with most HOFers)



\*\*9.2.8.2 Interactions\*\*



\- Click inductee → modal with full career card.

\- Filters stack; clicking a record holder jumps to their profile.



\*\*9.2.8.3 DTOs\*\*  

HOFEntry{id, type:"player"|"coach", name, class\_year, teams\\\[\\], accolades\\\[\\], bio}  

CareerRecord{stat\_key, rank, holder\_id, value}



\*\*9.2.8.4 Endpoints\*\*  

GET /api/hof/inductees?year=|all= → HOFEntry\\\[\\]  

GET /api/hof/directory?filters= → HOFEntry\\\[\\]  

GET /api/records?scope=career → CareerRecord\\\[\\]



\*\*9.2.8.5 Acceptance\*\*  

Directory filters work on demo data; profile loads; shell copy present.



\*\*9.2.8.6 Error/Access.\*\*  

Graceful empty-state if seeds absent; ARIA timeline/list semantics.



\*\*9.2.8.7 Cross-Refs\*\*  

§3.6 Data Seeds (HOF Players/Coaches; Records XLS), §7 Stats/Records.



\*\*Global MVP "Coming Soon" Shell Pattern\*\*  

Any R2 page/card in MVP shows: Title, short paragraph explaining timing, and a disabled CTA ("Available in R2"). Cards still render to preserve grid. If an endpoint is missing, the card auto-falls back to the shell with no console errors.



\# 10\\. Development Roadmap (Post-MVP Features)



This section outlines features that are planned for future releases beyond the initial MVP. The specifications here define their intended behavior and logic for R2 (Release 2) and beyond.



\*\*10.1. Player Injury System\*\*



\*\*This system models player injuries, in-game (quarter-based) absences, multi-week injuries, and "Return-to-Play" (RTP) performance penalties. Disabled for MVP (R1) and enabled in R2. It is deterministic under the league seed.\*\*



\*\*10.1.1. Core Injury Mechanics\*\*



\*\*Injury Taxonomy \& Severity. Injuries are categorized by type (e.g., Soft Tissue, Joint/Ligament, Bone/Fracture, Head/Neurological, Illness/Cramp) and mapped to a severity class that drives duration:\*\*



\- \*\*Minor: 0-7 days (≈0-1 game)\*\*

\- \*\*Moderate: 1-3 weeks\*\*

\- \*\*Major: 3-8 weeks\*\*

\- \*\*Severe: 8-20 weeks\*\*

\- \*\*Season-ending: Remainder of season (league-capped)\*\*



\*\*Incidence Model \& Triggers. A per-snap injury probability is computed deterministically:\*\*



\*\*p\_i = base\_rate × PosMulti × Usage\_i × Aggression × PronenessCurve\_i × LeagueFreq\*\*



\- \*\*Positional Multipliers (PosMulti): Role risk (e.g., RB, LB: 1.10×-1.25×; OL/DL variable by scheme).\*\*

\- \*\*Usage\_i: Recent workload proxy (snaps/touches last X plays or game trend).\*\*

\- \*\*Aggression: Team slider factor (0.9-1.1 suggested bounds).\*\*

\- \*\*PronenessCurve\_i: Maps injury\_proneness ∈ \\\[0,100\\] to ~0.75×-1.35×.\*\*

\- \*\*LeagueFreq: Season-level tuning for global injury rate.\*\*



\*\*Duration \& Recovery (Weekly). When a weekly severity is drawn, duration is sampled from a truncated distribution within its class window (caps enforced). Bye week healing multiplier: 1.35× (configurable).\*\*



\*\*RTP Performance Modifiers (Weekly). On return from a weekly injury, apply an initial attribute multiplier M\_0 that recovers exponentially per game:\*\*



\*\*M\_{t+1} = 1 - ((1 - M\_t) × (1 - d)) (where d is the per-game decay rate)\*\*



\*\*Typical M\_0 ranges by attribute: Speed 0.88-0.97; Agility 0.88-0.97; Strength 0.92-0.98; Throw Power 0.92-0.98; Awareness 0.95-0.99.\*\*



\*\*10.1.1a. In-Game Injury Durations (Quarter-Based)\*\*



\*\*Purpose. Model injuries that keep a player out for 1-4 quarters of the current game. Some may later escalate into a multi-week injury after medical evaluation.\*\*



\*\*Timescale Roll. On injury event, roll Timescale ∈ {Q-Only, Weeks} based on archetype + context:\*\*



\- \*\*Non-contact/fatigue or late-game hits → higher Q-Only weight.\*\*

\- \*\*High-impact contact/torque → higher Weeks weight.\*\*



\*\*Quarter Duration Draw. For Q-Only, draw q ∈ {1,2,3,4} with base weights:  

P(1)=0.45, P(2)=0.30, P(3)=0.15, P(4)=0.10); cap by quarters remaining. If drawn q ≥ quarters remaining → mark Out for Game (OFG).\*\*



\*\*Clock Integration. With 15-minute quarters, set return\_at = now + q × quarter\_length.\*\*



\*\*Same-Game RTP. If the player returns the same game, apply a temporary attribute penalty for the remainder of that game and, in some cases, a smaller penalty for the next game (decay via 10.1.5).\*\*



\*\*Post-Game Escalation. After the game, some Q-Only injuries roll to escalate into weekly absences (see 10.1.2 table).\*\*



\*\*10.1.1b. Return-to-Play (RTP) Profiles (Per-Injury Overrides)\*\*



\*\*By default, weekly injuries use the exponential recovery in 10.1.1. The table in 10.1.2 includes per-injury overrides for:\*\*



\- \*\*Same-Game RTP penalties, and\*\*

\- \*\*First N Games After Return penalties.\*\*



\*\*If present, these overrides supersede the defaults for those injuries.\*\*



\*\*10.1.2. Injury Type Table\*\*



| \*\*Category\*\* | \*\*Injury\*\* | \*\*Timescale\*\* | \*\*Base Duration\*\* | \*\*Affected Attributes\*\* | \*\*RTP (Same Game)\*\* | \*\*RTP (Next Games)\*\* | \*\*Post-Game Escalation\*\* |

| --- | --- | --- | --- | --- | --- | --- | --- |

| Minor (Q) | Stinger / Burner | Q-Only | 1-2 quarters (OFG possible) | strength, tackling | \\-5% strength rest of game | \\-2% for 1 game (decays) | 5% → Minor (3-5 days) |

| Minor (Q) | Cramps / Dehydration | Q-Only | 1 quarter (sometimes 2) | stamina, speed | \\-3% stamina rest of game |     | 2% → Minor (2-3 days) |

| Minor (Q) | Wind Knocked / Light Rib Bruise | Q-Only | 1-2 quarters | awareness, strength | \\-3% awareness rest of game |     | 8% → Minor (3-7 days) |

| Minor (Q) | Ankle Roll (tape \& test) | Q-Only | 1-3 quarters (OFG possible) | speed, agility | \\-5% speed/agility rest of game | \\-2% for 1 game | 15% → Minor (1-2 wks) |

| Moderate (Q) | Hamstring Tweak | Q-Only | 2-4 quarters (often OFG) | speed, agility | \\-8% speed rest of game | \\-3% for 1 game | 25% → Moderate (1-3 wks) |

| Moderate (Q) | Concussion Eval (failed) | Q-Only | OFG | awareness | No return | Protocol governs (4-14 days typical) | 20% → Minor-Moderate (protocol) |

| Minor | Bruised Ribs (moderate) | Weeks | 1-2 wks | throw\_power, strength |     | \\-5% for 1 game |     |

| Minor | Mild Ankle Sprain | Weeks | 1-2 wks | speed, agility |     | \\-5% for 1 game |     |

| Minor-Mod | Turf Toe | Weeks | 1-3 wks | acceleration, agility |     | \\-5% for 1 game |     |

| Moderate | Groin Strain | Weeks | 1-3 wks | speed, agility |     | \\-5% for 1 game |     |

| Q/Minor | Back Spasms (chronic) | Q or Weeks | Q: 1-2 qtrs; Weeks: 1-3 wks | strength, agility | \\-5% strength rest of game |     | 10% monthly recurrence |

| Moderate | High Ankle Sprain | Weeks | 4-6 wks | speed, agility |     | \\-5% for 2 games |     |

| Mod-Major | MCL Sprain (Grade I-II) | Weeks | 3-6 wks | strength, tackling |     | \\-5% for 1-2 games |     |

| Major | Separated Shoulder | Weeks | 4-8 wks | throw\_power, strength |     | \\-7% for 2 games |     |

| Major | Broken Hand (non-throwing) | Weeks | 4-6 wks | catching, tackling |     | First game back: cast penalty -5% |     |

| Severe | Broken Collarbone | Weeks | 8-10 wks | throw\_power, strength |     | \\-8% for 2-3 games |     |

| Severe | Torn Meniscus (scope) | Weeks | 6-8 wks | agility, acceleration |     | \\-6% for 2 games |     |

| Season-End | Torn ACL | Season | Season | speed, agility, strength |     | N/A |     |

| Season-End | Torn Achilles | Season | Season | acceleration, speed |     | N/A |     |



\*\*Notes.\*\*



\- \*\*OFG (Out for Game): Triggered when drawn quarters ≥ remaining quarters or medical rule bars return (e.g., failed concussion eval).\*\*

\- \*\*Position Bias: Stingers LB/DB; shoulder QB/WR; turf toe WR/RB/QB-mobile; MCL OL/DL/LB.\*\*

\- \*\*Bye-Week Healing: Weekly injuries benefit from the 1.35× bye healing multiplier.\*\*



\*\*10.1.3. System Implementation \& Safety\*\*



\*\*SFS Integration. The Score Fidelity System may apply a +1.0% max compensatory tweak to the league scoring multiplier if a spike in injuries depresses offense below tolerance.\*\*



\*\*Safeguards.\*\*



\- \*\*Team Availability Throttle: If a team exceeds max\_absent\_players, auto-reduce per-snap injury risk for that team until they fall below the cap.\*\*

\- \*\*Season-Ending Cap: If the league cap for season-ending injuries is reached, redistribute probability mass to lower severities for the remainder of the season.\*\*



\*\*10.1.4. Escalation \& Recurrence Rules\*\*



\*\*Escalation (Q → Weeks). After a Q-Only injury game, roll the listed Post-Game Escalation chance. On success, convert to the specified Minor/Moderate window and apply the RTP (Next Games) profile.\*\*



\*\*Chronic Flags. Certain injuries (e.g., hamstring, back spasms) set a recurrence flag with a periodic check (weekly or monthly). A recurrence can trigger:\*\*



\- \*\*A fresh Q-Only absence, or\*\*

\- \*\*A shortened Minor window (tunable), with reduced but non-zero RTP penalties.\*\*



\*\*10.1.5. RTP Decay Policy (Consistency)\*\*



\*\*Use the exponential rule from 10.1.1 for all weekly returns. For injuries with table overrides, set:\*\*



\- \*\*M\_0 to the specified initial penalty, and\*\*

\- \*\*Choose d so the penalty decays to ≈0 over the indicated 1-3 games (e.g., d ≈ 0.5-0.7 for 2-game fade).\*\*



\*\*Same-game penalties (Q-Only returns) apply immediately and expire at the final whistle, unless a "next-game" note is specified.\*\*



\*\*10.1.6. Engine Integration (In-Game \& Data)\*\*



\*\*State \& Timestamps.\*\*



\- \*\*For Q-Only: store injury.return\_at\_game\_clock (or status=OUT\_GAME if OFG).\*\*

\- \*\*For weekly: store injury.out\_weeks\_remaining and injury.rtp\_profile.\*\*



\*\*UI Hooks.\*\*



\- \*\*PBP/Box: show countdown (minutes/quarters) or OFG tag.\*\*

\- \*\*Next-Game badge: display expected RTP penalty (e.g., "−5% Speed (1 game)").\*\*

\- \*\*Roster/Depth: flag Questionable/Probable/Out from thresholds (optional R2 polish).\*\*



\*\*Data \& Tuning.\*\*



\- \*\*Table 10.1.2 can be exported as /app/data/injuries.csv with columns:  

&nbsp;   category,injury,timescale,base\_duration,affected,r2p\_same,r2p\_next,escalation\_rate,notes\*\*

\- \*\*All randomness must be seeded off the league seed for save/load determinism.\*\*



\*\*10.2. Advanced Coaching \& Strategy Profiles - \_Expanded\_\*\*



These profiles provide a strategic identity for a game by modifying play-call frequencies and applying minor, conditional attribute boosts.



\- \*\*Selection:\*\* A coach selects one Offensive and one Defensive strategy profile before a game, which is locked for the duration.

\- \*\*Balance \& Brittleness Tax:\*\* All strategies are governed by strict tuning guardrails. Play-family frequency shifts are capped at ±60%. All strategies have an inherent risk ("brittleness tax"), e.g., Run-Heavy Offenses suffer an extra -10% weight on explosive passes when trailing by 10+ points.



\*\*10.2.1. Offensive Strategy Profiles (Examples)\*\*



| \*\*Strategy\*\* | \*\*Core Effect\*\* | \*\*Best Used When\*\* |

| --- | --- | --- |

| \*\*Ground \& Pound\*\* | +50% run plays, -35% deep passes | You have a lead, bad weather, or a dominant offensive line. |

| \*\*West Coast (Quick Game)\*\* | +60% quick/short pass concepts, -40% deep shots | Facing a heavy pass rush or soft, off-coverage. |

| \*\*Air Raid\*\* | +70% spread passes, +20% tempo, -40% runs | You have elite WR depth and a high-volume QB. |

| \*\*Vertical (Air Coryell)\*\* | +50% deep/intermediate passes, -30% screens | You have big outside WRs and a strong-armed QB. |

| \*\*RPO Emphasis\*\* | +70% RPO tags on early downs, -40% pure dropbacks | The opponent has linebackers with static, predictable rules. |



\*\*10.2.2. Defensive Strategy Profiles (Examples)\*\*



| \*\*Strategy\*\* | \*\*Core Effect\*\* | \*\*Best Used When\*\* |

| --- | --- | --- |

| \*\*Stop the Run\*\* | +50% 8-man boxes, +3-4 Shed/Tackle vs run | Facing a run-heavy, gap/power scheme. |

| \*\*Man Coverage\*\* | +40% man calls, +3-4 Man Cov rating | You have elite CBs who can win one-on-one matchups. |

| \*\*Zone Coverage\*\* | +40% zone calls, +3-4 Zone/Play Rec rating | You need to protect against deep passes. |

| \*\*Blitz Heavy\*\* | +65% 5+ man pressures, +3-4 Pass Rush ratings | Facing a QB with slow processing or a weak offensive line. |

| \*\*Two-High Shell\*\* | +50% split-safety looks (Cover-2/4/6) | Facing an opponent with a dangerous deep passing game. |



\# 11\\. Future To-Do List



This is a consolidated list of pending items for future development cycles.



\- \*\*Financials:\*\*

\- Implement a formula to calculate dead cap money when players are released.

\- \*\*UI/UX:\*\*

\- Allow users to customize page layouts by moving and resizing modules/cards. Their location and size should be user-definable.

\- \*\*Coaching Staff:\*\*

\- Create a single, composite \*\*"Overall"\*\* rating calculation for coaches, similar to the one players have, for easier comparison.

\- Add a \*\*Trainer\*\* to the coaching staff who will impact injury occurrence and recovery speed.

\- \*\*File System:\*\*

\- Update all hardcoded Windows file paths (e.g., C:\\\\Users\\\\bpalm\\\\...) to be relative paths from the project root (e.g., /data/reports/) to ensure the system is OS-agnostic.



\# 12\\. Headlines Feature (MVP)



\#\# 12.1 Overview



"Weekly Headlines" is an AI-generated news briefing displayed at the top of the Dashboard after each weekly simulation. The feature synthesizes in-game events (upsets, records, milestones, standings shifts, injuries) into 3–5 punchy one-sentence headlines ranked by notability. Headlines are generated via API call to Claude (Anthropic) and cached in the save file. If no internet connection is available, a fallback message prompts the user to connect for headlines.



\#\# 12.2 Event Detection \& Tier System



After each weekly simulation completes, the game runs an event-detection pass to identify candidate stories, score them by tier and sub-criteria, and select the top 4–5 for headline generation.



\#\#\# 12.2.1 Tier 1 — Mandatory (Auto-include if present)



Events in Tier 1 always appear in the headline list. If multiple Tier 1 events occur in a single week, all are included (capped at 3 total).



\*\*1a. Your Team — Standings/Playoff Implications\*\*



\- Condition: User's team clinches division title, playoff spot, or \*\*playoff bye week\*\* (not regular bye)

\- Condition: User's team is eliminated from playoff contention

\- Condition: User's team takes or loses the division lead

\- Data required: standings before/after, playoff seed/bye status

\- Example: "Chiefs clinch AFC West and #1 seed bye"



\*\*1b. Single-Season or Career Records\*\*



\- Condition: Any player (any team) breaks a single-season franchise record (e.g., most passing yards, sacks, rushing TDs in a season) OR breaks an all-time historical NFL record

\- Data required: player\_id, season stats, previous franchise single-season record, all-time record if applicable

\- Example: "Mahomes breaks own single-season passing record with 4,847 yards"

\- Exclusion: Do not include single-game records in this category; they belong in Tier 2.4



\*\*1c. Major Upsets \& Dominant Blowouts\*\* (merged, equal weight)



\- \*\*Upset condition:\*\* Away team has power\_rating >= 50 (bottom half) and beats opponent with power\_rating <= 25 (top quarter), OR losing-record team (losing %) beats winning team with top-3 record in conference

\- \*\*Blowout condition:\*\* Margin of victory >= 21 points (any team)

\- Data required: game result, both teams' power\_rating, records, final score

\- Examples: "3-win Jets shock unbeaten Ravens in OT" / "49ers crush Texans 52-14"



\#\#\# 12.2.2 Tier 2 — High Priority (if Tier 1 slots filled)



Events in Tier 2 are scanned only after all Tier 1 events are added. If the headline list has fewer than 4 items, Tier 2 events fill remaining slots.



\*\*2a. Statistical Milestones \& Your Team's Notable Performance\*\* (combined, stat milestones prioritized slightly higher)



\- \*\*Stat milestones (higher sub-priority):\*\*

\- Single-game: 300+ passing yards, 150+ rushing yards, 3+ interceptions thrown, 3+ sacks, 10+ tackles, 3+ pass breakups

\- Season threshold: Any player's season total crosses 1,000 yards (passing or rushing) for the first time this season

\- Franchise single-game records (non-season): e.g., most passing yards in a game (season records belong in Tier 1b)

\- Data required: player\_id, stats, season totals, franchise single-game record for position/stat type

\- Examples: "Mahomes posts 412 yards in prime-time win" / "RB Johnson becomes 5th Chief to cross 1,000 rushing yards"



\- \*\*Your team's notable performance (lower sub-priority within Tier 2a):\*\*

\- You win as heavy underdog (power\_rating difference >= 15)

\- You lose as heavy favorite (power\_rating difference >= 15)

\- You score 35+ points (offensive explosive output)

\- You hold opponent to 10 or fewer points (defensive shutout/near-shutout)

\- Data required: your team's power\_rating, opponent's, final score

\- Examples: "Chiefs shock Ravens 24-21 behind late FG" / "Chiefs defense holds Broncos scoreless"



\#\#\# 12.2.3 Tier 3 — Fill-in (if you need more stories to reach 4–5 headlines)



Events in Tier 3 are scanned only if headline list has fewer than 4 items. Rank within tier by secondary criteria (e.g., streak length, injury severity).



\*\*3a. Notable Injuries\*\* (starters only, highest Tier 3 priority)



\- Condition: Player with overall\_rating >= 80 OR listed as depth\_chart starter for position is placed on injury list

\- Data required: player\_id, overall\_rating, position, injury type, expected return week

\- Example: "Ravens' star safety ruled out for season with knee injury"



\*\*3b. Close Games / Dramatic Finishes\*\* (one-score margin or comebacks)



\- Condition: Final margin <= 3 points, OR team trails by 14+ at any half and wins

\- Data required: game result, score\_by\_quarter for both teams

\- Example: "Cowboys stun Eagles in OT after trailing 20-3 at halftime"



\*\*3c. Win/Loss Streaks\*\* (round numbers only)



\- Condition: Team reaches 5, 7, or 10-game win or losing streak

\- Data required: team's record, recent game results

\- Example: "Steelers snap 5-game losing streak with win over Ravens"



\#\# 12.3 Event Scoring \& Candidate Selection Algorithm



\*(Pending — not yet specified. Brian's source paste ended at this heading; fill in the scoring/selection algorithm detail here before this section is implemented.)\*

