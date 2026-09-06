from typing import List
from sqlmodel import Session, select
from app.engine.rng import RNG
from app.engine.game_sim import TeamSim, simulate_game
from app.models.sim_models import SimTeam, SimGame, SimGameEvent
from .standings_service import update_power
from .roster_service import aggregate_team_ratings
from app.engine.rating import TeamRatings
from .stats_service import record_team_game_stats
from .player_stats_service import persist_player_game_logs_for_game

def _team_sim_from_roster(session: Session, t: SimTeam) -> TeamSim:
    agg = aggregate_team_ratings(session, t.id)
    ratings = TeamRatings(
        offense=agg["offense"], defense=agg["defense"], special=agg["special"],
        run_bias=agg["run_bias"], aggression=agg["aggression"], pace=agg["pace"]
    )
    return TeamSim(name=t.name, abbr=t.abbr, ratings=ratings)

def sim_week(session: Session, season: int, week: int, seed: int) -> List[SimGame]:
    rng = RNG.with_seed(seed + week * 9973)
    games = session.query(SimGame).filter(SimGame.season==season, SimGame.week==week).all()

    for g in games:
        if g.is_played: continue
        home = session.query(SimTeam).filter(SimTeam.id == g.home_team_id).first()
        away = session.query(SimTeam).filter(SimTeam.id == g.away_team_id).first()

        hsim = _team_sim_from_roster(session, home)
        asim = _team_sim_from_roster(session, away)

        result = simulate_game(rng, hsim, asim)

        g.home_score = result.home_score
        g.away_score = result.away_score
        g.is_played = True
        session.add(g)
        # events
        for idx, ev in enumerate(result.events):
            session.add(SimGameEvent(game_id=g.id, idx=idx, desc=ev.desc,
                                         clock_left=ev.clock_left, home_score=ev.home_score, away_score=ev.away_score))
        # persist team stats
        record_team_game_stats(session, g, result.home_totals, result.away_totals)
        # NEW: build per-player logs from those team rows
        persist_player_game_logs_for_game(session, g.id)
        # power rating (ELO)
        home.power, away.power = update_power(home.power, away.power, result.home_score, result.away_score)
        session.add(home); session.add(away)

    session.commit()
    return games
