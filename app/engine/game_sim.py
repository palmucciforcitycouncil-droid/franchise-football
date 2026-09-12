from dataclasses import dataclass
from typing import List
from .rng import RNG
from .rating import TeamRatings
from .game_state import DriveEvent, GameResult, PlayEvent
from .drive_sim import simulate_drive, _kicker_adjusted_prob
from .tuning import DRIVE_SIM_PARAMS as P
from .player_ai import build_matchup_context
from .defensive_ai import LEAGUE_AVG_YPC, LEAGUE_AVG_YPA
from .gameplan import Gameplan
from . import coaching
from .coaching import StaffEffect
from . import special_teams
from app.services.depth_chart import get_offensive_starters, get_defensive_starters, OffensiveStarters

@dataclass
class TeamSim:
    name: str
    abbr: str
    ratings: TeamRatings

@dataclass
class TeamTotals:
    points: int = 0
    plays: int = 0
    yards: int = 0
    pass_yards: int = 0
    rush_yards: int = 0
    pass_attempts: int = 0
    rush_attempts: int = 0
    turnovers: int = 0

    def ypc(self) -> float:
        return self.rush_yards / self.rush_attempts if self.rush_attempts else LEAGUE_AVG_YPC

    def ypa(self) -> float:
        return self.pass_yards / self.pass_attempts if self.pass_attempts else LEAGUE_AVG_YPA


def _resolve_kickoff(
    rng: RNG, kicker_is_home: bool, home: TeamSim, away: TeamSim, h: int, a: int, drives_left: int,
    home_off_starters: OffensiveStarters, away_off_starters: OffensiveStarters,
    is_two_minute: bool, allow_onside: bool,
    home_staff: StaffEffect | None = None, away_staff: StaffEffect | None = None,
) -> tuple[int, bool, int, int, List[PlayEvent]]:
    """Kickoffs (GDD Sec 6.8, app/engine/special_teams.py) -- resolved
    here, not in drive_sim.py, since a kickoff happens BETWEEN drives
    (possibly deciding who even gets the next one, via an onside kick),
    not down-by-down within one. Returns (new_field_pos, receiver_is_home,
    h_delta, a_delta, kickoff_play_events). receiver_is_home is normally
    `not kicker_is_home` -- it can equal `kicker_is_home` instead only
    when an onside kick is recovered by the team that just kicked it.
    h_delta/a_delta are nonzero only on the rare kickoff-return
    touchdown, which scores immediately with no snap ever run."""
    kicker_trailing = (h < a) if kicker_is_home else (a < h)
    receiver_is_home = not kicker_is_home
    events: List[PlayEvent] = []

    strategy = special_teams.decide_kickoff_strategy(kicker_trailing, drives_left, rng) if allow_onside else "normal"
    if strategy == "onside":
        recovered, spot = special_teams.onside_kick_result(rng)
        desc = "Onside kick recovered by the kicking team!" if recovered else "Onside kick recovered by the receiving team"
        events.append(PlayEvent(0, 0, 0, "onside_kick", 0, desc, "recovered" if recovered else "turnover"))
        return spot, (kicker_is_home if recovered else receiver_is_home), 0, 0, events

    receiving_starters = home_off_starters if receiver_is_home else away_off_starters
    kres = special_teams.kickoff_result(rng, receiving_starters)
    events.append(PlayEvent(0, 0, 0, "kickoff", kres.return_yards, kres.desc, kres.kind, returner_name=kres.returner_name))
    if kres.kind != "return_td":
        return kres.new_pos, receiver_is_home, 0, 0, events

    # Kickoff return TD (rare, special_teams.RETURN_TD_MAX_PROB caps it
    # low) -- the RECEIVING team scores immediately, no snap ever run.
    # PAT/2-point decided the same way drive_sim.py's simulate_drive
    # decides one after an offensive-drive TD, using the receiving team's
    # own kicker. The kickoff THAT this score's ensuing possession would
    # need is deliberately not itself re-simulated (a disclosed, bounded
    # simplification against a freak double-return-TD chain) -- it starts
    # at a plain touchback spot instead, same as this project's existing
    # "some real sequences stay simplified, not fabricated" precedent.
    receiver = home if receiver_is_home else away
    receiver_kicker = receiving_starters.k
    receiver_trailing = (h < a) if receiver_is_home else (a < h)
    receiver_staff = home_staff if receiver_is_home else away_staff
    if special_teams.decide_pat_or_two(
            receiver_trailing, is_two_minute, receiver.ratings.aggression, rng,
            two_point_bias=coaching.offense_two_point_bias(receiver_staff)) == "two_point":
        made_two = special_teams.two_point_attempt(rng)
        pts = 8 if made_two else 6
        events.append(PlayEvent(0, 0, 0, "two_point", 0,
                                 "Two-point conversion is GOOD" if made_two else "Two-point conversion FAILED",
                                 "gain" if made_two else "turnover"))
    else:
        made_pat = rng.prob(_kicker_adjusted_prob(P.pat_make, receiver_kicker))
        pts = 7 if made_pat else 6
        events.append(PlayEvent(0, 0, 0, "extra_point", 0,
                                 "Extra point is GOOD" if made_pat else "Extra point is NO GOOD",
                                 "field_goal" if made_pat else "turnover"))
    h_delta = pts if receiver_is_home else 0
    a_delta = pts if not receiver_is_home else 0
    return 25, kicker_is_home, h_delta, a_delta, events


def simulate_game(
    rng: RNG, home: TeamSim, away: TeamSim,
    home_ep_multiplier: float = 1.0, away_ep_multiplier: float = 1.0,
    home_gameplan: Gameplan | None = None, away_gameplan: Gameplan | None = None,
    home_staff: StaffEffect | None = None, away_staff: StaffEffect | None = None,
) -> GameResult:
    """home_ep_multiplier/away_ep_multiplier: the Score Fidelity System's
    (app/engine/score_fidelity.py) per-game scoring nudge, computed from
    Team Power Ratings by whoever has season context (season_state.py).
    Default 1.0 (no effect) for callers with no season -- e.g. the
    standalone single-game simulator (app/main.py's /simulate route),
    which has no Team Power Rating to derive a multiplier from.

    home_gameplan/away_gameplan: the Weekly Gameplan (GDD Sec 10.4.1) for
    whichever of the two is the user's team -- None (the default) for
    every AI team and for the standalone single-game simulator, which
    has no concept of "the user's team" either.

    home_staff/away_staff: each team's real coaching staff reduced to
    sim biases (app/engine/coaching.py's StaffEffect, GDD Sec 7.7.2).
    Unlike the gameplans these are meaningful for BOTH teams in every
    game -- they're what give each team a distinct play-calling
    identity. None means "no coaching influence at all", which is
    exactly how this engine behaved before the Coach entity existed, so
    callers without a staff (tests, a database with no coaches
    imported) are unaffected. Resolved once here and held for the whole
    game, matching GDD Sec 7.7.3's "Weekly strategy profile (Off + Def +
    ST) locked at kickoff"."""
    drives_total = int((home.ratings.pace_drives() + away.ratings.pace_drives()) / 2)
    home_first = rng.prob(0.5)
    events: List[DriveEvent] = []
    all_plays: List[PlayEvent] = []
    h = a = 0
    htot = TeamTotals(); atot = TeamTotals()

    # Real starters + matchup composites, built once per game (not per
    # drive -- starters don't change mid-game) for both directions of play.
    home_off_starters = get_offensive_starters(home.abbr)
    home_def_starters = get_defensive_starters(home.abbr)
    away_off_starters = get_offensive_starters(away.abbr)
    away_def_starters = get_defensive_starters(away.abbr)
    ctx_home_offense = build_matchup_context(home_off_starters, away_def_starters, home_ep_multiplier)
    ctx_away_offense = build_matchup_context(away_off_starters, home_def_starters, away_ep_multiplier)

    # Opening kickoff (GDD Sec 6.8) -- whoever DIDN'T win the "receive
    # first" coin flip (home_first) kicks it away. Reuses the exact same
    # _resolve_kickoff this loop calls after every scoring drive below,
    # so a freak opening-kickoff return TD is handled identically to any
    # other kickoff-return score (0-0 game, so no onside attempt here --
    # there's no deficit yet to justify one).
    field_pos, next_side_home, opening_h, opening_a, pending_kickoff_events = _resolve_kickoff(
        rng, kicker_is_home=not home_first, home=home, away=away, h=0, a=0, drives_left=drives_total - 1,
        home_off_starters=home_off_starters, away_off_starters=away_off_starters,
        is_two_minute=False, allow_onside=False,
        home_staff=home_staff, away_staff=away_staff,
    )
    h += opening_h
    a += opening_a

    for i in range(drives_total):
        side_home = next_side_home
        off = home if side_home else away
        ctx = ctx_home_offense if side_home else ctx_away_offense

        # rough clock proxy
        drives_left = drives_total - i - 1
        is_two_min = drives_left <= 2
        trailing = (h < a) if side_home else (a < h)
        fourth_ok = (is_two_min or trailing) and off.ratings.aggression >= 0.55

        # In-game offensive performance SO FAR (before this drive) -- the
        # defense's Sec 6.6.3 Step 1 anticipation input. Read from this
        # offense's own running totals, not the defense's -- the defense
        # is reacting to what the offense has actually been doing.
        off_tot = htot if side_home else atot
        offense_gameplan = home_gameplan if side_home else away_gameplan
        defense_gameplan = away_gameplan if side_home else home_gameplan
        offense_staff = home_staff if side_home else away_staff
        defense_staff = away_staff if side_home else home_staff
        pts, txt, next_field_pos, plays, yards, tos, drive_play_events = simulate_drive(
            rng, ctx, off.ratings, field_pos,
            is_two_minute=is_two_min, trailing=trailing, fourth_down_ok=fourth_ok,
            off_ypc=off_tot.ypc(), off_ypa=off_tot.ypa(),
            offense_gameplan=offense_gameplan, defense_gameplan=defense_gameplan,
            offense_staff=offense_staff, defense_staff=defense_staff,
        )

        # The PREVIOUS iteration's kickoff (or the opening kickoff, before
        # this loop starts) belongs to THIS drive -- prepended here so it
        # picks up the same offense_abbr/drive_number stamping as every
        # other PlayEvent below, rather than needing its own separate path.
        drive_play_events = pending_kickoff_events + drive_play_events
        pending_kickoff_events = []

        for pe in drive_play_events:
            pe.offense_abbr = off.abbr
            pe.drive_number = i + 1  # 1-based, matches this drive's index in `events` below
        all_plays.extend(drive_play_events)

        # "defensive_touchdown" is a turnover too (an INT/fumble returned
        # for a Defensive TD, GDD Sec 6.7.2) -- excluded here for the same
        # reason a plain "turnover" already is, see drive_sim.py's own
        # total_yards handling for the same convention.
        pass_yards = sum(pe.yards for pe in drive_play_events if pe.play_type == "pass" and pe.outcome not in ("turnover", "defensive_touchdown"))
        rush_yards = sum(pe.yards for pe in drive_play_events if pe.play_type == "run" and pe.outcome not in ("turnover", "defensive_touchdown"))
        pass_attempts = sum(1 for pe in drive_play_events if pe.play_type == "pass" and pe.outcome != "sack")
        rush_attempts = sum(1 for pe in drive_play_events if pe.play_type == "run")

        # Safety points belong to the defense, not this drive's offense --
        # simulate_drive() returns pts=0 for a safety and flags it via txt.
        safety_pts = 2 if txt == "Safety" else 0

        # Defensive TD points (GDD Sec 6.7.2) also belong to the defense,
        # not this drive's offense -- simulate_drive() signals it with a
        # NEGATIVE pts (-6/-7) rather than a new return value, the same
        # "someone other than this drive's offense scored" shape Safety
        # already established (see simulate_drive's own docstring).
        defensive_td_pts = -pts if pts < 0 else 0
        offense_pts = max(pts, 0)

        if side_home:
            h += offense_pts  # offense (home) scores normally; 0 on a safety/defensive TD
            a += safety_pts + defensive_td_pts  # defense (away) gets the points instead
            htot.points += offense_pts; htot.plays += plays; htot.yards += yards; htot.turnovers += tos
            htot.pass_yards += pass_yards; htot.rush_yards += rush_yards
            htot.pass_attempts += pass_attempts; htot.rush_attempts += rush_attempts
        else:
            a += offense_pts
            h += safety_pts + defensive_td_pts
            atot.points += offense_pts; atot.plays += plays; atot.yards += yards; atot.turnovers += tos
            atot.pass_yards += pass_yards; atot.rush_yards += rush_yards
            atot.pass_attempts += pass_attempts; atot.rush_attempts += rush_attempts

        events.append(DriveEvent(
            desc=f"{off.abbr} {txt}",
            clock_left=max(0, drives_left * 180),
            home_score=h, away_score=a
        ))

        # A score (TD/FG/Defensive TD -- pts != 0; a Safety's own free
        # kick stays the pre-existing hardcoded next_field_pos=35, out of
        # this pass's scope) means the NEXT drive opens with a real
        # kickoff instead of just inheriting simulate_drive's placeholder
        # 25. Anything else (punt, turnover, turnover on downs, missed
        # FG) is a normal change of possession at the spot -- no kick
        # involved, so next_side_home just flips like it always did.
        if pts != 0:
            field_pos, next_side_home, kickoff_h, kickoff_a, pending_kickoff_events = _resolve_kickoff(
                rng, kicker_is_home=side_home, home=home, away=away, h=h, a=a, drives_left=drives_left,
                home_off_starters=home_off_starters, away_off_starters=away_off_starters,
                is_two_minute=is_two_min, allow_onside=True,
                home_staff=home_staff, away_staff=away_staff,
            )
            h += kickoff_h
            a += kickoff_a
        else:
            field_pos = next_field_pos
            next_side_home = not side_home

    winner = "home" if h >= a else "away"
    res = GameResult(home_score=h, away_score=a, winner=winner, events=events, plays=all_plays)
    res.home_totals = htot  # type: ignore[attr-defined]
    res.away_totals = atot  # type: ignore[attr-defined]
    return res
