"""
Season state: schedule, results, and standings.

Persisted to data/saves/current_season.json (GDD Part 1 Sec 8: JSON
save/export) via app.services.save_service. get_season() loads that
file on first use if it exists; simulate_current_week() saves after
every simulated week, so a season survives a server restart. Reset
Season explicitly rebuilds from the current LEAGUE_SEED and overwrites
the save file -- loading never mixes a stale save with a changed seed
silently.

Concurrency: app/main.py's /season/simulate-week and /season/reset
routes are plain `def`s, which FastAPI runs in a thread pool -- so two
requests CAN genuinely execute concurrently on different threads (a
double-click, a slow request retried, a page reload resubmitting the
form). simulate_current_week()'s read-current_week / simulate / save
sequence is not atomic on its own: two overlapping calls can both read
the same current_week before either increments it, both simulate the
same week (inflating that week's teams' win/loss counts), and current
_week can end up past N_WEEKS entirely. A real occurrence of this (a
team with 20 wins in an 18-week season, current_week at 21) is what
_STATE_LOCK below fixes -- every mutating call now fully serializes."""
from __future__ import annotations
import threading
from dataclasses import dataclass, field

from app.config import get_league_seed
from app.data.teams import TEAMS, TEAMS_BY_ABBR
from app.engine.schedule import generate_season_schedule, N_WEEKS
from app.engine.placeholder_ratings import ratings_for
from app.engine.rng import RNG, stable_seed
from app.engine.game_sim import simulate_game, TeamSim
from app.engine.game_state import GameResult
from app.engine import (
    power_rating, score_fidelity, playoffs, progression, season_stats, coaching, coach_progression, injuries,
    free_agency,
)
from app.engine.score_fidelity import SFSState
from app.engine.playoffs import PlayoffBracket
from app.services import gameplan_store, history_store, power_rank_history, coach_store, coach_records, depth_chart, injury_store
from app.core.db import get_session
from app.models.player import Player, Position
from sqlmodel import select


@dataclass
class TeamRecord:
    abbr: str
    location: str
    wins: int = 0
    losses: int = 0
    points_for: int = 0
    points_against: int = 0
    power_rating: float = power_rating.INITIAL_RATING  # GDD Sec 7.2 -- UI label "Power Ranking"

    @property
    def win_pct(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total else 0.0

    @property
    def point_diff(self) -> int:
        return self.points_for - self.points_against

    @property
    def games_played(self) -> int:
        return self.wins + self.losses


@dataclass
class WeekGame:
    home_abbr: str
    away_abbr: str
    result: GameResult | None = None


@dataclass
class Season:
    league_seed: int
    schedule: list[list[WeekGame]]
    records: dict[str, TeamRecord]
    current_week: int = 1  # 1-indexed; next week to simulate
    sfs: SFSState = field(default_factory=SFSState)  # Score Fidelity System weekly-feedback state
    user_team_abbr: str | None = None  # GDD Sec 10.1: the team the player runs as GM/Coach, chosen once at franchise creation
    playoffs: PlayoffBracket | None = None  # GDD Sec 7.3 -- None until the regular season completes and Sim Week is pressed once more
    season_number: int = 0  # 0-indexed; feeds schedule.py's 3-/4-year rotation formulas and is incremented by start_new_season()

    @property
    def is_complete(self) -> bool:
        return self.current_week > N_WEEKS

    def standings(self) -> list[TeamRecord]:
        return sorted(
            self.records.values(),
            key=lambda r: (-r.win_pct, -r.point_diff, r.location),
        )


def _bootstrap_season_number() -> int:
    """A brand-new franchise's first season continues chronologically
    AFTER whatever's already permanently archived in history_store.py
    (real-NFL-seeded seasons via scripts/import_nfl_history.py, or a
    previous franchise's own simulated seasons -- history.json is never
    cleared on reset, by design, so it's one continuous, ever-growing
    league timeline, not a per-franchise save slot) rather than always
    restarting at 0."""
    return len(history_store.get_history())


def _build_season(
    league_seed: int, season_number: int | None = None,
    prior_standings: dict[tuple[str, str], list[str]] | None = None,
) -> Season:
    if season_number is None:
        season_number = _bootstrap_season_number()
    raw_schedule = generate_season_schedule(league_seed, season_number=season_number, prior_standings=prior_standings)
    schedule = [
        [WeekGame(home_abbr=h, away_abbr=a) for h, a in week]
        for week in raw_schedule
    ]
    records = {
        t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS
    }
    return Season(league_seed=league_seed, schedule=schedule, records=records, season_number=season_number)


_season: Season | None = None
_STATE_LOCK = threading.RLock()  # serializes every mutating call -- see module docstring. Reentrant: simulate_current_week()
# holds the lock and then calls get_season(), which also acquires it -- a plain Lock would deadlock on that.


def get_season() -> Season:
    global _season
    if _season is None:
        with _STATE_LOCK:
            if _season is None:  # re-check: another thread may have loaded it while we waited for the lock
                from app.services import save_service
                loaded = save_service.load_season()
                _season = loaded if loaded is not None else _build_season(get_league_seed())
    return _season


def reset_season() -> Season:
    global _season
    with _STATE_LOCK:
        from app.services import save_service
        _season = _build_season(get_league_seed())
        season_stats.clear_current_season_cache()
        # R1: a brand-new franchise starts with a clean bill of health --
        # closes out any stale active injuries left over from a prior
        # simulation run against this same database.
        injury_store.resolve_all_active()
        depth_chart.clear_starters_cache()
        save_service.save_season(_season)
        return _season


def set_user_team(team_abbr: str) -> Season:
    """Sets the franchise's user-controlled team (GDD Sec 10.1). Chosen
    once, at franchise creation -- there's no mid-season re-pick route;
    starting a new franchise (reset_season) is what clears it, since
    _build_season's fresh Season defaults user_team_abbr to None."""
    if team_abbr not in TEAMS_BY_ABBR:
        raise ValueError(f"No such team: {team_abbr!r}")
    with _STATE_LOCK:
        season = get_season()
        season.user_team_abbr = team_abbr
        from app.services import save_service
        save_service.save_season(season)
        return season


def _simulate_matchup(season: Season, home_abbr: str, away_abbr: str, week_for_parity: int, seed_parts: tuple) -> GameResult:
    """The per-game simulation core shared by simulate_current_week
    (regular season) and simulate_playoff_round (postseason): real
    starters/ratings, the Score Fidelity System's EP-anchoring
    multiplier, the Weekly Gameplan lookup, the real coaching-staff
    lookup (app/engine/coaching.py -- for BOTH teams, unlike the
    gameplan, which only the user's team ever has), and the resulting
    points/Power Rating updates. Deliberately does NOT touch
    TeamRecord.wins/losses -- those are a regular-season-only concept;
    playoff wins/losses live in the bracket itself
    (PlayoffMatchup.winner_abbr), not in TeamRecord."""
    home_info = TEAMS_BY_ABBR[home_abbr]
    away_info = TEAMS_BY_ABBR[away_abbr]
    home = TeamSim(name=home_info.location, abbr=home_info.abbr,
                    ratings=ratings_for(home_info, season.league_seed))
    away = TeamSim(name=away_info.location, abbr=away_info.abbr,
                    ratings=ratings_for(away_info, season.league_seed))

    home_rec = season.records[home_abbr]
    away_rec = season.records[away_abbr]

    win_prob = power_rating.home_win_probability(
        home_rec.power_rating, home_rec.wins, home_rec.games_played,
        away_rec.power_rating, away_rec.wins, away_rec.games_played,
        week_for_parity,
    )

    game_seed = stable_seed(season.league_seed, *seed_parts)
    rng = RNG.with_seed(game_seed)
    home_mult = score_fidelity.ep_multiplier(rng, win_prob, True, season.sfs.scoring_feedback_multiplier)
    away_mult = score_fidelity.ep_multiplier(rng, win_prob, False, season.sfs.scoring_feedback_multiplier)

    home_gameplan = gameplan_store.get_gameplan(home_abbr) if home_abbr == season.user_team_abbr else None
    away_gameplan = gameplan_store.get_gameplan(away_abbr) if away_abbr == season.user_team_abbr else None

    # GDD Sec 7.7.2: every team's real staff, not just the user's --
    # this is what makes an AI team's play-calling reflect its actual
    # coordinators instead of the league-average baseline. Falls back to
    # a fully neutral effect when no coaches are imported.
    home_staff = coaching.staff_effect_for(home_abbr)
    away_staff = coaching.staff_effect_for(away_abbr)

    result = simulate_game(rng, home, away, home_mult, away_mult, home_gameplan, away_gameplan,
                            home_staff=home_staff, away_staff=away_staff)

    home_rec.points_for += result.home_score
    home_rec.points_against += result.away_score
    away_rec.points_for += result.away_score
    away_rec.points_against += result.home_score

    home_rec.power_rating, away_rec.power_rating = power_rating.update_ratings(
        home_rec.power_rating, away_rec.power_rating, result.home_score, result.away_score,
    )
    return result


def simulate_current_week() -> int:
    """Simulates every game in the current week, updates records and
    Team Power Ratings, runs the Score Fidelity System's weekly feedback
    update, advances current_week. Returns the week number that was just
    simulated. The whole thing runs under _STATE_LOCK (see module
    docstring) -- without it, two concurrent calls (this is a plain
    `def` route, thread-pooled by FastAPI) can both read the same
    current_week, both simulate the same week, and current_week can end
    up past N_WEEKS entirely."""
    with _STATE_LOCK:
        season = get_season()
        if season.is_complete:
            return season.current_week - 1

        week_num = season.current_week

        # R1 (GDD Sec 6.10.4): decrement/taper every active injury BEFORE
        # this week's games, so a player whose weeks_out reaches 0 this
        # week is available for THIS week's games. clear_starters_cache()
        # afterward: get_offensive_starters/get_defensive_starters are
        # lru_cache'd per team_abbr only, so a team whose availability
        # just changed (a starter went OUT, or came off RTP) needs a
        # fresh selection this week, not last week's cached one.
        injuries.apply_weekly_decay(season.season_number, week_num)
        depth_chart.clear_starters_cache()

        week_games = season.schedule[week_num - 1]
        week_total_points = 0
        week_total_teams = 0

        for game in week_games:
            result = _simulate_matchup(
                season, game.home_abbr, game.away_abbr, week_num,
                (season.season_number, week_num, game.home_abbr, game.away_abbr),
            )
            game.result = result

            home_rec = season.records[game.home_abbr]
            away_rec = season.records[game.away_abbr]
            if result.winner == "home":
                home_rec.wins += 1
                away_rec.losses += 1
            else:
                away_rec.wins += 1
                home_rec.losses += 1

            week_total_points += result.home_score + result.away_score
            week_total_teams += 2

        # ROADMAP.md Sec2d-B item 10: real week-over-week Power Ranking
        # movement needs a persisted snapshot to diff against -- this is
        # the one place every team's rank for this week is known, right
        # after every game's power_rating update above and before the
        # week advances. See power_rank_history.py's own docstring for
        # the store's shape and the test-isolation convention it follows.
        ranks = {
            r.abbr: i for i, r in enumerate(
                sorted(season.records.values(), key=lambda r: -r.power_rating), start=1
            )
        }
        power_rank_history.record_snapshot(season.season_number, week_num, ranks)
        season_stats.clear_current_season_cache()

        # R1 (GDD Sec 6.10.1): roll new injuries from what just happened
        # this week, from each player's real accumulated exposure in
        # their own game's box score -- see injuries.py's module
        # docstring for why this replaces a live per-play hook inside
        # drive_sim.py. Runs AFTER games so this week's box scores are
        # final; clear the starters cache again so next week's selection
        # (and this week's Player Card/Roster status badges) reflect any
        # brand-new injuries immediately.
        injuries.roll_injuries_for_week(season, week_num)
        depth_chart.clear_starters_cache()

        season.current_week += 1

        if week_total_teams:
            measured_ppg = week_total_points / week_total_teams
            score_fidelity.weekly_feedback_update(season.sfs, week_num, measured_ppg)

        from app.services import save_service
        save_service.save_season(season)

        return week_num


def simulate_playoff_round() -> str:
    """GDD Sec 7.3: simulates every remaining matchup in the current
    playoff round, building the Wild Card round the first time this is
    called after the regular season completes, and building the next
    round's matchups once the current one finishes -- one round per
    call, same "Sim Week" cadence as simulate_current_week. Returns the
    round name just simulated ("WC"/"DIV"/"CONF"/"SB"). Raises if the
    regular season isn't finished yet -- app/main.py's route is what
    decides which of these two functions to call, based on
    season.is_complete.

    A call once the Super Bowl is already decided safely no-ops and
    returns "SB" again, same post-completion-no-op convention as
    simulate_current_week."""
    with _STATE_LOCK:
        season = get_season()
        if not season.is_complete:
            raise ValueError("Regular season isn't finished yet")

        if season.playoffs is None:
            season.playoffs = playoffs.build_wild_card_round(season)

        bracket = season.playoffs
        current_round = bracket.rounds[-1]
        round_name = current_round[0].round_name

        if all(m.is_complete for m in current_round):
            return round_name  # Super Bowl already decided -- no-op

        pseudo_week = N_WEEKS + {"WC": 1, "DIV": 2, "CONF": 3, "SB": 4}[round_name]
        for matchup in current_round:
            matchup.result = _simulate_matchup(
                season, matchup.home_abbr, matchup.away_abbr, pseudo_week,
                (season.season_number, "playoffs", round_name, matchup.home_abbr, matchup.away_abbr),
            )

        # GDD Sec 7.9.2: conference-title and Super Bowl credit is
        # awarded to each winning (and, for the SB, losing) staff by the
        # role each coach held. Safe to call on every round -- it no-ops
        # for WC/DIV, and Sec 7.9.2's idempotency requirement means a
        # replayed round credits nothing a second time.
        coach_records.credit_championship_round(season, round_name)

        if round_name != "SB":
            bracket.rounds.append(playoffs.build_next_round(bracket))

        from app.services import save_service
        save_service.save_season(season)
        return round_name


# Which side of the ball a player develops under, for choosing between a
# staff's offensive and defensive development ratings. K/P sit on the
# offensive side by default -- neither coordinator really develops a
# specialist (that's the ST coach's job, and GDD Sec 7.7.2.3 defines no
# development rating for special teams at all), and both multipliers are
# bounded to the same narrow band regardless.
DEFENSIVE_POSITIONS = {
    Position.LE, Position.RE, Position.DT,
    Position.LOLB, Position.MLB, Position.ROLB,
    Position.CB, Position.FS, Position.SS,
}


def apply_progression_to_roster(season: Season) -> int:
    """GDD Sec 7.6: ages and develops every real, rostered player
    (free agents are skipped -- they didn't play a snap this season, so
    there's no usage/performance signal to progress them against).
    Returns the number of players updated. A player's usage input
    (app/engine/progression.py's F_use) comes from this season's real
    touches: QB attempts / RB carries / WR-TE targets (season_stats.py's
    offensive aggregation) for offensive skill players, or a defensive
    activity proxy -- solo tackles + interceptions + forced fumbles +
    passes defended (season_stats.py's aggregate_season_defensive_stats,
    now real for every DL/LB/DB via app/engine/defensive_box_score.py,
    not interception-only) -- for defenders. Sacks and tackles-for-loss
    are deliberately NOT added again on top of solo_tackles here, since
    defensive_box_score.py already folds a sack/TFL into its own
    solo-tackle count; adding them again would double-count the same
    play. OL/K/P still get progression.py's documented neutral default
    -- no real per-play usage stat exists for them in this engine.

    Each player's own team's coaching staff also scales their GROWTH
    (never their decline) via app/engine/coaching.py's
    dev_multiplier_offense/dev_multiplier_defense, built from the real
    player_dev_offense/player_dev_defense ratings of the head coach, the
    relevant coordinator, and the position-coach pool (GDD Sec
    7.7.2.3/8.2.1). A league-average staff -- and a database with no
    coaches imported at all -- multiplies by exactly 1.0, so this
    changes nothing for a franchise without a real staff."""
    passing, rushing, receiving = season_stats.aggregate_season_stats(season)
    touches: dict[tuple[str, str], int] = {}
    for key, line in passing.items():
        touches[key] = touches.get(key, 0) + line.attempts
    for key, line in rushing.items():
        touches[key] = touches.get(key, 0) + line.carries
    for key, line in receiving.items():
        touches[key] = touches.get(key, 0) + line.targets
    for key, line in season_stats.aggregate_season_defensive_stats(season).items():
        touches[key] = touches.get(key, 0) + line.solo_tackles + line.interceptions + line.forced_fumbles + line.passes_defended

    updated = 0
    with get_session() as s:
        players = s.exec(select(Player).where(Player.team_abbr != None)).all()  # noqa: E711
        for player in players:
            key = (player.team_abbr, player.full_name)
            rng = RNG.with_seed(stable_seed(season.league_seed, season.season_number, player.player_id, "progression"))
            effect = coaching.staff_effect_for(player.team_abbr)
            dev_mult = (effect.dev_multiplier_defense if player.position in DEFENSIVE_POSITIONS
                        else effect.dev_multiplier_offense)
            result = progression.progress_player(player, touches.get(key), season.season_number, rng,
                                                  coach_dev_multiplier=dev_mult)
            progression.apply_progression(player, result)
            # R4a (GDD Sec 8.3): contract_years_remaining is now a real,
            # decrementing term rather than the M8-era static 1-5
            # placeholder -- see app/engine/contracts.py's module
            # docstring. Floored at 0 (an expired deal) rather than going
            # negative; R4b (Free Agency) is the chunk that acts on a
            # player reaching 0, not this one.
            player.contract_years_remaining = max(0, player.contract_years_remaining - 1)
            s.add(player)
            updated += 1
        # R4b (GDD Sec 8.4): a contract that just hit 0 really releases
        # the player to free agency -- see app/engine/free_agency.py's
        # own module docstring for why this is R4b's trigger, not R4a's.
        # No re-add() needed: `players` are already session-tracked from
        # the loop above, and SQLAlchemy picks up further attribute
        # mutations on an already-added object automatically.
        free_agency.release_expired_contracts(players)

        # Emergency AI fill (see free_agency.fill_roster_gaps' own
        # docstring): after enough offseasons of real contract churn, a
        # team can be left with ZERO players at a position
        # get_offensive_starters/get_defensive_starters index
        # unconditionally -- a real IndexError crash, caught on this
        # chunk's own first real two-season test run. Autoflush (the
        # session default) means this query already reflects the
        # releases just made above, no manual list-merging needed.
        free_agent_pool = list(s.exec(select(Player).where(Player.team_abbr == None)).all())  # noqa: E711
        for team in TEAMS:
            team_roster = [p for p in players if p.team_abbr == team.abbr]
            free_agency.fill_roster_gaps(team.abbr, team_roster, free_agent_pool, season.season_number)

        s.commit()
    return updated


def apply_coach_offseason(season: Season) -> int:
    """GDD Sec 8.2.2/8.2.3: the coaching-staff half of the offseason.

    Records the just-completed season into every employed coach's
    career record (Sec 7.9.1's rollups + Sec 7.7.2.4's lifecycle
    counters, including a freshly computed Job Security Score), then
    ages every coach one year, progresses/regresses their dynamic
    ratings against their team's real end-of-season league ranks, and
    rolls Sec 8.2.3's age-based retirement. Returns the number of
    coaches updated.

    Vacancies left by a retirement are deliberately NOT auto-filled --
    see app/engine/coach_progression.py's docstring for why (the hiring
    market needs the same negotiation machinery R4a builds for player
    contracts). The Staff page renders a vacant seat as vacant.

    A database with no coaches returns 0 and changes nothing, so a
    franchise that predates the coach import rolls over exactly as it
    did before."""
    from app.models.coach import Coach as CoachModel
    from sqlalchemy.exc import OperationalError

    coach_records.record_season_results(season)
    ranks = coach_progression.compute_team_ranks(season)

    updated = 0
    try:
        with get_session() as s:
            coaches = s.exec(select(CoachModel).where(CoachModel.retired == False)).all()  # noqa: E712
            for coach in coaches:
                team_ranks = ranks.get(coach.team_abbr or "", coach_progression.TeamRanks())
                result = coach_progression.progress_coach(
                    coach, team_ranks, season.season_number, season.league_seed,
                )
                coach_progression.apply_coach_progression(coach, result)
                s.add(coach)
                updated += 1
            s.commit()
    except OperationalError:
        return 0

    coach_store.clear_cache()
    coaching.clear_cache()
    return updated


def start_new_season() -> Season:
    """GDD Sec 4's Offseason step + Sec 7.6 (Player Progression &
    Regression): moves a completed franchise into its next season.
    Requires the playoffs to be fully decided -- this isn't a
    mid-season operation.

    What carries forward vs. resets, and why:
    - season_number increments, so schedule.py's 3-year intra-conference
      / 4-year inter-conference rotations actually rotate.
    - Real final division standings (playoffs.final_division_standings,
      the SAME tie-break chain as playoff seeding) feed the new
      schedule's standings-based games -- replacing schedule.py's
      season-0-only bootstrap order.
    - Every real rostered player ages and develops for real
      (apply_progression_to_roster), mutating the actual DB rows.
    - Every employed coach has this season written into their career
      record, ages a year, progresses/regresses against their team's
      real league ranks, and rolls Sec 8.2.3's retirement check
      (apply_coach_offseason) -- also real DB writes.
    - The user's chosen team (Sec 10.1) carries forward -- a new season
      isn't a new franchise.
    - The Score Fidelity System's weekly-feedback multiplier (Sec 6.2.4)
      carries forward -- it's meant to self-correct over time, not
      reset every year.
    - Weekly Gameplan settings (gameplan_store) are untouched -- keyed
      by team abbr, not by season.
    - Everything else per-season (records, schedule, playoffs) is
      fresh, same as reset_season() already does for a brand-new
      franchise.
    - The just-completed season's final standings, champion, awards,
      and stat leaders are archived permanently (history_store.py)
      BEFORE any of the above resets happen -- otherwise that season's
      numbers would simply be lost, which is exactly the gap this
      whole function exists to close.
    """
    with _STATE_LOCK:
        season = get_season()
        if season.playoffs is None or not season.playoffs.is_complete:
            raise ValueError("Playoffs aren't finished yet")

        prior_standings = playoffs.final_division_standings(season)
        history_store.archive_season(season)
        history_store.clear_career_stats_cache()
        season_stats.clear_current_season_cache()
        apply_progression_to_roster(season)
        # GDD Sec 8.2.2/8.2.3 -- runs AFTER the player pass so the
        # coaching staff that earned this season's results is the one
        # credited with them, and before the new Season object exists so
        # every rank it reads still refers to the season just finished.
        apply_coach_offseason(season)
        # R1: offseason healing -- see injury_store.resolve_all_active()'s
        # own docstring for why a trailing RTP taper can still be active
        # at season end even though weeks_out itself is always capped to
        # the season boundary.
        injury_store.resolve_all_active()
        depth_chart.clear_starters_cache()

        next_number = season.season_number + 1
        new_season = _build_season(season.league_seed, season_number=next_number, prior_standings=prior_standings)
        new_season.user_team_abbr = season.user_team_abbr
        new_season.sfs = season.sfs

        global _season
        _season = new_season
        from app.services import save_service
        save_service.save_season(new_season)
        return new_season
