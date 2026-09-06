from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class GuardrailLog:
    nudge_events: int = 0
    last_delta: float = 0.0

    def record(self, delta: float):
        self.nudge_events += 1
        self.last_delta = delta
