"""
Correlation utilities for season sanity checks.
"""

from __future__ import annotations
from typing import List, Tuple, Optional
import math


def _pairwise(xs: List[float], ys: List[float]) -> Tuple[float, float, float]:
    """Calculate pairwise correlation coefficient."""
    n = min(len(xs), len(ys))
    if n == 0:
        return (0.0, 0.0, 0.0)
    xm = sum(xs) / n
    ym = sum(ys) / n
    num = sum((x - xm) * (y - ym) for x, y in zip(xs[:n], ys[:n]))
    xd = math.sqrt(sum((x - xm) ** 2 for x in xs[:n]))
    yd = math.sqrt(sum((y - ym) ** 2 for y in ys[:n]))
    denom = xd * yd if xd > 1e-12 and yd > 1e-12 else 1.0
    r = num / denom
    return (r, xm, ym)


def spearman_rank(xs: List[float], ys: List[float]) -> float:
    """Calculate Spearman rank correlation coefficient."""
    def ranks(vs):
        pairs = sorted((v, i) for i, v in enumerate(vs))
        rks = [0] * len(vs)
        i = 0
        while i < len(pairs):
            j = i
            while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
                j += 1
            # average rank for ties
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                rks[pairs[k][1]] = avg
            i = j + 1
        return rks
    
    if not xs or not ys or len(xs) != len(ys):
        return 0.0
    
    rx = ranks(xs)
    ry = ranks(ys)
    r, _, _ = _pairwise(rx, ry)
    return r
