from __future__ import annotations
from typing import Type

def get_player_model() -> Type:
    """
    Always return the canonical Player model for use across the sim.
    If an old module exists, we still map to core_min.Player to avoid schema drift.
    """
    try:
        # Prefer canonical core model
        from app.models.core_min import Player as CorePlayer
        return CorePlayer
    except Exception:
        # Fallback: if core missing, use legacy (unlikely in your repo now)
        from app.models.player import Player as LegacyPlayer  # type: ignore
        return LegacyPlayer

def copy_legacy_fields_to_core(p) -> None:
    """
    If an object was constructed with legacy attributes (position/full_name),
    ensure canonical fields are populated.
    """
    if hasattr(p, "position") and not getattr(p, "pos", None):
        p.pos = p.position  # type: ignore
    if hasattr(p, "full_name") and not getattr(p, "name", None):
        p.name = p.full_name  # type: ignore
