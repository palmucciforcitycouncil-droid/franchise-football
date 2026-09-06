from app.engine.rng import RNG
from app.engine.rating import TeamRatings
from app.engine.game_sim import TeamSim, simulate_game
from app.engine.tuning import TARGETS as T

def mk(off=70, de=70, st=60, rb=0.5, ag=0.5, pace=0.5):
    return TeamRatings(offense=off, defense=de, special=st, run_bias=rb, aggression=ag, pace=pace)

def test_distributions_within_bands():
    rng = RNG.with_seed(2025)
    h = TeamSim("H","H", mk())
    a = TeamSim("A","A", mk())
    N = 200
    pts_h=pts_a=plays=yards=tos=0
    for _ in range(N):
        r = simulate_game(rng, h, a)
        pts_h += r.home_score; pts_a += r.away_score
        ht = r.home_totals; at = r.away_totals  # type: ignore[attr-defined]
        plays += ht.plays + at.plays
        yards += ht.yards + at.yards
        tos += ht.turnovers + at.turnovers
    g_teams = 2*N
    ppt = (pts_h+pts_a)/g_teams
    ppt_ok = (T.pts_per_team_min <= ppt <= T.pts_per_team_max)
    ypp = yards / max(1, plays)
    ypp_ok = (T.ypp_min <= ypp <= T.ypp_max)
    topg = tos / N / 2.0
    to_ok = (T.to_per_team_min <= topg <= T.to_per_team_max)
    assert ppt_ok and ypp_ok and to_ok
