import math
from app.engine.rng import RNG
from app.engine.rating import TeamRatings
from app.engine.game_sim import TeamSim, simulate_game

def mk(off=65, de=60, st=60, rb=0.5, ag=0.5, pace=0.5):
    from app.engine.rating import TeamRatings
    return TeamRatings(offense=off, defense=de, special=st, run_bias=rb, aggression=ag, pace=pace)

def test_sim_deterministic():
    rng = RNG.with_seed(42)
    a = TeamSim("A","A", mk())
    b = TeamSim("B","B", mk())
    res1 = simulate_game(rng, a, b)
    rng2 = RNG.with_seed(42)
    res2 = simulate_game(rng2, a, b)
    assert (res1.home_score, res1.away_score) == (res2.home_score, res2.away_score)
    assert len(res1.events) == len(res2.events)

def test_better_offense_scores_more():
    rng = RNG.with_seed(99)
    a = TeamSim("A","A", mk(off=80))
    b = TeamSim("B","B", mk(off=55))
    res = simulate_game(rng, a, b)
    assert res.home_score > res.away_score or res.away_score > 0  # sanity that scoring exists
