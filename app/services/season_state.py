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
from types import SimpleNamespace

from app.config import get_league_seed
from app.data.teams import TEAMS, TEAMS_BY_ABBR
from app.engine.schedule import generate_season_schedule, generate_preseason_schedule, N_WEEKS
from app.engine.placeholder_ratings import ratings_for
from app.engine.rng import RNG, stable_seed
from app.engine.game_sim import simulate_game, TeamSim
from app.engine.game_state import GameResult
from app.engine.weather import generate_weather
from app.engine import (
    power_rating, score_fidelity, playoffs, progression, season_stats, coaching, coach_progression, injuries,
    free_agency, awards, headlines, draft,
)
from app.engine.score_fidelity import SFSState
from app.engine.playoffs import PlayoffBracket
from app.services import (
    gameplan_store, history_store, power_rank_history, coach_store, coach_records, depth_chart, injury_store,
    award_race_history, headlines_history, undrafted_pool,
)
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
    # R10 (GDD preseason): 4 real, user-triggered games per team, generated
    # up front (same as the regular schedule) but never touching
    # TeamRecord.wins/losses or the regular schedule -- see
    # simulate_preseason()'s own docstring for what a preseason game DOES
    # feed into (progression, Week-1 scouting/stats backfill).
    preseason_schedule: list[list[WeekGame]] = field(default_factory=list)
    # None outside the offseason; "staff" then "resign" while it's in
    # progress (Brian's ask, 2026-09-13: distinct stops for Staff
    # Decisions and Free Agent Decisions, not one flat pause) -- set by
    # begin_offseason()/advance_offseason_stage(), cleared implicitly
    # (back to None) when finish_offseason() builds the next Season.
    # "staff": coach signing (every AI team's own hiring/firing) and
    #   player aging/progression have already run; Sim Week (app/main.py)
    #   stops advancing and instead sends the player to the Staff page --
    #   a chance to review/adjust their OWN staff (the existing, always-
    #   available /staff hire/fire routes) before continuing.
    # "resign": the player's own expiring-contract re-signing window is
    #   open on the GM Desk; finish_offseason() (free agency, the draft,
    #   and the new Season) only runs once this stage ends.
    # See season_state.begin_offseason()/advance_offseason_stage()/
    # finish_offseason().
    offseason_stage: str | None = None

    @property
    def is_complete(self) -> bool:
        return self.current_week > N_WEEKS

    @property
    def preseason_rounds_played(self) -> int:
        """0-4: how many of the 4 preseason rounds have been simulated.
        simulate_preseason() always plays every round in one action, so
        in practice this only ever reads 0 (the "Preseason (0/4
        simulated)" button state) or 4 (all played, button disabled) --
        computed generally rather than as a bare bool for a truthful
        progress count if that ever changes."""
        return sum(1 for week in self.preseason_schedule if week and all(g.result is not None for g in week))

    @property
    def preseason_total_rounds(self) -> int:
        return len(self.preseason_schedule)

    @property
    def preseason_complete(self) -> bool:
        return self.preseason_total_rounds > 0 and self.preseason_rounds_played == self.preseason_total_rounds

    @property
    def preseason_pending(self) -> bool:
        """True only while preseason is genuinely still "the first weeks"
        to sim -- there's an unplayed preseason AND not even Week 1 of
        the regular season has been simulated yet. Deliberately does NOT
        just check preseason_complete: a season that already advanced
        past Week 1 without ever playing its preseason (every save from
        before Sim Week drove preseason automatically, and any franchise
        that simply never clicked the old standalone preseason button)
        must never have Sim Week suddenly demand 4 rounds of preseason
        retroactively once the regular season -- or even the playoffs --
        is already well underway or done. Once current_week > 1, this is
        permanently False for the rest of the season, regardless of
        preseason_complete."""
        return bool(self.preseason_schedule) and not self.preseason_complete and self.current_week == 1

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
    raw_preseason = generate_preseason_schedule(league_seed, season_number=season_number)
    preseason_schedule = [
        [WeekGame(home_abbr=h, away_abbr=a) for h, a in week]
        for week in raw_preseason
    ]
    records = {
        t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS
    }
    # Brian's ask, 2026-09-13: next season's draft class exists and is
    # browsable/board-able for the ENTIRE season being built here, not
    # just after it ends -- generated once, right now, and persisted via
    # draft_class_store so the Draft page (and the eventual live pick-by-
    # pick event) both read the exact same real, deterministic class.
    # Harmless to regenerate if this ever runs twice for the same
    # season_number+1 (generate_draft_class is a pure function of
    # (league_seed, season_number) -- byte-identical either way).
    from app.services import draft_class_store
    draft_class_store.save_class(season_number + 1, draft.generate_draft_class(league_seed, season_number + 1))
    # Draft-Pick Trading (GDD Sec 8.5): keeps the real 3-draft-year
    # tradeable window (this season + the next two) always seeded as a
    # new season starts, whether that's a brand-new franchise
    # (reset_season()) or a real rollover (start_new_season()).
    from app.services import draft_pick_store
    draft_pick_store.ensure_lookahead_seeded(season_number)
    return Season(league_seed=league_seed, schedule=schedule, records=records, season_number=season_number,
                  preseason_schedule=preseason_schedule)


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
        from app.services import save_service, owner_pressure_store, team_expectations
        _season = _build_season(get_league_seed())
        season_stats.clear_current_season_cache()
        # R1: a brand-new franchise starts with a clean bill of health --
        # closes out any stale active injuries left over from a prior
        # simulation run against this same database.
        injury_store.resolve_all_active()
        depth_chart.clear_starters_cache()
        # R3d: a brand-new franchise starts every owner at neutral (Sec
        # 3.2 -- OwnerWinPressure is franchise history, and a reset IS a
        # new franchise) and gets a fresh preseason expectation snapshot
        # for its own season 0 (Sec 3.3), computed from the real,
        # freshly-reset rosters/coaches.
        owner_pressure_store.reset_all()
        team_expectations.compute_and_store(_season.season_number)
        save_service.save_season(_season)
        from app.services import save_manager
        save_manager.sync_active_save_summary()
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
        from app.services import save_service, save_manager
        save_service.save_season(season)
        save_manager.sync_active_save_summary()
        return season


def _simulate_one_game(season: Season, home_abbr: str, away_abbr: str, week_for_parity: int, seed_parts: tuple) -> GameResult:
    """The real per-game simulation core shared by simulate_current_week
    (regular season), simulate_playoff_round (postseason), AND
    simulate_preseason (R10): real starters/ratings, the Score Fidelity
    System's EP-anchoring multiplier (read from season.records as they
    stand right now -- for preseason that's always the fresh 0-0/
    INITIAL_RATING state, since it runs before Week 1), the Weekly
    Gameplan lookup, the real coaching-staff lookup, and real per-game
    weather (R7). Deliberately touches NOTHING on season.records itself
    -- every caller decides for itself what a game's result should
    update: _simulate_matchup (below) applies the regular-season/playoff
    points+Power-Rating side effects; simulate_preseason applies none at
    all, per GDD preseason's own scope (not shown in Standings/Power
    Rankings/Awards anywhere)."""
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

    # R7 (GDD Sec 6.9.2): deterministic per-game weather, keyed off the
    # same real (league_seed, season_number, week) inputs every other
    # per-week seeded system in this engine uses, plus the home team
    # (weather is a property of ITS stadium/climate). week_for_parity is
    # the real week number for a regular-season game and the pseudo-week
    # (N_WEEKS + round offset) for a playoff round -- both are stable,
    # real per-(season, matchup) inputs, so this is deterministic and
    # regenerable on demand (app/main.py recomputes the identical Weather
    # for display without needing to persist it on GameResult).
    weather = generate_weather(season.league_seed, season.season_number, week_for_parity, home_abbr)

    return simulate_game(rng, home, away, home_mult, away_mult, home_gameplan, away_gameplan,
                          home_staff=home_staff, away_staff=away_staff, weather=weather)


def _simulate_matchup(season: Season, home_abbr: str, away_abbr: str, week_for_parity: int, seed_parts: tuple) -> GameResult:
    """_simulate_one_game() plus the regular-season/playoff side effects:
    points_for/against and Power Rating updates. Deliberately does NOT
    touch TeamRecord.wins/losses -- those are a regular-season-only
    concept; playoff wins/losses live in the bracket itself
    (PlayoffMatchup.winner_abbr), not in TeamRecord."""
    home_rec = season.records[home_abbr]
    away_rec = season.records[away_abbr]

    result = _simulate_one_game(season, home_abbr, away_abbr, week_for_parity, seed_parts)

    home_rec.points_for += result.home_score
    home_rec.points_against += result.away_score
    away_rec.points_for += result.away_score
    away_rec.points_against += result.home_score

    home_rec.power_rating, away_rec.power_rating = power_rating.update_ratings(
        home_rec.power_rating, away_rec.power_rating, result.home_score, result.away_score,
    )
    return result


def simulate_preseason() -> int:
    """R10 (GDD preseason): user-triggered, all 4 rounds simulated in one
    action (unlike the regular season's one-week-at-a-time Sim Week) --
    the /season page's "Preseason (0/4 simulated)" button calls this
    once and it becomes "Preseason (4/4 complete)", disabled, forever
    after (idempotent: calling this again once preseason_complete is
    already True is a safe no-op, same convention as simulate_current_
    week/simulate_playoff_round post-completion). Returns the number of
    preseason games actually simulated by THIS call (0 on a no-op).

    Deliberately touches NOTHING on season.records (wins/losses/points/
    Power Rating) or season_stats' current-season cache -- a preseason
    game is real and its box score IS queried (progression's usage
    nudge, and scouting.py's/the Dashboard's Week-1-only backfill), but
    it does not count as a regular-season result anywhere records/
    standings/Power Rankings/Awards read from, per this feature's own
    GDD scope."""
    with _STATE_LOCK:
        season = get_season()
        if season.preseason_complete or not season.preseason_schedule:
            return 0

        simulated = 0
        for round_idx, round_games in enumerate(season.preseason_schedule, start=1):
            if all(g.result is not None for g in round_games):
                continue
            _before_preseason_round(season, round_idx)
            for game in round_games:
                if game.result is not None:
                    continue
                game.result = _simulate_one_game(
                    season, game.home_abbr, game.away_abbr, 1,
                    (season.season_number, "preseason", round_idx, game.home_abbr, game.away_abbr),
                )
                simulated += 1
            _after_preseason_round(season, round_idx)

        from app.services import save_service
        save_service.save_season(season)
        return simulated


def simulate_next_preseason_round() -> int:
    """Sims exactly the next unplayed preseason round -- the Sim Week
    button's own cadence (one click, one round/week), unlike
    simulate_preseason()'s all-4-at-once convenience action above. This
    is what makes preseason read as the real first weeks of the season:
    app/main.py's Sim Week route calls this first, before
    simulate_current_week(), whenever the preseason isn't complete yet.
    Same "never touches season.records" rule as simulate_preseason().
    Returns the round number (1-4) just simulated, or 0 if there's no
    preseason schedule or it's already complete (idempotent, same
    post-completion no-op convention as the other simulate_* functions)."""
    with _STATE_LOCK:
        season = get_season()
        if not season.preseason_schedule or season.preseason_complete:
            return 0

        for round_idx, round_games in enumerate(season.preseason_schedule, start=1):
            if all(g.result is not None for g in round_games):
                continue
            _before_preseason_round(season, round_idx)
            for game in round_games:
                if game.result is not None:
                    continue
                game.result = _simulate_one_game(
                    season, game.home_abbr, game.away_abbr, 1,
                    (season.season_number, "preseason", round_idx, game.home_abbr, game.away_abbr),
                )
            _after_preseason_round(season, round_idx)
            from app.services import save_service
            save_service.save_season(season)
            return round_idx
        return 0  # unreachable given the preseason_complete check above, but explicit


def _before_preseason_round(season: Season, round_idx: int) -> None:
    """Injury clock between preseason rounds (2026-09-14): a player hurt in
    one preseason round heals on the same weekly cadence as the regular
    season. Round 1 is skipped -- nothing has happened yet this preseason,
    and Week 1's own decay already runs before the regular season."""
    if round_idx > 1:
        injuries.apply_weekly_decay(season.season_number, 0)
        depth_chart.clear_starters_cache()


def _after_preseason_round(season: Season, round_idx: int) -> None:
    """Brian's ask, 2026-09-14: preseason games are real games -- players
    can get hurt in them, and each round gets its own headlines (results +
    starter injuries), same pipeline as a regular-season week. Starters are
    captured BEFORE injuries are rolled (see headlines.starter_ids_for_games)."""
    round_games = season.preseason_schedule[round_idx - 1]
    starter_ids = headlines.starter_ids_for_games(round_games)
    new_injuries = injuries.roll_injuries_for_preseason_round(season, round_idx)
    depth_chart.clear_starters_cache()
    headlines_history.record_week_headlines(
        season.season_number, f"P{round_idx}",
        headlines.preseason_round_headlines(season, round_idx, new_injuries, starter_ids),
    )


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

        # R9 (GDD Sec 12, ROADMAP.md Sec4e): Weekly Headlines' division-
        # lead-change/clinch detection needs a BEFORE-this-week snapshot to
        # diff against -- captured here since final_division_standings() is
        # a cheap pure function over season.records, not because it needs
        # to be persisted (unlike power_rank_history's cross-week diffing,
        # this diff never needs to survive past this one function call).
        prior_division_standings = playoffs.final_division_standings(season)

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
                sorted(season.records.values(), key=lambda r: -power_rating.power_score_for(r)), start=1
            )
        }
        power_rank_history.record_snapshot(season.season_number, week_num, ranks)
        season_stats.clear_current_season_cache()

        # R8 (Awards Page): a real weekly snapshot of the Top-5 per award
        # plus Pro Bowl starters -- the one place this week's exact
        # awards-race state is known, same "right after this week's own
        # Power Rank snapshot" timing as that store. awards.py's own
        # functions always compute fresh from real game stats; this is
        # what remembers what THIS week's computation looked like for the
        # Weekly Race Archive tab to show later, since nothing else does.
        award_race_history.record_week_awards(season.season_number, week_num, {
            "mvp": awards.most_valuable_player(season),
            "opoy": awards.offensive_player_of_the_year(season),
            "dpoy": awards.defensive_player_of_the_year(season),
            "oroy": awards.offensive_rookie_of_the_year(season),
            "droy": awards.defensive_rookie_of_the_year(season),
            "coty": awards.coach_of_the_year(season),
            "pro_bowl": {
                "AFC": awards.pro_bowl_starters(season, "AFC"),
                "NFC": awards.pro_bowl_starters(season, "NFC"),
            },
        })

        # R1 (GDD Sec 6.10.1): roll new injuries from what just happened
        # this week, from each player's real accumulated exposure in
        # their own game's box score -- see injuries.py's module
        # docstring for why this replaces a live per-play hook inside
        # drive_sim.py. Runs AFTER games so this week's box scores are
        # final; clear the starters cache again so next week's selection
        # (and this week's Player Card/Roster status badges) reflect any
        # brand-new injuries immediately.
        starter_ids = headlines.starter_ids_for_games(week_games)  # kickoff lineups, before injuries change them
        new_injuries = injuries.roll_injuries_for_week(season, week_num)
        depth_chart.clear_starters_cache()

        # R9 (GDD Sec 12, ROADMAP.md Sec4e): real event detection + a
        # deterministic template render (no LLM -- see headlines.py's own
        # module docstring for why) over this week's now-final box scores,
        # standings movement, and injuries. Stored so the Dashboard reads a
        # week's headlines once instead of recomputing on every request.
        # (season_stats' current-season cache was already cleared above,
        # right after this week's games -- injuries don't change box-score
        # stats, so it's still fresh for headlines.weekly_headlines()'s own
        # cached_current_season_aggregates() call.)
        this_week_headlines = headlines.weekly_headlines(season, week_num, prior_division_standings, new_injuries, starter_ids)
        headlines_history.record_week_headlines(season.season_number, week_num, this_week_headlines)

        # R3d Sec 10: "after each game, if JSS threshold triggers" --
        # every AI team's HC/OC/DC/ST gets a real (seeded) firing-
        # probability roll for the week just played. Sec 3.4's own
        # in-season week modifiers (as low as 0.05 through week 3-4) are
        # what keep this rare early, not a separate gate here. The
        # user's own team is excluded -- Sec 11's manual Staff-page
        # controls are the user's equivalent.
        from app.services import coach_ai
        coach_ai.run_inseason_autonomy(season, week_num, season.user_team_abbr)
        coach_store.clear_cache()

        season.current_week += 1

        if week_total_teams:
            measured_ppg = week_total_points / week_total_teams
            score_fidelity.weekly_feedback_update(season.sfs, week_num, measured_ppg)

        from app.services import save_service, save_manager
        save_service.save_season(season)
        save_manager.sync_active_save_summary()

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

        # Brian's ask, 2026-09-14: headlines continue through the playoffs --
        # each round's results and standout performers, keyed by round name.
        headlines_history.record_week_headlines(
            season.season_number, round_name, headlines.playoff_round_headlines(season, current_round),
        )

        if round_name != "SB":
            bracket.rounds.append(playoffs.build_next_round(bracket))

        from app.services import save_service, save_manager
        save_service.save_season(season)
        save_manager.sync_active_save_summary()
        return round_name


# Which side of the ball a player develops under, for choosing between a
# staff's offensive and defensive development ratings. K/P sit on the
# offensive side by default -- neither coordinator really develops a
# specialist (that's the ST coach's job, and GDD Sec 7.7.2.3 defines no
# development rating for special teams at all), and both multipliers are
# bounded to the same narrow band regardless.
DEFENSIVE_POSITIONS = {
    Position.EDGE, Position.DT,
    Position.LB,
    Position.CB, Position.S,
}

# R10 (GDD preseason): a preseason snap counts toward progression.py's
# F_use touches input at this fraction of a real regular-season snap --
# "as if the player had ~25% of a regular-season game's usage" per this
# feature's own locked-in spec, not a full extra game's worth.
PRESEASON_NUDGE_WEIGHT = 0.25


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

    # R10 (GDD preseason): preseason usage counts toward the SAME F_use
    # touches input, at PRESEASON_NUDGE_WEIGHT (25%) -- "as if the player
    # had ~25% of a regular-season game's usage" per this feature's own
    # spec, not a full extra game's worth. Added on top of (not replacing)
    # the regular-season touches above, so a player who also played real
    # regular-season snaps gets both; a franchise with no preseason games
    # simulated yet (preseason_schedule empty, or none of its games have
    # a result) contributes exactly 0, unchanged from before this existed.
    if season.preseason_schedule:
        pre_season_view = SimpleNamespace(schedule=season.preseason_schedule)
        pre_passing, pre_rushing, pre_receiving = season_stats.aggregate_season_stats(pre_season_view)
        for key, line in pre_passing.items():
            touches[key] = touches.get(key, 0) + round(line.attempts * PRESEASON_NUDGE_WEIGHT)
        for key, line in pre_rushing.items():
            touches[key] = touches.get(key, 0) + round(line.carries * PRESEASON_NUDGE_WEIGHT)
        for key, line in pre_receiving.items():
            touches[key] = touches.get(key, 0) + round(line.targets * PRESEASON_NUDGE_WEIGHT)
        for key, line in season_stats.aggregate_season_defensive_stats(pre_season_view).items():
            pre_defensive_touches = line.solo_tackles + line.interceptions + line.forced_fumbles + line.passes_defended
            touches[key] = touches.get(key, 0) + round(pre_defensive_touches * PRESEASON_NUDGE_WEIGHT)

    updated = 0
    # Perf (Brian's ask, 2026-09-13: Sim Week should take 5s or less):
    # staff_effect_for() is real, cached DB-backed work -- cheap on a
    # repeat call for a team already seen, but this loop runs it once per
    # PLAYER (up to ~1700) instead of once per the ~32 real teams
    # present. Hoisting it into a small per-team cache here doesn't
    # change a single result (still the exact same cached function this
    # is dispatching to), just how many times this loop bothers calling
    # it. (Profiling found the REAL cost of this loop to be SQLModel's
    # own validate-on-assignment __setattr__ plus the ORM's per-row
    # UPDATE compilation across ~1700 players and ~70 columns each --
    # switching to session.bulk_update_mappings() was tried and measured
    # SLOWER, not faster, since it still compiles/binds every column per
    # row and adds a full model_dump() per player on top, so that's not
    # used here; a real fix needs bypassing SQLModel's per-attribute
    # validation entirely, a larger, riskier change than this session
    # has scoped out yet.)
    effect_by_team: dict[str, object] = {}
    with get_session() as s:
        players = s.exec(select(Player).where(Player.team_abbr != None)).all()  # noqa: E711
        for player in players:
            key = (player.team_abbr, player.full_name)
            rng = RNG.with_seed(stable_seed(season.league_seed, season.season_number, player.player_id, "progression"))
            if player.team_abbr not in effect_by_team:
                effect_by_team[player.team_abbr] = coaching.staff_effect_for(player.team_abbr)
            effect = effect_by_team[player.team_abbr]
            dev_mult = (effect.dev_multiplier_defense if player.position in DEFENSIVE_POSITIONS
                        else effect.dev_multiplier_offense)
            result = progression.progress_player(player, touches.get(key), season.season_number, rng,
                                                  coach_dev_multiplier=dev_mult)
            progression.apply_progression(player, result)
            # R4a (GDD Sec 8.3): contract_years_remaining is now a real,
            # decrementing term rather than the M8-era static 1-5
            # placeholder -- see app/engine/contracts.py's module
            # docstring. Floored at 0 (an expired deal) rather than going
            # negative. Deliberately NOT released here anymore: R4b's
            # release_expired_contracts()/fill_roster_gaps() now run
            # later, in finish_offseason(), AFTER the offseason's real
            # re-signing window (Brian's ask, 2026-09-13) -- a player at
            # 0 years stays rostered (and shows up in GM Desk's Expiring
            # Contracts table) until that window closes, so the user
            # (and, automatically, every AI team via
            # free_agency.run_ai_resign_decisions()) gets a real chance
            # to keep them first.
            player.contract_years_remaining = max(0, player.contract_years_remaining - 1)
            s.add(player)
            updated += 1
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
                # Coach Contract Realism (docs/R3d_COACHING_SYSTEM_SPECIFICATION.md
                # Sec 11): contract_years now really counts down, same rollover
                # spot Player.contract_years_remaining already decrements at
                # (R4a). Employed coaches only -- a free agent (team_abbr is
                # None, e.g. just fired, or a never-hired pool candidate) has
                # no active contract to count down. Floored at 0, not
                # negative -- 0 means "expired," not "owes the team years."
                # AI teams' expired contracts get resolved by coach_ai.run_
                # offseason_autonomy() right below; the user's own team's
                # expired contracts just sit at 0 until the user explicitly
                # Extends or Fires (same "user coaching moves are always
                # manual" precedent as Fire/Hire).
                if coach.team_abbr is not None:
                    coach.contract_years = max(0, coach.contract_years - 1)
                s.add(coach)
                updated += 1
            s.commit()
    except OperationalError:
        return 0

    coach_store.clear_cache()
    coaching.clear_cache()

    # R3d Sec 10: AI autonomy runs AFTER progression/retirement so it
    # evaluates this season's real, final ratings/ranks -- and BEFORE
    # the new Season object exists (team_expectations' preseason
    # snapshot, computed once start_new_season()/reset_season() finishes
    # building next season, needs to see any coach hired here already).
    # The user's own team is excluded; Sec 11's Staff-page controls are
    # its manual equivalent.
    from app.services import coach_ai
    coach_ai.run_offseason_autonomy(season, exclude_team_abbr=season.user_team_abbr)
    coach_store.clear_cache()
    coaching.clear_cache()

    # R13 Sec 7: AI Focus Autonomy -- reassigns AI teams' ASSISTANT coaches'
    # Focus Areas based on this season's real signals. Runs last, after
    # hiring/firing has already settled this offseason's real staff, so it
    # never re-evaluates a coach who was just fired.
    coach_ai.run_focus_autonomy(season, exclude_team_abbr=season.user_team_abbr)
    coach_store.clear_cache()
    coaching.clear_cache()

    return updated


def begin_offseason() -> Season:
    """GDD Sec 4's Offseason step, first stage: everything that must
    settle BEFORE anyone's expired contract is actually released, so the
    re-signing window has real players to act on. Requires the playoffs
    to be fully decided -- this isn't a mid-season operation. Idempotent:
    calling this again once `offseason_stage` is already set just
    returns the season unchanged (same post-completion no-op convention
    as simulate_current_week/simulate_playoff_round), so app/main.py's
    Sim Week route can call it unconditionally once the playoffs are
    done.

    What happens here, and why this stage specifically:
    - The just-completed season's final standings, champion, awards, and
      stat leaders are archived permanently (history_store.py) before
      anything below mutates real state -- otherwise that season's
      numbers would simply be lost.
    - Every real rostered player ages and develops for real
      (apply_progression_to_roster), including decrementing
      contract_years_remaining -- but no longer releases anyone at 0;
      see that function's own docstring for why release moved to
      finish_offseason().
    - Every employed coach has this season written into their career
      record, ages a year, progresses/regresses against their team's
      real league ranks, rolls Sec 8.2.3's retirement check, and every
      AI team (not the user's) makes its real hiring/firing decisions
      for the season ahead (apply_coach_offseason).
    - Offseason injury healing (injury_store.resolve_all_active()).

    Leaves `offseason_stage` at "staff" -- the user's OWN team's staff
    decisions (the existing, always-available /staff hire/fire routes)
    are made here, before advance_offseason_stage() opens the re-signing
    window and finish_offseason() runs free agency, the draft, and
    builds the new Season."""
    with _STATE_LOCK:
        season = get_season()
        if season.playoffs is None or not season.playoffs.is_complete:
            raise ValueError("Playoffs aren't finished yet")
        if season.offseason_stage is not None:
            return season

        history_store.archive_season(season)
        history_store.clear_career_stats_cache()
        season_stats.clear_current_season_cache()

        # Offseason Recap (Brian's ask, 2026-09-13): a real before/after
        # roster snapshot -- nothing else logs overall_rating or
        # team_abbr history anywhere, so this is the ONE point where
        # "before" can be captured: every Player row, right before
        # apply_progression_to_roster() (next line) starts mutating
        # ratings, and long before free agency/the draft start moving
        # people between teams. complete_draft_and_advance_season() is
        # what diffs this against the final state once everything lands.
        from app.services import offseason_recap_store
        with get_session() as s:
            before_snapshot = {p.player_id: (p.team_abbr, p.overall_rating) for p in s.exec(select(Player)).all()}
        offseason_recap_store.save_before_snapshot(season.season_number, before_snapshot)

        apply_progression_to_roster(season)
        # GDD Sec 8.2.2/8.2.3 -- runs AFTER the player pass so the
        # coaching staff that earned this season's results is the one
        # credited with them.
        apply_coach_offseason(season)
        # R1: offseason healing -- see injury_store.resolve_all_active()'s
        # own docstring for why a trailing RTP taper can still be active
        # at season end even though weeks_out itself is always capped to
        # the season boundary.
        injury_store.resolve_all_active()
        depth_chart.clear_starters_cache()

        season.offseason_stage = "staff"
        from app.services import save_service, save_manager
        save_service.save_season(season)
        save_manager.sync_active_save_summary()
        return season


def advance_offseason_stage() -> Season:
    """Moves the offseason from "staff" (Staff Decisions, on /staff) to
    "resign" (Free Agent Decisions, on the GM Desk) -- the user has
    reviewed/adjusted their own staff (or simply chose not to) and is
    ready to move on. Raises if the offseason hasn't begun, or has
    already moved past "staff"."""
    with _STATE_LOCK:
        season = get_season()
        if season.offseason_stage != "staff":
            raise ValueError("Not at the Staff Decisions stage")
        season.offseason_stage = "resign"
        from app.services import save_service, save_manager
        save_service.save_season(season)
        save_manager.sync_active_save_summary()
        return season


def finish_offseason(season: Season | None = None) -> Season:
    """GDD Sec 4's Offseason step, third stage (R4b Free Agency): closes
    out the re-signing window and opens the live draft. Requires
    `offseason_stage == "resign"` -- i.e. begin_offseason() then
    advance_offseason_stage() have already run.

    Order matters here: every AI team (all but the user's own -- they
    got the real interactive GM Desk Negotiation flow instead while
    `offseason_stage` was "resign") makes its own resign-or-release call
    for its expiring contracts FIRST (free_agency.run_ai_resign_decisions),
    then whoever -- AI or user -- still has a contract at 0 years is
    released to free agency (free_agency.release_expired_contracts), then
    every team's roster gets emergency-filled at any position left with
    zero players (free_agency.fill_roster_gaps), so the draft (which
    reads real, live roster counts for its own needs-aware AI picks) sees
    the real, final post-free-agency rosters.

    Leaves `offseason_stage` at "draft" and starts the live pick-by-pick
    draft (draft_progress_store.start(), using next season's class --
    already generated and persisted back when THIS season was built, see
    _build_season()'s own comment) -- advance_draft_pick() is what moves
    things the rest of the way; complete_draft_and_advance_season() is
    what finally builds the new Season, once every slot resolves."""
    with _STATE_LOCK:
        season = season if season is not None else get_season()
        if season.offseason_stage != "resign":
            raise ValueError("Not at the Free Agent Decisions stage -- begin_offseason()/advance_offseason_stage() first")

        with get_session() as s:
            players = s.exec(select(Player).where(Player.team_abbr != None)).all()  # noqa: E711
            # Brian's ask, 2026-09-13: AI teams make their own resign/
            # release decision for their expiring contracts here, same
            # window the user's own team just went through interactively
            # on the GM Desk -- neither side is auto-released before this
            # point.
            free_agency.run_ai_resign_decisions(players, season.season_number, exclude_team_abbr=season.user_team_abbr)
            # R4b (GDD Sec 8.4): whoever -- AI declined, or the user
            # simply moved on without re-signing -- still has a contract
            # at 0 years now really releases to free agency.
            free_agency.release_expired_contracts(players)

            # Emergency AI fill (see free_agency.fill_roster_gaps' own
            # docstring): after enough offseasons of real contract churn,
            # a team can be left with ZERO players at a position
            # get_offensive_starters/get_defensive_starters index
            # unconditionally. Autoflush (the session default) means this
            # query already reflects the releases just made above.
            free_agent_pool = list(s.exec(select(Player).where(Player.team_abbr == None)).all())  # noqa: E711
            for team in TEAMS:
                team_roster = [p for p in players if p.team_abbr == team.abbr]
                newly_signed = free_agency.fill_roster_gaps(team.abbr, team_roster, free_agent_pool, season.season_number)
                # R5 (Sec 9.2): an emergency-signed free agent might be a
                # previously-undrafted rookie -- remove() is a no-op for
                # anyone not actually in that pool, so this is safe to
                # call unconditionally rather than checking membership
                # first.
                for signed_player in newly_signed:
                    undrafted_pool.remove(signed_player.player_id)

            s.commit()
        depth_chart.clear_starters_cache()

        next_number = season.season_number + 1
        from app.services import draft_progress_store
        order = draft.compute_draft_order(season, season.league_seed, next_number)
        draft_progress_store.start(next_number, order)

        season.offseason_stage = "draft"
        from app.services import save_service, save_manager
        save_service.save_season(season)
        save_manager.sync_active_save_summary()
        return season


def current_draft_slot():
    """The live draft's current slot (draft.DraftSlot: round/overall_
    pick/team_abbr), or None if there's no live draft in progress right
    now, or it's already fully resolved. Read-only -- app/main.py's
    routes use this to decide whether "Sim Pick" should actually resolve
    a pick (an AI team is on the clock) or just no-op (the user's own
    team is on the clock and must act via a manual pick or "End"),
    without mutating anything themselves."""
    season = get_season()
    if season.offseason_stage != "draft":
        return None
    next_number = season.season_number + 1
    from app.services import draft_progress_store
    progress = draft_progress_store.get(next_number)
    if progress is None:
        return None
    slots = draft.draft_slots(progress["order"], season_number=next_number)
    idx = progress["current_pick_index"]
    if idx >= len(slots):
        return None
    return slots[idx]


def advance_draft_pick(chosen_prospect_index: int | None = None) -> dict:
    """Resolves exactly the current live-draft slot (Brian's ask,
    2026-09-13: Sim Pick / Sim to Your Next Pick / End, never auto-
    running the user's own picks except via "End"). If
    `chosen_prospect_index` is given, it's the user's own real, manual
    choice -- only valid when the current slot's team IS
    season.user_team_abbr. Otherwise the exact same needs-aware AI logic
    simulate_draft() uses picks for whichever team is on the clock
    (including the user's own team, when called from the "End"
    bail-out -- app/main.py's routes are what decide when that's
    appropriate, this function itself has no opinion). Automatically
    calls complete_draft_and_advance_season() once the resolved pick was
    the draft's very last slot. Returns the resolved pick dict (same
    shape draft_store.py's `picks` entries use). Raises if there's no
    live draft in progress, it's already fully resolved, or a manual
    pick is attempted out of turn / on an already-drafted prospect."""
    with _STATE_LOCK:
        season = get_season()
        if season.offseason_stage != "draft":
            raise ValueError("No live draft in progress")
        next_number = season.season_number + 1
        from app.services import draft_progress_store, draft_class_store
        progress = draft_progress_store.get(next_number)
        if progress is None:
            raise ValueError("No live draft in progress")
        slots = draft.draft_slots(progress["order"], season_number=next_number)
        idx = progress["current_pick_index"]
        if idx >= len(slots):
            raise ValueError("The draft is already fully resolved")
        slot = slots[idx]

        prospects = draft_class_store.get_class(next_number)
        if prospects is None:
            # Defensive fallback only -- every real season's class is
            # persisted the moment that season is built (_build_season);
            # this only matters for a save from before that existed.
            # generate_draft_class is deterministic, so this reproduces
            # the exact same class byte-for-byte, not a different one.
            prospects = draft.generate_draft_class(season.league_seed, next_number)
        prospects_by_index = {p.index: p for p in prospects}
        drafted_indexes = set(progress["drafted_indexes"])

        if chosen_prospect_index is not None:
            if slot.team_abbr != season.user_team_abbr:
                raise ValueError("It isn't your team's turn to pick")
            if chosen_prospect_index in drafted_indexes:
                raise ValueError("That prospect has already been drafted")
            prospect = prospects_by_index[chosen_prospect_index]
        else:
            # Real, live roster counts (one query) -- cheap and correct,
            # since apply_single_pick_to_db() already wrote every prior
            # pick to the DB for real as it resolved (see draft.py's own
            # docstring for why this store never needs to track counts
            # itself as extra persisted state).
            group_counts = draft._all_teams_group_counts()
            specialists_this_round = sum(
                1 for p in progress["picks"] if p["round"] == slot.round and p["position"] in ("K", "P")
            )
            prospect = draft.resolve_one_pick(
                prospects_by_index, drafted_indexes, slot.team_abbr, group_counts,
                round_num=slot.round, specialists_taken_this_round=specialists_this_round,
                league_seed=season.league_seed, season_number=next_number,
            )

        pick = draft.apply_single_pick_to_db(
            prospect, slot.team_abbr, slot.overall_pick, slot.round, season.league_seed, next_number,
        )
        draft_progress_store.record_pick(next_number, pick, prospect.index)

        if idx + 1 >= len(slots):
            complete_draft_and_advance_season(season)
        return pick


def complete_draft_and_advance_season(season: Season | None = None) -> Season:
    """Runs once the live draft's last slot resolves -- called
    automatically by advance_draft_pick(), not normally called directly.
    Finalizes whoever's left in the class as real free agents
    (draft.finalize_undrafted_to_db), folds the live progress record
    into draft_store.py's permanent per-season record (the exact same
    shape draft.apply_draft_to_db() already produces, so the read-only
    Draft Results review works unchanged for a past season), clears the
    now-resolved class/progress/board stores, and builds the new Season
    -- the second half of what finish_offseason() used to do in one
    shot, before the live draft existed. Same carries-forward-vs-resets
    rules as before (season_number increments, real final standings feed
    the new schedule, user_team_abbr/sfs carry forward, everything else
    per-season is fresh)."""
    with _STATE_LOCK:
        season = season if season is not None else get_season()
        if season.offseason_stage != "draft":
            raise ValueError("No live draft to complete")
        next_number = season.season_number + 1
        from app.services import draft_progress_store, draft_class_store, draft_board_store, draft_store
        progress = draft_progress_store.get(next_number)
        if progress is None:
            raise ValueError("No live draft to complete")
        slots = draft.draft_slots(progress["order"])
        if progress["current_pick_index"] < len(slots):
            raise ValueError("The draft isn't fully resolved yet")

        prospects = draft_class_store.get_class(next_number) or draft.generate_draft_class(season.league_seed, next_number)
        prospects_by_index = {p.index: p for p in prospects}
        drafted_indexes = set(progress["drafted_indexes"])
        undrafted_count = draft.finalize_undrafted_to_db(prospects_by_index, drafted_indexes, season.league_seed, next_number)
        draft_store.record_draft(next_number, progress["order"], progress["picks"], undrafted_count)
        draft_progress_store.clear(next_number)
        draft_class_store.clear_class(next_number)
        draft_board_store.clear_season(next_number)

        undrafted_pool.decrement_and_expire()
        depth_chart.clear_starters_cache()

        prior_standings = playoffs.final_division_standings(season)
        new_season = _build_season(season.league_seed, season_number=next_number, prior_standings=prior_standings)
        new_season.user_team_abbr = season.user_team_abbr
        new_season.sfs = season.sfs

        # R3d Sec 3.3: this season's PerformanceExpectation, frozen now
        # -- after begin_offseason()'s AI hiring/firing has already
        # settled who's coaching, before any game of the new season has
        # been played. OwnerWinPressure is untouched here on purpose
        # (Sec 3.2: it persists across seasons, only apply_coach_
        # offseason()'s own end-of-season roll changes it).
        from app.services import team_expectations
        team_expectations.compute_and_store(new_season.season_number)

        _compute_and_save_offseason_recap(season, next_number)

        global _season
        _season = new_season
        from app.services import save_service, save_manager
        save_service.save_season(new_season)
        save_manager.sync_active_save_summary()
        return new_season


def _recap_player_row(p: Player) -> dict:
    return {
        "player_id": p.player_id, "name": p.full_name, "position": p.position.value,
        "team_abbr": p.team_abbr, "overall_rating": p.overall_rating, "age": p.age,
    }


def _compute_and_save_offseason_recap(season: Season, next_number: int) -> None:
    """Football-GM-style recap (Brian's ask, 2026-09-13), computed once
    right here -- the one moment every offseason move (progression, free
    agency, the draft) has already landed but the OLD season object
    (real final standings/records) still exists to compare against.
    Saved via offseason_recap_store so /offseason/recap never has to
    recompute or guess at "before" data that's gone by the time anyone
    loads that page. A player who existed before but not after (an
    expired undrafted rookie hard-deleted by undrafted_pool.decrement_
    and_expire(), say) is simply skipped from the delta/new-team lists --
    not a real ongoing player to report on anymore."""
    from app.services import offseason_recap_store, draft_store, undrafted_pool, history_store, team_expectations

    before = offseason_recap_store.get_before_snapshot(season.season_number) or {}
    with get_session() as s:
        after_players = s.exec(select(Player)).all()
        after_rows = {p.player_id: _recap_player_row(p) for p in after_players}

    top_players = sorted(after_rows.values(), key=lambda r: -r["overall_rating"])[:10]

    improving: list[dict] = []
    declining: list[dict] = []
    new_team: list[dict] = []
    for pid, (old_team, old_ovr) in before.items():
        row = after_rows.get(pid)
        if row is None:
            continue  # released/expired/deleted since -- not a real ongoing player anymore
        delta = row["overall_rating"] - old_ovr
        if delta != 0:
            entry = {**row, "delta": delta}
            (improving if delta > 0 else declining).append(entry)
        if old_team and row["team_abbr"] and old_team != row["team_abbr"]:
            new_team.append({**row, "old_team_abbr": old_team})
    improving.sort(key=lambda r: -r["delta"])
    declining.sort(key=lambda r: r["delta"])
    new_team.sort(key=lambda r: -r["overall_rating"])

    # Top Rookies: this year's real draft picks (draft_store, already
    # sorted-by-nothing -- resort by overall_rating) plus any undrafted
    # signee still on a roster (an emergency fill_roster_gaps() pickup) --
    # both real, zero new computation.
    draft_data = draft_store.get_draft(next_number)
    rookies: list[dict] = []
    if draft_data:
        drafted_ids = {pick["player_id"] for pick in draft_data["picks"]}
        for pick in draft_data["picks"]:
            rookies.append({
                "name": pick["name"], "team_abbr": pick["team_abbr"], "position": pick["position"],
                "college": pick["college"], "overall_rating": pick["overall_rating"],
            })
        for pid, row in after_rows.items():
            if pid.startswith(f"draft_{next_number}_") and pid not in drafted_ids and row["team_abbr"]:
                rookies.append({
                    "name": row["name"], "team_abbr": row["team_abbr"], "position": row["position"],
                    "college": None, "overall_rating": row["overall_rating"],
                })
    rookies.sort(key=lambda r: -r["overall_rating"])
    rookies = rookies[:10]

    # Top/Improving/Declining Teams: team_expectations' real roster-
    # strength percentile, frozen once per season (this season's own
    # entry was computed by the PRIOR cycle's call to this same
    # function/compute_and_store, so it already exists) -- a cleaner
    # signal than raw win totals since it isolates roster strength from
    # a lucky/unlucky won-loss record.
    old_expectations = team_expectations.for_season(season.season_number)
    new_expectations = team_expectations.for_season(next_number)
    top_teams = sorted(
        ({"abbr": abbr, "rating_pctile": exp.team_rating_pctile} for abbr, exp in new_expectations.items()),
        key=lambda r: -r["rating_pctile"],
    )[:10]
    team_deltas = []
    for abbr, new_exp in new_expectations.items():
        old_exp = old_expectations.get(abbr)
        if old_exp is None:
            continue
        team_deltas.append({"abbr": abbr, "delta": new_exp.team_rating_pctile - old_exp.team_rating_pctile})
    improving_teams = sorted((t for t in team_deltas if t["delta"] > 0), key=lambda t: -t["delta"])[:10]
    declining_teams = sorted((t for t in team_deltas if t["delta"] < 0), key=lambda t: t["delta"])[:10]

    offseason_recap_store.save_recap(season.season_number, {
        "season_number": season.season_number,
        "top_players": top_players, "improving_players": improving[:10], "declining_players": declining[:10],
        "top_rookies": rookies, "new_team_players": new_team[:10],
        "top_teams": top_teams, "improving_teams": improving_teams, "declining_teams": declining_teams,
    })


def start_new_season() -> Season:
    """Convenience one-shot: begin_offseason() -> advance_offseason_stage()
    -> finish_offseason() -> auto-resolve every live-draft slot (the same
    real AI logic "End" uses, applied here to a draft nobody's watched
    at all -- a legitimate path, not a special case) -> complete_draft_
    and_advance_season(), with no interactive Staff/GM-Desk/Draft pause
    anywhere in between. This is exactly what a caller that doesn't need
    the interactive pauses (tests, or anyone who just wants the whole
    offseason resolved in one call) should use. app/main.py's routes use
    the pieces above separately instead, so the real Staff, GM Desk, and
    Draft screens each get a chance to run between them."""
    with _STATE_LOCK:
        season = begin_offseason()
        advance_offseason_stage()
        finish_offseason(season)
        while current_draft_slot() is not None:
            advance_draft_pick()
        return get_season()
