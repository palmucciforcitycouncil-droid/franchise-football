import os
from app.services.importer.generator import make_league, DEFAULT_ROSTER_SIZES

def test_generator_determinism_and_counts():
    seed = 123
    teams1, players1, depth1 = make_league(seed=seed)
    teams2, players2, depth2 = make_league(seed=seed)

    # determinism: same lengths and first few player identities
    assert len(teams1) == len(teams2) == 32
    assert len(players1) == len(players2) == 32 * sum(DEFAULT_ROSTER_SIZES.values())
    assert len(depth1) == len(depth2) == 32 * len(DEFAULT_ROSTER_SIZES)

    # First 5 players identical across runs
    a = [(p.first_name,p.last_name,p.position,p.jersey,p.team_key) for p in players1[:5]]
    b = [(p.first_name,p.last_name,p.position,p.jersey,p.team_key) for p in players2[:5]]
    assert a == b

    # Validate rating ranges and age >= 18
    for p in players1[:100]:  # sample early batch to keep test light
        assert p.age >= 18
        for r in [
            p.speed,p.strength,p.agility,p.throw_power,p.throw_accuracy,
            p.catching,p.tackling,p.awareness,p.potential,p.stamina,
            p.injury_proneness,p.morale
        ]:
            assert 0 <= r <= 100

    # Jersey uniqueness per team (sample first team)
    team_key = f"{teams1[0].location_name}|{teams1[0].nickname}"
    jerseys = [p.jersey for p in players1 if p.team_key == team_key]
    assert len(jerseys) == len(set(jerseys))
