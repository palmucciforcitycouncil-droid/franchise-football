"""
A deterministic phrasing picker shared by Weekly Headlines (GDD Sec 12)
and the Scouting Panel prose summaries (ROADMAP.md Sec4e, both scoped
2026-09-12) -- the one small piece of infrastructure both features need
instead of a live LLM call. Given the same LEAGUE_SEED and the same
real inputs, the same phrasing is picked every time (GDD Sec 1.3's
Determinism & Seeding Policy), the same way every other seeded draw in
this engine already works (app.engine.rng.stable_seed).

Not a general-purpose i18n/templating system -- just enough to pick one
of N real phrasings for a category and fill in real values via
str.format. If a template references a key `values` doesn't have,
that's a real bug in the template bank, not something to swallow -- the
caller sees the KeyError.
"""
from __future__ import annotations

from app.engine.rng import stable_seed


def pick_and_render(templates: dict[str, list[str]], category: str, seed_key: tuple, **values) -> str:
    """templates: {category: [template, ...]}, each template a plain
    str.format() string. seed_key: whatever makes this specific pick
    reproducible (e.g. (league_seed, season_number, week, event_key)) --
    the caller's job to make it unique enough that two different real
    events in the same category don't always land on the same variant."""
    variants = templates[category]
    index = stable_seed(*seed_key, category) % len(variants)
    return variants[index].format(**values)
