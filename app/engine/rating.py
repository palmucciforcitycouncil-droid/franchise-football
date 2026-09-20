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
        # Real NFL averages ~11 drives per team per game (~22 total) at
        # ~5.6-6 real plays/drive, for ~63-65 total offensive snaps/team.
        # The 19->23.5 (9.5/team -> 11.75/team) scaling this function
        # used to return was already close to real DRIVE count, but this
        # engine's down-by-down mechanics run longer per drive than real
        # (~7.1-7.4 plays/drive, measured) -- there's no direct "plays
        # per drive" knob (it's emergent from the yardage/conversion-rate
        # model, not something this function controls), so hitting the
        # real total-plays/team target means undershooting real drive
        # COUNT to compensate for overshooting real plays-PER-drive, a
        # real (disclosed) tradeoff, not an attempt to match real
        # drives/game independently. Re-measured with the reproduction
        # methodology in the sim-realism investigation (200 games/team,
        # two average 70/70/70-pace-0.5 teams): baseline was 74.6 total
        # plays/team/game at the previous 19->23.5 scaling (a QB
        # finished a season at 878 pass attempts vs. real full-season
        # starters' ~500-600). Rescaled to 0 -> 16 total (8/team), 1 ->
        # 20 total (10/team), landing baseline total plays/team back in
        # the real ~63-65 band -- see tests/test_stat_realism.py's
        # team-level plays/game and yards/game checks, which guard this
        # going forward.
        return int(16 + self.pace * 4)
