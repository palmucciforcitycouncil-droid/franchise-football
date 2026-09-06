"""
Penalty Codes Enumeration

Normalized penalty codes for consistent stat tracking across the GDD v3.2 Stat Catalog.
"""

from enum import Enum

class PenaltyCode(Enum):
    """NFL penalty codes with normalized categorization."""
    
    # Offensive penalties
    FALSE_START = "false_start"
    HOLDING_OFFENSE = "holding_offense"
    PASS_INTERFERENCE_OFFENSE = "pass_interference_offense"
    ILLEGAL_FORMATION = "illegal_formation"
    ILLEGAL_MOTION = "illegal_motion"
    ILLEGAL_SHIFT = "illegal_shift"
    ILLEGAL_SUBSTITUTION = "illegal_substitution"
    ILLEGAL_TOUCHDOWN = "illegal_touchdown"
    ILLEGAL_BLOCK_ABOVE_WAIST = "illegal_block_above_waist"
    ILLEGAL_BLOCK_BELOW_WAIST = "illegal_block_below_waist"
    ILLEGAL_CONTACT = "illegal_contact"
    ILLEGAL_CRACKBACK = "illegal_crackback"
    ILLEGAL_CUT = "illegal_cut"
    ILLEGAL_DOUBLE_TEAM = "illegal_double_team"
    ILLEGAL_HANDS_TO_FACE = "illegal_hands_to_face"
    ILLEGAL_PEEL_BACK = "illegal_peel_back"
    ILLEGAL_PICK = "illegal_pick"
    ILLEGAL_PROCEDURE = "illegal_procedure"
    ILLEGAL_TOUCHDOWN_PASS = "illegal_touchdown_pass"
    ILLEGAL_USE_OF_HANDS = "illegal_use_of_hands"
    INELIGIBLE_DOWNFIELD_PASS = "ineligible_downfield_pass"
    INTENTIONAL_GROUNDING = "intentional_grounding"
    OFFSIDE_OFFENSE = "offside_offense"
    PERSONAL_FOUL_OFFENSE = "personal_foul_offense"
    ROUGHING_PASSER = "roughing_passer"
    TRIPPING_OFFENSE = "tripping_offense"
    UNNECESSARY_ROUGHNESS_OFFENSE = "unnecessary_roughness_offense"
    UNSPORTSMANLIKE_CONDUCT_OFFENSE = "unsportsmanlike_conduct_offense"
    
    # Defensive penalties
    DEFENSIVE_HOLDING = "defensive_holding"
    PASS_INTERFERENCE_DEFENSE = "pass_interference_defense"
    DEFENSIVE_OFFSIDE = "defensive_offside"
    ENCROACHMENT = "encroachment"
    NEUTRAL_ZONE_INFRACTION = "neutral_zone_infraction"
    ROUGHING_KICKER = "roughing_kicker"
    ROUGHING_PUNTER = "roughing_punter"
    ROUGHING_PASSER_DEFENSE = "roughing_passer_defense"
    PERSONAL_FOUL_DEFENSE = "personal_foul_defense"
    UNNECESSARY_ROUGHNESS_DEFENSE = "unnecessary_roughness_defense"
    UNSPORTSMANLIKE_CONDUCT_DEFENSE = "unsportsmanlike_conduct_defense"
    ILLEGAL_CONTACT_DEFENSE = "illegal_contact_defense"
    ILLEGAL_USE_OF_HANDS_DEFENSE = "illegal_use_of_hands_defense"
    ILLEGAL_HANDS_TO_FACE_DEFENSE = "illegal_hands_to_face_defense"
    TRIPPING_DEFENSE = "tripping_defense"
    LEVERAGE = "leverage"
    RUNNING_INTO_KICKER = "running_into_kicker"
    RUNNING_INTO_PUNTER = "running_into_punter"
    
    # Special teams penalties
    FAIR_CATCH_INTERFERENCE = "fair_catch_interference"
    KICK_CATCH_INTERFERENCE = "kick_catch_interference"
    INVALID_FAIR_CATCH_SIGNAL = "invalid_fair_catch_signal"
    INVALID_KICK_FORMATION = "invalid_kick_formation"
    INVALID_SIGNAL = "invalid_signal"
    KICKING_TEAM_PLAYER_OUT_OF_BOUNDS = "kicking_team_player_out_of_bounds"
    RECEIVING_TEAM_PLAYER_OUT_OF_BOUNDS = "receiving_team_player_out_of_bounds"
    
    # General penalties
    DELAY_OF_GAME = "delay_of_game"
    EXCESSIVE_TIMEOUTS = "excessive_timeouts"
    ILLEGAL_FORWARD_PASS = "illegal_forward_pass"
    ILLEGAL_KICK = "illegal_kick"
    ILLEGAL_TOUCH = "illegal_touch"
    ILLEGAL_WEDGE = "illegal_wedge"
    INELIGIBLE_RECEIVER_DOWNFIELD = "ineligible_receiver_downfield"
    INVALID_FORMATION = "invalid_formation"
    INVALID_PLAYER_DOWNFIELD = "invalid_player_downfield"
    INVALID_SNAP = "invalid_snap"
    INVALID_SUBSTITUTION = "invalid_substitution"
    PLAYER_OUT_OF_BOUNDS = "player_out_of_bounds"
    SUBSTITUTION_INFRACTION = "substitution_infraction"
    TOO_MANY_MEN_ON_FIELD = "too_many_men_on_field"
    TOO_MANY_MEN_ON_FIELD_OFFENSE = "too_many_men_on_field_offense"
    TOO_MANY_MEN_ON_FIELD_DEFENSE = "too_many_men_on_field_defense"
    TOO_MANY_MEN_ON_FIELD_SPECIAL_TEAMS = "too_many_men_on_field_special_teams"

class PenaltyCategory(Enum):
    """Categories for penalty analysis."""
    
    OFFENSIVE_LINE = "offensive_line"
    DEFENSIVE_LINE = "defensive_line"
    PASS_COVERAGE = "pass_coverage"
    SPECIAL_TEAMS = "special_teams"
    PROCEDURAL = "procedural"
    PERSONAL_FOUL = "personal_foul"
    UNSPORTSMANLIKE = "unsportsmanlike"

# Mapping of penalty codes to categories
PENALTY_CATEGORIES = {
    # Offensive line penalties
    PenaltyCode.FALSE_START: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.HOLDING_OFFENSE: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_BLOCK_ABOVE_WAIST: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_BLOCK_BELOW_WAIST: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_CONTACT: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_CRACKBACK: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_CUT: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_DOUBLE_TEAM: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_HANDS_TO_FACE: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_PEEL_BACK: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_PICK: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.ILLEGAL_USE_OF_HANDS: PenaltyCategory.OFFENSIVE_LINE,
    PenaltyCode.TRIPPING_OFFENSE: PenaltyCategory.OFFENSIVE_LINE,
    
    # Defensive line penalties
    PenaltyCode.DEFENSIVE_HOLDING: PenaltyCategory.DEFENSIVE_LINE,
    PenaltyCode.DEFENSIVE_OFFSIDE: PenaltyCategory.DEFENSIVE_LINE,
    PenaltyCode.ENCROACHMENT: PenaltyCategory.DEFENSIVE_LINE,
    PenaltyCode.NEUTRAL_ZONE_INFRACTION: PenaltyCategory.DEFENSIVE_LINE,
    PenaltyCode.ILLEGAL_CONTACT_DEFENSE: PenaltyCategory.DEFENSIVE_LINE,
    PenaltyCode.ILLEGAL_USE_OF_HANDS_DEFENSE: PenaltyCategory.DEFENSIVE_LINE,
    PenaltyCode.ILLEGAL_HANDS_TO_FACE_DEFENSE: PenaltyCategory.DEFENSIVE_LINE,
    PenaltyCode.TRIPPING_DEFENSE: PenaltyCategory.DEFENSIVE_LINE,
    PenaltyCode.LEVERAGE: PenaltyCategory.DEFENSIVE_LINE,
    
    # Pass coverage penalties
    PenaltyCode.PASS_INTERFERENCE_OFFENSE: PenaltyCategory.PASS_COVERAGE,
    PenaltyCode.PASS_INTERFERENCE_DEFENSE: PenaltyCategory.PASS_COVERAGE,
    
    # Special teams penalties
    PenaltyCode.FAIR_CATCH_INTERFERENCE: PenaltyCategory.SPECIAL_TEAMS,
    PenaltyCode.KICK_CATCH_INTERFERENCE: PenaltyCategory.SPECIAL_TEAMS,
    PenaltyCode.INVALID_FAIR_CATCH_SIGNAL: PenaltyCategory.SPECIAL_TEAMS,
    PenaltyCode.INVALID_KICK_FORMATION: PenaltyCategory.SPECIAL_TEAMS,
    PenaltyCode.KICKING_TEAM_PLAYER_OUT_OF_BOUNDS: PenaltyCategory.SPECIAL_TEAMS,
    PenaltyCode.RECEIVING_TEAM_PLAYER_OUT_OF_BOUNDS: PenaltyCategory.SPECIAL_TEAMS,
    PenaltyCode.ROUGHING_KICKER: PenaltyCategory.SPECIAL_TEAMS,
    PenaltyCode.ROUGHING_PUNTER: PenaltyCategory.SPECIAL_TEAMS,
    PenaltyCode.RUNNING_INTO_KICKER: PenaltyCategory.SPECIAL_TEAMS,
    PenaltyCode.RUNNING_INTO_PUNTER: PenaltyCategory.SPECIAL_TEAMS,
    
    # Procedural penalties
    PenaltyCode.DELAY_OF_GAME: PenaltyCategory.PROCEDURAL,
    PenaltyCode.EXCESSIVE_TIMEOUTS: PenaltyCategory.PROCEDURAL,
    PenaltyCode.ILLEGAL_FORMATION: PenaltyCategory.PROCEDURAL,
    PenaltyCode.ILLEGAL_MOTION: PenaltyCategory.PROCEDURAL,
    PenaltyCode.ILLEGAL_SHIFT: PenaltyCategory.PROCEDURAL,
    PenaltyCode.ILLEGAL_SUBSTITUTION: PenaltyCategory.PROCEDURAL,
    PenaltyCode.ILLEGAL_PROCEDURE: PenaltyCategory.PROCEDURAL,
    PenaltyCode.INVALID_FORMATION: PenaltyCategory.PROCEDURAL,
    PenaltyCode.INVALID_SNAP: PenaltyCategory.PROCEDURAL,
    PenaltyCode.INVALID_SUBSTITUTION: PenaltyCategory.PROCEDURAL,
    PenaltyCode.SUBSTITUTION_INFRACTION: PenaltyCategory.PROCEDURAL,
    PenaltyCode.TOO_MANY_MEN_ON_FIELD: PenaltyCategory.PROCEDURAL,
    PenaltyCode.TOO_MANY_MEN_ON_FIELD_OFFENSE: PenaltyCategory.PROCEDURAL,
    PenaltyCode.TOO_MANY_MEN_ON_FIELD_DEFENSE: PenaltyCategory.PROCEDURAL,
    PenaltyCode.TOO_MANY_MEN_ON_FIELD_SPECIAL_TEAMS: PenaltyCategory.PROCEDURAL,
    
    # Personal foul penalties
    PenaltyCode.PERSONAL_FOUL_OFFENSE: PenaltyCategory.PERSONAL_FOUL,
    PenaltyCode.PERSONAL_FOUL_DEFENSE: PenaltyCategory.PERSONAL_FOUL,
    PenaltyCode.ROUGHING_PASSER: PenaltyCategory.PERSONAL_FOUL,
    PenaltyCode.ROUGHING_PASSER_DEFENSE: PenaltyCategory.PERSONAL_FOUL,
    PenaltyCode.UNNECESSARY_ROUGHNESS_OFFENSE: PenaltyCategory.PERSONAL_FOUL,
    PenaltyCode.UNNECESSARY_ROUGHNESS_DEFENSE: PenaltyCategory.PERSONAL_FOUL,
    
    # Unsportsmanlike conduct penalties
    PenaltyCode.UNSPORTSMANLIKE_CONDUCT_OFFENSE: PenaltyCategory.UNSPORTSMANLIKE,
    PenaltyCode.UNSPORTSMANLIKE_CONDUCT_DEFENSE: PenaltyCategory.UNSPORTSMANLIKE,
}

def get_penalty_category(penalty_code: PenaltyCode) -> PenaltyCategory:
    """Get the category for a penalty code."""
    return PENALTY_CATEGORIES.get(penalty_code, PenaltyCategory.PROCEDURAL)

def is_offensive_line_penalty(penalty_code: PenaltyCode) -> bool:
    """Check if a penalty is an offensive line penalty."""
    return get_penalty_category(penalty_code) == PenaltyCategory.OFFENSIVE_LINE

def is_defensive_line_penalty(penalty_code: PenaltyCode) -> bool:
    """Check if a penalty is a defensive line penalty."""
    return get_penalty_category(penalty_code) == PenaltyCategory.DEFENSIVE_LINE

def is_pass_coverage_penalty(penalty_code: PenaltyCode) -> bool:
    """Check if a penalty is a pass coverage penalty."""
    return get_penalty_category(penalty_code) == PenaltyCategory.PASS_COVERAGE

def is_special_teams_penalty(penalty_code: PenaltyCode) -> bool:
    """Check if a penalty is a special teams penalty."""
    return get_penalty_category(penalty_code) == PenaltyCategory.SPECIAL_TEAMS
