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
        # Real NFL averages ~11 drives per team per game (~22 total);
        # this used to run 0 -> 20 total (10/team), 1 -> 30 total
        # (15/team) -- at the real pace-rating distribution's ~0.5
        # average (placeholder_ratings.py's uniform(0.3, 0.75)), that
        # put total offensive-play volume (drives x real plays/drive)
        # ~18% over real per-game rates, part of what inflated every
        # counting stat (yards, TDs, tackles) in this engine's
        # stat-realism audit (HANDOFF.md item 36). Rescaled to 0 ->
        # 19 total (9.5/team), 1 -> 23.5 total (11.75/team).
        return int(19 + self.pace * 4.5)
