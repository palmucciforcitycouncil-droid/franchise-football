"""Model export aggregator for convenient imports like:
   from app.models import Team, Player, DepthChart, GameResult
"""

from .team import Team
from .player import Player
from .depth_chart import DepthChart
from .game_result import GameResult
from .player_stats import PlayerStats
from .user_profile import UserProfile

# Optional: expose DB helpers if present; ignore if module layout differs.
try:
    from .database import Base  # and any helpers your code defines
except Exception:
    pass

__all__ = [
    "Team",
    "Player",
    "DepthChart",
    "GameResult",
    "PlayerStats",
    "UserProfile",
]
