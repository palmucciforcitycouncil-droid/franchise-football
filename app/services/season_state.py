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
from app.engine import power_rating, score_fidelity
from app.engine.score_fidelity import SFSState
from app.services import gameplan_store


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

    @property
    def is_complete(self) -> bool:
        return self.current_week > N_WEEKS

    def standings(self) -> list[TeamRecord]:
        return sorted(
            self.records.values(),
            key=lambda r: (-r.win_pct, -r.point_diff, r.location),
        )


def _build_season(league_seed: int) -> Season:
    raw_schedule = generate_season_schedule(league_seed)
    schedule = [
        [WeekGame(home_abbr=h, away_abbr=a) for h, a in week]
        for week in raw_schedule
    ]
    records = {
        t.abbr: TeamRecord(abbr=t.abbr, location=t.location) for t in TEAMS
    }
    return Season(league_seed=league_seed, schedule=schedule, records=records)


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
        week_games = season.schedule[week_num - 1]
        week_total_points = 0
        week_total_teams = 0

        for game in week_games:
            home_info = TEAMS_BY_ABBR[game.home_abbr]
            away_info = TEAMS_BY_ABBR[game.away_abbr]
            home = TeamSim(name=home_info.location, abbr=home_info.abbr,
                            ratings=ratings_for(home_info, season.league_seed))
            away = TeamSim(name=away_info.location, abbr=away_info.abbr,
                            ratings=ratings_for(away_info, season.league_seed))

            home_rec = season.records[game.home_abbr]
            away_rec = season.records[game.away_abbr]

            # Score Fidelity System (GDD Sec 6.2): pre-game win probability
            # from current Team Power Ratings drives each team's EP-anchoring
            # multiplier for this game -- computed BEFORE simulating, using
            # each team's record entering this week (not updated by it).
            win_prob = power_rating.home_win_probability(
                home_rec.power_rating, home_rec.wins, home_rec.games_played,
                away_rec.power_rating, away_rec.wins, away_rec.games_played,
                week_num,
            )

            game_seed = stable_seed(season.league_seed, week_num, game.home_abbr, game.away_abbr)
            rng = RNG.with_seed(game_seed)
            # Consumed from the same seeded rng as the game itself, so a
            # season replay with the same LEAGUE_SEED stays fully
            # deterministic (see score_fidelity.ep_multiplier's docstring).
            home_mult = score_fidelity.ep_multiplier(rng, win_prob, True, season.sfs.scoring_feedback_multiplier)
            away_mult = score_fidelity.ep_multiplier(rng, win_prob, False, season.sfs.scoring_feedback_multiplier)

            # Weekly Gameplan (GDD Sec 10.4.1): only the user's own team
            # ever has one set (app/main.py's /gameplan route only
            # accepts season.user_team_abbr) -- every AI team gets None,
            # which the engine treats as "no override, use the default
            # play-calling AI" (see app/engine/gameplan.py).
            home_gameplan = gameplan_store.get_gameplan(game.home_abbr) if game.home_abbr == season.user_team_abbr else None
            away_gameplan = gameplan_store.get_gameplan(game.away_abbr) if game.away_abbr == season.user_team_abbr else None

            result = simulate_game(rng, home, away, home_mult, away_mult, home_gameplan, away_gameplan)
            game.result = result

            home_rec.points_for += result.home_score
            home_rec.points_against += result.away_score
            away_rec.points_for += result.away_score
            away_rec.points_against += result.home_score
            if result.winner == "home":
                home_rec.wins += 1
                away_rec.losses += 1
            else:
                away_rec.wins += 1
                home_rec.losses += 1

            home_rec.power_rating, away_rec.power_rating = power_rating.update_ratings(
                home_rec.power_rating, away_rec.power_rating, result.home_score, result.away_score,
            )

            week_total_points += result.home_score + result.away_score
            week_total_teams += 2

        season.current_week += 1

        if week_total_teams:
            measured_ppg = week_total_points / week_total_teams
            score_fidelity.weekly_feedback_update(season.sfs, week_num, measured_ppg)

        from app.services import save_service
        save_service.save_season(season)

        return week_num
