"""
Score Fidelity System (GDD Part 1 Sec 6.2) -- keeps simulated league-wide
scoring aligned with modern NFL averages while preserving per-game
unpredictability, per the GDD's stated design goal.

This engine derives outcomes bottom-up from real player attributes
(app/engine/player_ai.py, drive_sim.py's per-play resolution), not the
GDD's assumed top-down architecture of "convert an EP target into an
abstracted per-drive TD/FG/Punt/TO probability table." There is no such
abstracted table here -- replacing the per-play engine with one would
undo the player-level AI, defensive AI, and box-score work already
built. So EP anchoring is implemented as a small, BOUNDED per-game
scoring multiplier layered on top of the existing formulas (the real
injection point: MatchupContext.ep_multiplier, read by
drive_sim._resolve_pass/_resolve_run to nudge completion odds and
yardage), not a wholesale replacement of how a play's outcome is
decided.

Real, deliberate scope cuts from the full Sec 6.2 spec (documented here,
not silently dropped):
- No true per-quarter EP/Dirichlet quarter-share tracking -- the engine
  has no quarter/clock model (just a two-minute-drill proxy), so the
  Dirichlet draw's "realistic variance" role is approximated by one
  per-game noise draw instead of four per-quarter draws.
- Sec 6.2.3's EP_team formula also has pace_factor and strength_factor
  terms, both omitted here -- both are already modeled directly by the
  existing engine (TeamRatings.pace controls drives/game; real
  player-attribute matchups already drive scoring efficiency), so
  including them again in this multiplier would double-count them.
- No Red Zone Module (logistic RZ-TD% correction) or endgame PAT-decision
  model (Sec 6.2.5) -- both need real telemetry on red-zone trip rate /
  2-point decision frequency this engine doesn't track yet.
- Weekly feedback only closes the loop on the GDD's single strictest,
  most measurable target (Sec 6.2.4's season/rolling-mean PPG error) --
  the GDD's own weekly_feedback_update pseudocode references
  GSM/PN/QBM/MIX multipliers and k_ppg/k_pace/k_q/K_mix constants with
  no formulas given for how they're derived from telemetry; only the
  PPG piece (GSM, effectively) is concrete enough to implement
  faithfully rather than guessed at.
- No formal +/-0.7 / +/-1.0 / +/-10% / +/-2pp tolerance-enforcement
  harness -- verified empirically instead (re-measuring actual output
  across a full season), the same way this project's original
  hand-tuned calibration pass was verified.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from app.engine.rng import RNG

TARGET_PPG_PER_TEAM = 22.0        # modern NFL average -- matches this project's own prior calibration target
WIN_PROB_SCALE = 0.25             # bounds the win-probability-driven swing
HOME_COMPONENT = 0.02             # small home-scoring edge, distinct from Elo's HFA (which shapes win prob, not scoring efficiency)
GAME_VARIANCE_SIGMA = 0.05        # per-game noise draw -- stand-in for true per-quarter Dirichlet variance (see module docstring)
MULTIPLIER_CLAMP = (0.80, 1.20)   # keeps EP anchoring a nudge, not a rewrite of the underlying player-attribute engine

FEEDBACK_LEARNING_RATE = 0.01     # how hard one week's PPG error moves the multiplier, before damping
FEEDBACK_WEEKLY_CAP = 0.02        # max multiplier change from a single week, pre-damping
FEEDBACK_EMA_ALPHA = 0.35         # GDD's own stated damping factor (Sec 6.2.5 pseudocode: "EMA damping alpha≈0.35")
FEEDBACK_CLAMP = (0.85, 1.15)


@dataclass
class SFSState:
    """Persisted alongside Season (app/services/season_state.py) -- the
    weekly feedback loop's only piece of durable state, plus a telemetry
    log so the correction is inspectable after the fact, not just a
    number that silently drifts."""
    scoring_feedback_multiplier: float = 1.0
    telemetry: list[dict] = field(default_factory=list)


def ep_multiplier(rng: RNG, home_win_prob: float, is_home: bool, feedback_multiplier: float) -> float:
    """Sec 6.2.3's EP_team formula, adapted -- see module docstring for
    what's included/omitted and why. Returns a bounded scoring multiplier
    for one team in one game. `rng` must be the same seeded RNG the game
    itself uses (not an uncontrolled random source), so a season replay
    with the same LEAGUE_SEED stays fully deterministic."""
    win_prob_for_team = home_win_prob if is_home else (1.0 - home_win_prob)
    win_prob_modifier = 1.0 + (win_prob_for_team - 0.5) * WIN_PROB_SCALE
    home_component = HOME_COMPONENT if is_home else 0.0
    game_noise = rng.gauss(1.0, GAME_VARIANCE_SIGMA)
    raw = (1.0 + home_component) * win_prob_modifier * game_noise * feedback_multiplier
    lo, hi = MULTIPLIER_CLAMP
    return max(lo, min(hi, raw))


def weekly_feedback_update(sfs: SFSState, week_num: int, measured_ppg_this_week: float) -> None:
    """Sec 6.2.5's weekly_feedback_update, scoped to the PPG (GSM) term
    only -- see module docstring. Mutates `sfs` in place (multiplier +
    telemetry append), matching season_state.py's existing
    mutate-then-save pattern for Season/TeamRecord."""
    error = measured_ppg_this_week - TARGET_PPG_PER_TEAM
    raw_delta = -FEEDBACK_LEARNING_RATE * error
    capped_delta = max(-FEEDBACK_WEEKLY_CAP, min(FEEDBACK_WEEKLY_CAP, raw_delta))
    candidate = sfs.scoring_feedback_multiplier + capped_delta
    damped = FEEDBACK_EMA_ALPHA * candidate + (1 - FEEDBACK_EMA_ALPHA) * sfs.scoring_feedback_multiplier
    lo, hi = FEEDBACK_CLAMP
    new_multiplier = max(lo, min(hi, damped))

    sfs.telemetry.append({
        "week": week_num,
        "measured_ppg": round(measured_ppg_this_week, 2),
        "target_ppg": TARGET_PPG_PER_TEAM,
        "error": round(error, 2),
        "multiplier_before": round(sfs.scoring_feedback_multiplier, 4),
        "multiplier_after": round(new_multiplier, 4),
    })
    sfs.scoring_feedback_multiplier = new_multiplier
