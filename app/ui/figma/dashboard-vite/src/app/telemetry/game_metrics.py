from __future__ import annotations
from dataclasses import dataclass

@dataclass
class GameMetrics:
    total_yards: int = 0
    total_points: int = 0
    punts: int = 0
    fg_attempts: int = 0
    sacks: int = 0

    def as_live(self):
        from app.engine.safety_controller import LiveMetrics
        return LiveMetrics(
            total_yards=self.total_yards,
            total_points=self.total_points,
            punts=self.punts,
            fg_attempts=self.fg_attempts,
            sacks=self.sacks
        )
