from __future__ import annotations
from typing import Dict, List

def offense_group(slots: Dict[str, List[int]]) -> List[int]:
    """Extract offensive players from lineup slots."""
    keys = ["QB", "RB", "WR1", "WR2", "WR3", "TE", "LT", "LG", "C", "RG", "RT"]
    out: List[int] = []
    for k in keys:
        out.extend(slots.get(k, [])[:1])  # Only take first (starter)
    return [pid for pid in out if pid and pid > 0]

def defense_group(slots: Dict[str, List[int]]) -> List[int]:
    """Extract defensive players from lineup slots."""
    keys = ["EDGE1", "EDGE2", "DL1", "DL2", "LB1", "LB2", "CB1", "CB2", "S1", "S2"]
    out: List[int] = []
    for k in keys:
        out.extend(slots.get(k, [])[:1])  # Only take first (starter)
    return [pid for pid in out if pid and pid > 0]

def special_group(slots: Dict[str, List[int]]) -> Dict[str, int]:
    """Extract special teams players from lineup slots."""
    return {
        "K": (slots.get("K", [None])[0] or -1),
        "P": (slots.get("P", [None])[0] or -1),
        "LS": (slots.get("LS", [None])[0] or -1),
        "KR": (slots.get("KR", [None])[0] or -1),
        "PR": (slots.get("PR", [None])[0] or -1),
    }

def get_starting_lineup(slots: Dict[str, List[int]]) -> Dict[str, int]:
    """Get starting lineup (first player in each slot)."""
    starters = {}
    for slot, players in slots.items():
        if players and players[0] and players[0] > 0:
            starters[slot] = players[0]
        else:
            starters[slot] = -1
    return starters

def get_backup_lineup(slots: Dict[str, List[int]]) -> Dict[str, List[int]]:
    """Get backup players (all players after the first)."""
    backups = {}
    for slot, players in slots.items():
        if len(players) > 1:
            backups[slot] = [p for p in players[1:] if p and p > 0]
        else:
            backups[slot] = []
    return backups

def get_depth_at_position(slots: Dict[str, List[int]], position: str) -> List[int]:
    """Get all players at a specific position."""
    position_slots = [slot for slot in slots.keys() if slot.startswith(position)]
    players = []
    for slot in position_slots:
        players.extend([p for p in slots.get(slot, []) if p and p > 0])
    return players

def get_offensive_line(slots: Dict[str, List[int]]) -> List[int]:
    """Get offensive line players."""
    oline_slots = ["LT", "LG", "C", "RG", "RT"]
    return [slots.get(slot, [-1])[0] for slot in oline_slots if slots.get(slot, [-1])[0] > 0]

def get_skill_positions(slots: Dict[str, List[int]]) -> List[int]:
    """Get skill position players."""
    skill_slots = ["QB", "RB", "WR1", "WR2", "WR3", "TE"]
    return [slots.get(slot, [-1])[0] for slot in skill_slots if slots.get(slot, [-1])[0] > 0]

def get_defensive_front(slots: Dict[str, List[int]]) -> List[int]:
    """Get defensive front players."""
    front_slots = ["EDGE1", "EDGE2", "DL1", "DL2"]
    return [slots.get(slot, [-1])[0] for slot in front_slots if slots.get(slot, [-1])[0] > 0]

def get_defensive_backs(slots: Dict[str, List[int]]) -> List[int]:
    """Get defensive backs."""
    back_slots = ["LB1", "LB2", "CB1", "CB2", "S1", "S2"]
    return [slots.get(slot, [-1])[0] for slot in back_slots if slots.get(slot, [-1])[0] > 0]

def get_specialists(slots: Dict[str, List[int]]) -> List[int]:
    """Get special teams specialists."""
    specialist_slots = ["K", "P", "LS"]
    return [slots.get(slot, [-1])[0] for slot in specialist_slots if slots.get(slot, [-1])[0] > 0]

def get_returners(slots: Dict[str, List[int]]) -> List[int]:
    """Get return specialists."""
    returner_slots = ["KR", "PR"]
    return [slots.get(slot, [-1])[0] for slot in returner_slots if slots.get(slot, [-1])[0] > 0]

def validate_lineup_completeness(slots: Dict[str, List[int]]) -> Dict[str, List[str]]:
    """Validate that lineup has all required positions filled."""
    issues = {"errors": [], "warnings": []}
    
    # Required positions
    required_positions = ["QB", "K", "P"]
    for pos in required_positions:
        if not slots.get(pos) or not slots[pos] or slots[pos][0] <= 0:
            issues["errors"].append(f"Missing {pos}")
    
    # Check for empty slots
    for slot, players in slots.items():
        if not players or not any(p and p > 0 for p in players):
            issues["warnings"].append(f"Empty slot: {slot}")
    
    return issues

def get_lineup_summary(slots: Dict[str, List[int]]) -> Dict[str, any]:
    """Get summary of lineup composition."""
    total_players = sum(len([p for p in players if p and p > 0]) for players in slots.values())
    filled_slots = sum(1 for players in slots.values() if players and any(p and p > 0 for p in players))
    empty_slots = len(slots) - filled_slots
    
    return {
        "total_players": total_players,
        "filled_slots": filled_slots,
        "empty_slots": empty_slots,
        "offense_players": len(offense_group(slots)),
        "defense_players": len(defense_group(slots)),
        "special_teams": len([p for p in special_group(slots).values() if p > 0])
    }

def get_position_groups(slots: Dict[str, List[int]]) -> Dict[str, List[int]]:
    """Get players grouped by position type."""
    return {
        "offense": offense_group(slots),
        "defense": defense_group(slots),
        "special_teams": list(special_group(slots).values()),
        "offensive_line": get_offensive_line(slots),
        "skill_positions": get_skill_positions(slots),
        "defensive_front": get_defensive_front(slots),
        "defensive_backs": get_defensive_backs(slots),
        "specialists": get_specialists(slots),
        "returners": get_returners(slots)
    }

def get_player_slot_mapping(slots: Dict[str, List[int]]) -> Dict[int, str]:
    """Get mapping of player_id to their primary slot."""
    player_slots = {}
    for slot, players in slots.items():
        if players and players[0] and players[0] > 0:
            player_slots[players[0]] = slot
    return player_slots

def get_slot_depth(slots: Dict[str, List[int]], slot: str) -> int:
    """Get depth at a specific slot."""
    return len([p for p in slots.get(slot, []) if p and p > 0])

def get_total_depth(slots: Dict[str, List[int]]) -> Dict[str, int]:
    """Get depth for all slots."""
    return {slot: get_slot_depth(slots, slot) for slot in slots.keys()}

def is_lineup_complete(slots: Dict[str, List[int]]) -> bool:
    """Check if lineup is complete (all critical positions filled)."""
    critical_positions = ["QB", "K", "P"]
    return all(slots.get(pos) and slots[pos] and slots[pos][0] > 0 for pos in critical_positions)

def get_missing_positions(slots: Dict[str, List[int]]) -> List[str]:
    """Get list of missing critical positions."""
    critical_positions = ["QB", "K", "P"]
    missing = []
    for pos in critical_positions:
        if not slots.get(pos) or not slots[pos] or slots[pos][0] <= 0:
            missing.append(pos)
    return missing

