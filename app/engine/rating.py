from dataclasses import dataclass

@dataclass(frozen=True)
class TeamRatings:
    offense: float   # 0..100
    defense: float   # 0..100
    special: float   # 0..100
    run_bias: float  # 0..1  (0 pass-heavy, 1 run-heavy)
    aggression: float  # 0..1 (4th-down, deep shots)
    pace: float        # drives per game baseline (0..1 maps to ~20..30)

    def pace_drives(self) -> int:
        # 0 -> 20 drives total (10 per team), 1 -> 30 drives total
        return int(20 + self.pace * 10)
