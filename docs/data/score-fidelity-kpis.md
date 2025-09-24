\# Score Fidelity — KPIs \& Data Checklist



\## KPI targets (computed from recent NFL seasons)

\- Points per team per game (mean, stdev)

\- One-score game rate (margin ≤ 8)

\- Shutout \& blowout rates (≥17)

\- TD:FG ratio, Red-zone (RZ) TD rate

\- PAT make %, 2-pt attempt %, 2-pt make %

\- FG make % by distance bands (0–39, 40–49, 50+)

\- Turnover rate

\- Plays per game (pace)

\- Quarter scoring shares (Q1–Q4; OT separate)

\- EP curve by starting field position



\## Source data → recommended outputs

\- `data\\reports\\pbp\_kpis\_extended.csv` (season rollup incl. playtype priors \& scoring knobs)

\- `data\\reports\\scoring\_by\_quarter.csv` (points by quarter including OT)

\- `data\\reports\\playtype\_by\_season.csv` (pass/run/punt/FG/kickoff %)

\- `data\\reports\\team\_offense\_epa\_top10\_{YEAR}.csv` (strength anchors)



\## Readiness checklist (before calibration)

\- \[ ] All four CSVs exist for the target season window

\- \[ ] No nulls in key KPI columns

\- \[ ] Distances binned; quarter mapping verified

\- \[ ] Seeds recorded for any stochastic ETL steps



