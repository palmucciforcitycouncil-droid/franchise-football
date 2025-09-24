\# Score Fidelity System (SFS) — Season-Level Normalization (MVP → R2)



\## Goal (plain language)

Make simulated scoring “look like NFL” at the \*\*season\*\* level without hand-rigging individual games. We calibrate the engine using league targets (points per game, TD/FG mix, quarter shares, etc.) computed from recent real seasons.



\## Inputs (data → targets)

\- Real NFL PBP-derived KPIs over a chosen window (default: last 3 seasons).

\- Derived targets we store at `data/model/calibration/season\_{YEAR}\_baselines.json` (later).

\- Targets include: mean/stdev points per team per game, one-score rate (≤8), shutout/blowout rates, TD:FG ratio, red-zone TD rate, PAT make %, 2-pt attempt/make %, FG make % by distance buckets, turnover rate, plays per game (pace), quarter scoring shares, and an EP (expected points) curve by starting field position.



\## Engine knobs we allow to move (bounded)

\- `pace\_factor` (drives/plays per game)

\- `red\_zone\_td\_bias` (TD vs FG inside RZ)

\- `fg\_make\_bias\_by\_bucket` (0–39 / 40–49 / 50+)

\- `pat\_make\_bias`, `two\_point\_attempt\_bias`, `two\_point\_make\_bias`

\- `turnover\_bias`

\- `quarter\_shape` (Q1..Q4 intensity multipliers or Dirichlet α)



\## Calibration loop (MVP — season-level only)

1\. Preseason: compute targets; initialize knobs to 1.0 (neutral).

2\. Sim a league slate (e.g., 10–25 weeks) with a fixed seed.

3\. Measure error vs targets. If any KPI outside tolerance:

&nbsp;  - Adjust the related knob(s) by a tiny percentage (±0.5–1.5% typical).

&nbsp;  - Repeat slate → measure → adjust.

4\. Stop when all tolerances are met or a max iteration budget is hit (fail CI if not met).



\## Tolerances (default — reviewed each release)

\- Points per team mean: ±5%

\- One-score game rate: ±3 percentage points

\- TD:FG ratio: ±5%

\- Quarter scoring shares: ±3 percentage points each

\- Plays per game: ±3%



\## Optional R2 “per-game nudger” (strict guardrails)

\- At most \*\*one\*\* flip per team per game from a pre-tagged safe list (e.g., 45–49 yd FG make↔miss, RZ TD↔FG, XP make↔miss, 2-pt fail↔make).

\- No contradictions (clock/field/sequence). Each flip is logged to a `ReconciliationEvent` and the game is marked `reconciled = true`.

\- Goal is to pull \*\*season aggregates\*\* toward targets, not to rewrite box scores.



\## Outputs \& reporting

\- Live KPIs after each iteration: `data\\reports\\season\_kpis\_{YEAR}.parquet`

\- Optional R2 audit: `data\\reports\\reconciliation\_events\_{YEAR}.parquet`

\- UI: a small “Calibration: ON” badge with a tooltip explaining season-level normalization.



\## Determinism

\- All sims and adjustments are seedable. CI runs the same seed to detect regressions.



\## Assumptions (MVP)

\- No weather; no special home-field beyond what the engine already models.

\- Team strength differences come from roster/OVR; coaches/schemes layer in later.



\## Changelog

\- v2.17.3 — Added Score Fidelity System spec (MVP → R2), league targets, tolerances, and optional per-game nudger rules.



