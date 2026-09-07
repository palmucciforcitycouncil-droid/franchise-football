from dataclasses import dataclass
import hashlib
import random
from typing import Optional


def stable_seed(*parts: object) -> int:
    """A deterministic 32-bit seed derived from `parts`, stable across
    processes and machines -- unlike Python's builtin `hash()` on a tuple
    containing strings, which is randomized per-process by default
    (PYTHONHASHSEED) and therefore gives a DIFFERENT value every time the
    server restarts. Several call sites (schedule generation, season and
    single-game simulation) used to seed their RNG with plain `hash((...))
    & 0xFFFFFFFF`, which meant the exact same matchup produced a different
    simulated result across server restarts -- silently contradicting the
    app's own "deterministic: replaying ... always produces this result"
    claim and the GDD Sec 1.3 determinism policy. Uses BLAKE2b (any stable
    hash would do; this one has a convenient fixed digest_size) rather than
    Python's hash() specifically because that's the part that needs to be
    stable, not fast or cryptographically strong."""
    h = hashlib.blake2b(digest_size=4)
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"|")
    return int.from_bytes(h.digest(), "big", signed=False)


@dataclass
class RNG:
    seed: int
    _rng: random.Random

    @classmethod
    def with_seed(cls, seed: int) -> "RNG":
        return cls(seed=seed, _rng=random.Random(seed))

    def r(self) -> random.Random:
        return self._rng

    def choice(self, seq):
        return self._rng.choice(seq)

    def uniform(self, a: float, b: float) -> float:
        return self._rng.uniform(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        return self._rng.gauss(mu, sigma)

    def prob(self, p: float) -> bool:
        return self._rng.random() < p

    def weighted_choice(self, seq, weights):
        return self._rng.choices(seq, weights=weights, k=1)[0]
