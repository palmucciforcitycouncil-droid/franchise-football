from app.core.random import SeededRNG

def test_seeded_rng_reproducible():
    r1 = SeededRNG(seed=123)
    r2 = SeededRNG(seed=123)
    seq1 = [r1.randint(0, 100) for _ in range(8)]
    seq2 = [r2.randint(0, 100) for _ in range(8)]
    assert seq1 == seq2, "RNG with the same seed must be reproducible"

def test_seed_default_config_smoke():
    r = SeededRNG()  # uses DEFAULT_SEED from settings
    n = r.randint(1, 10)
    assert 1 <= n <= 10
