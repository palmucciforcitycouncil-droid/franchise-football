from __future__ import annotations
from dataclasses import dataclass
from app.config_sim_calibration import bands, safety

@dataclass
class LiveMetrics:
    total_yards: int = 0
    total_points: int = 0
    punts: int = 0
    fg_attempts: int = 0
    sacks: int = 0

@dataclass
class Nudge:
    logit_delta: float = 0.0  # additive on success logits

class SafetyController:
    def __init__(self):
        self.active = False
        self.last_nudge = Nudge(0.0)

    def evaluate(self, quarter: int, lm: LiveMetrics)->Nudge:
        if not safety.ENABLE or quarter < safety.START_QUARTER:
            self.active = False
            self.last_nudge = Nudge(0.0)
            return self.last_nudge

        # Trigger only if exceeding bands (hard bounds)
        trigger = False
        delta = 0.0

        if lm.total_yards > bands.YARDS_MAX or lm.total_points > bands.POINTS_MAX or lm.fg_attempts < bands.FG_ATT_MIN:
            # too offensive → slightly reduce success logits
            trigger = True
            delta = -safety.MAX_LOGIT_NUDGE
        if lm.total_yards < bands.YARDS_MIN or lm.total_points < bands.POINTS_MIN or lm.punts > bands.PUNTS_MAX:
            # too defensive → slightly increase success logits
            trigger = True
            delta = +safety.MAX_LOGIT_NUDGE

        if not trigger:
            self.active = False
            self.last_nudge = Nudge(0.0)
            return self.last_nudge

        self.active = True
        # one small nudge only; caller applies to pass/run success logits as a tiny additive before sigmoid
        self.last_nudge = Nudge(delta)
        return self.last_nudge
