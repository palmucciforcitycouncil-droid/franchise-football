from __future__ import annotations
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

SCHEMA_VERSION = "1.0"

class SaveBundle(BaseModel):
    """
    Complete league snapshot with versioned schema.
    Contains all league data organized by category.
    """
    schema_version: str
    meta: Dict[str, Any]

    # Core league data
    teams: List[Dict[str, Any]] = []
    players: List[Dict[str, Any]] = []
    player_contracts: List[Dict[str, Any]] = []
    player_contract_asks: List[Dict[str, Any]] = []
    trade_block: List[Dict[str, Any]] = []

    # Coaching data
    coaches: List[Dict[str, Any]] = []
    coach_contracts: List[Dict[str, Any]] = []
    coach_asks: List[Dict[str, Any]] = []
    coach_offers: List[Dict[str, Any]] = []

    # Coach focus system
    coach_focus_assignments: List[Dict[str, Any]] = []
    team_weekly_focus_effects: List[Dict[str, Any]] = []
    team_season_focus_tallies: List[Dict[str, Any]] = []

    # Gameplan system
    gameplan_selections: List[Dict[str, Any]] = []
    gameplan_traces: List[Dict[str, Any]] = []

    # League structure
    standings: List[Dict[str, Any]] = []          # optional if present in your project
    schedule: List[Dict[str, Any]] = []           # optional
    results: List[Dict[str, Any]] = []            # optional box scores / summaries

    # Awards and records
    awards_weekly: List[Dict[str, Any]] = []      # optional
    awards_annual: List[Dict[str, Any]] = []      # optional
    hof_inductees: List[Dict[str, Any]] = []      # optional
    records_single_season: List[Dict[str, Any]] = []  # optional
    records_career: List[Dict[str, Any]] = []         # optional

