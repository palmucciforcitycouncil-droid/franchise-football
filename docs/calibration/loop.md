\# Calibration Loop — Operator’s Guide



\## Overview

We auto-tune a small set of engine knobs so season-level KPIs match real NFL targets. This loop runs offline (not during a single game) and is deterministic (fixed seed).



\## Steps

1\. \*\*Load Targets\*\*: Read the current season’s targets bundle (KPIs) from data.

2\. \*\*Initialize Knobs\*\*: Start from neutral (1.0) or last known good values.

3\. \*\*Sim a Slate\*\*: Run N weeks of the league (e.g., 10–25) with a fixed seed.

4\. \*\*Measure Errors\*\*: Compute KPI deltas (observed vs target).

5\. \*\*Adjust Knobs\*\*: Apply tiny proportional nudges to relevant knobs. Keep within bounds (e.g., 0.90–1.10).

6\. \*\*Check Tolerances\*\*: If all KPIs are in tolerance, stop and persist results.

7\. \*\*Iterate\*\*: Otherwise, go back to step 3 up to a max iterations cap (e.g., 12).



\## Guardrails

\- Discrete scoring only ({2,3,6,7,8} building blocks); no impossible totals.

\- No per-play edits in MVP; per-game R2 flips capped at 1/team/game with audit.

\- Never degrade variance to arcade-flat outcomes; preserve stdev target.



\## Persistence

\- Save per-iteration KPI snapshots to `data\\reports\\season\_kpis\_{YEAR}.parquet`.

\- Save final knob set to `data\\model\\calibration\\season\_{YEAR}\_knobs.json` (later).



\## CI Acceptance

\- Batch sim with DEFAULT\_SEED=2025; assert KPI tolerances.

\- Fail if we hit max iterations without meeting tolerances.



