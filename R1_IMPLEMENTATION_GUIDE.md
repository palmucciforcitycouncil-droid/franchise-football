# R1: Injury System — Detailed Implementation Guide

**Status:** M1-M6 complete. Ready to begin R1.

---

## Phase 0: Pre-Coding Testing & Verification (THIS SESSION)

**Do this BEFORE starting any coding in a new session.**

### 1. Live Testing Checklist
Run through the dev server (already up) to verify M1-M6 are solid:

- [ ] **Roster page M4**: 
  - [ ] Attributes view shows player attributes (SPD/STR/AGI/AWR/STA)
  - [ ] Stats view shows games/Pass/Rush/Rec/Def columns
  - [ ] Team Quota badges display with correct colors
  - [ ] View toggle works
  
- [ ] **Stats page M3**: 
  - [ ] Player/Team/Coach tabs work
  - [ ] Column customizer opens/closes
  - [ ] Sorting by column works
  
- [ ] **HOF page M5**: 
  - [ ] "Class of Inductees" shows correctly
  - [ ] Hall of Fame Members list displays
  - [ ] League Record Book shows top-10 leaders
  
- [ ] **Player Card M6**:
  - [ ] Stats tab shows career stats (if seasons archived)
  - [ ] Overview/Ratings tabs populate correctly
  
- [ ] **Core M1-M2**: 
  - [ ] Simulate a week, verify defensive TD credit appears
  - [ ] Check box scores show kicking/punting lines

### 2. Test Suite Verification
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```
Should show: **247 passed, 1 skipped** (or better)

### 3. Git Status Clean
```
git status
# Should show: "nothing to commit, working tree clean"
```

---

## What R1 Actually Does (Architecture Overview)

**Goal:** Players can get injured during games, affecting rotation and stats.

**Key Integration Points:**
1. **When**: During `simulate_drive()` — on any play, a check for injury (tied to player durability)
2. **What**: Player marked as injured for rest of game (or season?)
3. **How**: Backup automatically takes over (rotation.py already supports this)
4. **Track**: Box scores show which players were injured, games played
5. **Persist**: Save injury state to season_state so it carries across weeks

**No new UI yet.** This is pure engine work.

---

## R1 Broken Into 4 Sub-Chunks

### R1a: Design & Architecture (Design Session — Opus — 1-2 hours)
**Purpose:** Nail down injury system design before writing code.

**Deliverable:** Detailed design document (no code yet)

**What to Design:**
- When do injuries happen? (per play? per drive? per game?)
- Injury probability formula (tied to `durability` attribute)
- Injury types (severity levels? duration?)
- How does backup rotation increase?
- What gets saved to season_state?
- Where in game_sim/drive_sim flow?

**Prompt Template for R1a (Opus):**
```
Read HANDOFF.md and ROADMAP.md. Design R1a: Injury System Architecture.

Context: M1-M6 complete. You're designing (not implementing) the injury system.
The goal is to tie in-game injuries to player durability, auto-increase backup rotation.

Key constraints:
- Injuries should tie to player durability (0-99 Madden attribute)
- When a starter is injured, backup should auto-increase snaps/touches
- rotation.py (item 37) already supports variable reliability_factor
- No new UI in MVP scope — just engine work
- Must not corrupt existing stat tracking

Design only — no code. Document:
1. Injury trigger points (which code calls check for injury?)
2. Probability model (what formula? tied to what factors?)
3. Injury types/severity (single type or graduated?)
4. Duration (rest of game? whole season? recovery timeline?)
5. Backup rotation integration (how does reliability_factor increase?)
6. State persistence (what gets saved to season_state?)
7. Box score / stats tracking (new fields or reuse existing?)

Deliverable: Design doc (markdown) explaining each decision and why.
```

**Success Criteria:**
- [ ] Clear injury trigger points identified
- [ ] Probability formula defined
- [ ] Backup auto-increase mechanism explained
- [ ] Season-state persistence plan clear
- [ ] No ambiguity in flow

---

### R1b: Core Injury System in Game Sim (Implementation — Sonnet — 2-3 hours)

**Deliverable:** Injury events fire during drives, Player marked as injured, stats track it

**Key Files to Modify:**
- `app/engine/game_state.py` — add injury state tracking
- `app/engine/drive_sim.py` — add injury check, injury probability function
- `app/services/season_state.py` — persist injuries week-to-week
- Tests: `tests/test_drive_sim.py`, `tests/test_game_sim.py`

**What R1b Does:**
1. Add injury check to `simulate_drive()` (every play or every drive?)
2. Create `_injury_probability()` function in `drive_sim.py`
3. Track injured players in game state
4. Verify box scores don't break when a player is injured mid-game
5. Run full test suite twice (engine work per ROADMAP.md §5.4)

**Prompt Template for R1b (Sonnet):**
```
Read HANDOFF.md and ROADMAP.md. Implement chunk R1b: Injury System Core Engine.

Context: R1a design complete. You're implementing the core injury mechanics.
Key files: app/engine/game_state.py, drive_sim.py, season_state.py, tests.

R1a Design decisions (copy from R1a output):
[Paste R1a design decisions here — trigger points, probability, duration, etc.]

Scope (R1b only):
1. Add injury event triggering in simulate_drive() per R1a design
2. Create _injury_probability() function tied to player durability
3. Track injured players in GameState 
4. Update box_score.py to handle injured players (games_played calc)
5. Persist injuries to season_state across weeks
6. Do NOT integrate with rotation.py yet (that's R1c)
7. Do NOT update UI (no new templates)

Key constraint: Don't break existing tests. Run suite twice before committing.

Implementation approach:
- Reuse PlayEvent for injury events? Or new injury tracking?
- Use existing Player.durability directly
- Keep changes minimal — only what R1b needs

Files touched: game_state.py, drive_sim.py, season_state.py, box_score.py, game_sim.py, plus test updates.
```

**Success Criteria:**
- [ ] Injuries fire during games (testable with a deterministic seed)
- [ ] Box scores correctly count games played for injured players
- [ ] Injuries persist across weeks
- [ ] Full test suite passes (247+ passed, 1 skipped) run twice
- [ ] No stat corruption

---

### R1c: Rotation Integration (Implementation — Sonnet — 1.5-2 hours)

**Deliverable:** When a starter is injured, backup's touches/snaps auto-increase

**Key Files:**
- `app/engine/rotation.py` (item 37's work) — modify reliability_factor or backup-selection logic
- `app/services/depth_chart.py` — how backups are selected
- `app/engine/drive_sim.py`, `player_ai.py` — use updated rotation
- Tests: `tests/test_rotation.py` (new)

**What R1c Does:**
1. When starter is injured, increase backup's reliability_factor or equivalent
2. Verify backup gets selected for remaining plays that game
3. Box score shows backup carries/receptions/etc, not injured starter
4. Test: starter injured in Q1, backup leads team in touches by Q4

**Prompt Template for R1c (Sonnet):**
```
Read HANDOFF.md and ROADMAP.md. Implement chunk R1c: Rotation Integration.

Context: R1b (core injury system) complete. You're integrating injuries with rotation.py.

R1b assumed injuries exist (from previous chunk). Now wire them to rotation.

Scope (R1c only):
1. Modify rotation.py to increase backup reliability_factor when starter is injured
2. Ensure backup-selection logic (choose_ball_carrier, choose_pass_target, etc.) uses updated rotation
3. Verify box scores credit backup, not injured starter
4. Test: full game with a starter injured in Q1, verify backup dominates stats
5. Run full test suite twice

Key files: rotation.py, depth_chart.py, drive_sim.py, player_ai.py, box_score.py.

Constraint: Rotation already works (item 37). Don't redesign it — just wire in injury signal.
```

**Success Criteria:**
- [ ] Backup gets increased snap share when starter injured
- [ ] Box score correctly attributes stats to backup
- [ ] Full test suite passes twice
- [ ] Live test: simulate game, injure starter, verify backup stats increase

---

### R1d: Testing & Integration (QA — Sonnet — 1-2 hours)

**Deliverable:** Comprehensive injury testing, edge cases, live verification

**What R1d Does:**
1. Write integration tests for full injury flow (R1b + R1c together)
2. Test edge cases: multiple injuries same game, backups-of-backups, injury probability calibration
3. Live browser test: simulate full season with injuries, check stats realism
4. Update HANDOFF.md with R1 summary
5. Run full test suite multiple times, verify no regressions

**Prompt Template for R1d (Sonnet):**
```
Read HANDOFF.md and ROADMAP.md. Implement chunk R1d: Injury System Testing & Integration.

Context: R1a (design), R1b (core engine), R1c (rotation) all complete.
You're doing final QA and integration testing.

Scope (R1d only):
1. Write comprehensive integration tests in test_drive_sim.py/test_game_sim.py:
   - Injury probability increases with lower durability
   - Backup reliably takes over when starter injured
   - Stats attributed correctly
   - Multiple injuries same game handled
   - Backup-of-backup scenarios (if starter injured, backup injured, 3rd string takes over)

2. Edge cases:
   - What happens if all players at a position get injured? (should have 3rd/4th string available per rotation.py)
   - Injury at rare position (K/P) — handled gracefully?
   - Injury in last play of game vs first play

3. Live testing (via browser):
   - Simulate full season, verify injury frequency looks reasonable
   - Check no unexpected stat spikes or stat corruption
   - Verify roster/depth-chart pages show correct games-played for injured players

4. Stat realism check:
   - Run test_stat_realism.py, verify no new outliers

5. Run full test suite 3+ times. Should see 247+ passed, 1 skipped consistently.

Deliverable: New tests, all passing, no stat corruption.
```

**Success Criteria:**
- [ ] All R1-specific tests pass
- [ ] Full test suite passes 247+/1 at least 3 times
- [ ] Live season sim runs smoothly with injuries
- [ ] No stat outliers or corruption
- [ ] HANDOFF.md updated with R1 session notes

---

## Testing Strategy & Workflow

### When to Test (By Phase)

**Before R1a starts:**
- ✅ Already done above (Phase 0)

**After R1b (core injury system):**
1. Run full test suite twice (engine work rule)
2. Add injury event for one specific player, verify it fires
3. Check box_score.py doesn't crash with injured players
4. Don't test rotation yet (R1c does that)

**After R1c (rotation integration):**
1. Run full test suite twice
2. Live test: simulate game, injure a starter in Q1
3. Verify backup gets 3+ carries/targets rest of game
4. Check box score attributes stats correctly

**After R1d (full integration):**
1. Run full test suite 3+ times
2. Live test: simulate 2+ week season with multiple injury events
3. Check stats don't show corruption
4. Compare injury rate across 5 simulated seasons (should be similar each time, not random)

### Test Tools

```powershell
# Full suite (takes ~7 minutes)
.\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short

# Quick check (just game-related tests)
.\.venv\Scripts\python.exe -m pytest tests/test_drive_sim.py tests/test_game_sim.py tests/test_box_score.py -v

# Run twice (per ROADMAP.md §5.4 for engine work)
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short; .\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short
```

---

## Concurrency Rules for R1

### ✅ Can Run Concurrently (Safe)
- R1a design + any other session doing UI work (M-series style)
- R1b + R1c if they touch completely different files (unlikely — they both touch rotation/drive_sim)
- R1 + R6/R7 (small, independent chunks)

### ❌ Do NOT Run Concurrently (Will Conflict)
- R1b + R1c (both modify drive_sim.py, player_ai.py, rotation.py)
- R1a + R1b (R1b needs R1a design first)
- Any R1 chunk + R2 (R2 depends on R1 being complete and stable)
- Any R1 chunk + R4/R5 (ROADMAP.md says R1 must complete first — "it'll change how those get built")

### Best Practice
**Run R1 linearly: R1a → R1b → R1c → R1d, no concurrency.**

If running other sessions in parallel:
- R1a can run with UI work (M-series) in parallel
- After R1a complete, others can do R6/R7 while you wait for R1b
- Keep R1b/c/d strictly sequential

---

## Commit Messages Template

After each R1 sub-chunk, use this format:

```
Build Injury System phase X/4 (ROADMAP.md R1X)

[Paragraph describing what this phase does]

Key files touched: [list]
Test results: NNN passed, 1 skipped
Dependencies: [what R1 sub-chunks must happen before this]

Co-Authored-By: Claude [Model] <noreply@anthropic.com>
```

---

## Post-R1 Checklist

Once all R1a/b/c/d complete:

- [ ] All 4 sub-chunks committed and pushed
- [ ] Full test suite passes 247+ / 1 skipped (run 3 times)
- [ ] No live game stat corruption observed
- [ ] HANDOFF.md updated with R1 session notes
- [ ] ROADMAP.md shows R1 complete
- [ ] R2/R3 ready to start (R1 is blocking dependency for them)

---

## Git Workflow Per Sub-Chunk

```bash
# After R1a design (save as doc, commit separately or just reference in R1b)
# After R1b implementation
git add app/engine/drive_sim.py app/engine/game_state.py app/services/season_state.py app/engine/box_score.py tests/test_drive_sim.py
git commit -m "Build Injury System core engine (ROADMAP.md R1b)..."
git push

# After R1c rotation integration
git add app/engine/rotation.py app/services/depth_chart.py tests/test_rotation.py
git commit -m "Build Injury System rotation integration (ROADMAP.md R1c)..."
git push

# After R1d testing
git add tests/test_drive_sim.py tests/test_game_sim.py docs/HANDOFF.md
git commit -m "Build Injury System testing & integration (ROADMAP.md R1d)..."
git push
```

---

## Next Steps (After R1 Complete)

1. **R2 (Return-game)**: Can start, but R1 must ship first
2. **R3 (Coaching)**: Independent, can run in parallel with R2
3. **R4a (Contracts)**: Depends on R1/R2 being stable (R4 is biggest chunk)

**Recommended next:** Start R1a design session now. After R1a, you'll know if any design issues need pre-thought before R1b coding begins.
