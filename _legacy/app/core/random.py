from __future__ import annotations
import random
from typing import Optional
from .config import settings

class SeededRNG:
    """
    Deterministic RNG helper. Use one instance per simulation run
    to guarantee reproducibility given the same seed.
    """
    def __init__(self, seed: Optional[int] = None) -> None:
        self._seed = settings.default_seed if seed is None else seed
        self._rng = random.Random(self._seed)

    @property
    def seed(self) -> int:
        return self._seed

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def random(self) -> float:
        return self._rng.random()

    def choice(self, seq):
        return self._rng.choice(seq)

    def shuffle(self, x) -> None:
        self._rng.shuffle(x)
