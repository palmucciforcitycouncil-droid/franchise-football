from __future__ import annotations
import os

def use_pbp_v2() -> bool:
    """Check if PBP v2 feature is enabled via environment variable."""
    return os.environ.get("USE_PBP_V2", "false").lower() in ("1", "true", "yes", "on")

