from dataclasses import dataclass
import random
from typing import Optional

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
