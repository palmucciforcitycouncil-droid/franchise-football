"""
The project's one real position-group taxonomy (14 groups), collapsing
Player.position's Madden-granular scheme (see app/models/player.py's
module docstring for why that scheme is kept that granular) into the
groups the Roster page's Team Quota pills, Free Agents filter, and A1's
roster-strength aggregator (app/engine/roster_strength.py) all share.

Originally defined only in app/main.py (as `_QUOTA_GROUP_FOR_POSITION`/
`QUOTA_GROUPS`) for the Team Quota pills and Free Agents filter panel.
Pulled out here so app/engine/roster_strength.py -- which cannot import
from app/main.py without a circular import (main.py imports the engine
layer, not the reverse) -- uses the exact same groups rather than
inventing a second taxonomy. app/main.py now imports from here instead
of defining its own copy.
"""
from __future__ import annotations

from app.models.player import Position

POSITION_TO_GROUP: dict[Position, str] = {
    Position.QB: "QB", Position.HB: "RB",
    Position.WR: "WR", Position.TE: "TE",
    Position.T: "T", Position.G: "G", Position.C: "C",
    Position.EDGE: "EDGE", Position.DT: "DT",
    Position.LB: "LB",
    Position.CB: "CB", Position.S: "S",
    Position.K: "K", Position.P: "P",
}
QUOTA_GROUPS = ["QB", "RB", "WR", "TE", "C", "G", "T", "EDGE", "DT", "LB", "CB", "S", "K", "P"]
