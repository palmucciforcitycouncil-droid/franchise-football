"""
Helper functions for advanced stats calculations.
Safe division, rate calculations, and derived metrics.
"""

from typing import Union


def safe_divide(numerator: Union[int, float], denominator: Union[int, float], 
                default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    if denominator == 0:
        return default
    return float(numerator) / float(denominator)


def calculate_completion_percentage(completions: int, attempts: int) -> float:
    """Calculate completion percentage."""
    return safe_divide(completions * 100, attempts)


def calculate_passer_rating(completions: int, attempts: int, yards: int, 
                          touchdowns: int, interceptions: int) -> float:
    """Calculate NFL passer rating."""
    if attempts == 0:
        return 0.0
    
    # Completion percentage component
    comp_pct = safe_divide(completions, attempts)
    a = (comp_pct - 0.3) * 5
    
    # Yards per attempt component  
    ypa = safe_divide(yards, attempts)
    b = (ypa - 3) * 0.25
    
    # Touchdown percentage component
    td_pct = safe_divide(touchdowns, attempts)
    c = td_pct * 20
    
    # Interception percentage component
    int_pct = safe_divide(interceptions, attempts)
    d = 2.375 - (int_pct * 25)
    
    # Clamp values between 0 and 2.375
    a = max(0, min(2.375, a))
    b = max(0, min(2.375, b))
    c = max(0, min(2.375, c))
    d = max(0, min(2.375, d))
    
    return safe_divide((a + b + c + d) * 100, 6)


def calculate_yards_per_attempt(yards: int, attempts: int) -> float:
    """Calculate yards per attempt."""
    return safe_divide(yards, attempts)


def calculate_yards_per_carry(yards: int, carries: int) -> float:
    """Calculate yards per carry."""
    return safe_divide(yards, carries)


def calculate_yards_per_reception(yards: int, receptions: int) -> float:
    """Calculate yards per reception."""
    return safe_divide(yards, receptions)


def calculate_net_punt_average(net_yards: int, punts: int) -> float:
    """Calculate net punt average."""
    return safe_divide(net_yards, punts)


def calculate_field_goal_percentage(made: int, attempted: int) -> float:
    """Calculate field goal percentage."""
    return safe_divide(made * 100, attempted)


def calculate_third_down_percentage(conversions: int, attempts: int) -> float:
    """Calculate third down conversion percentage."""
    return safe_divide(conversions * 100, attempts)


def calculate_red_zone_percentage(touchdowns: int, attempts: int) -> float:
    """Calculate red zone touchdown percentage."""
    return safe_divide(touchdowns * 100, attempts)


def calculate_epa_per_play(epa_total: float, plays: int) -> float:
    """Calculate EPA per play."""
    return safe_divide(epa_total, plays)


def calculate_success_rate(successful_plays: int, total_plays: int) -> float:
    """Calculate success rate percentage."""
    return safe_divide(successful_plays * 100, total_plays)


def calculate_dvoa_equivalent(stat_value: float, league_average: float, 
                             league_std: float) -> float:
    """Calculate DVOA-style percentage above/below average."""
    if league_std == 0:
        return 0.0
    return safe_divide((stat_value - league_average) * 100, league_std)


def calculate_approximate_value(base_stats: dict) -> float:
    """Calculate approximate value based on key stats."""
    # Simplified AV calculation
    value = 0.0
    
    # QB value
    if 'pass_yards' in base_stats:
        value += base_stats['pass_yards'] * 0.01
    if 'pass_touchdowns' in base_stats:
        value += base_stats['pass_touchdowns'] * 2.0
    if 'interceptions' in base_stats:
        value -= base_stats['interceptions'] * 1.5
    
    # RB value
    if 'rush_yards' in base_stats:
        value += base_stats['rush_yards'] * 0.02
    if 'rush_touchdowns' in base_stats:
        value += base_stats['rush_touchdowns'] * 3.0
    
    # WR/TE value
    if 'receiving_yards' in base_stats:
        value += base_stats['receiving_yards'] * 0.015
    if 'receiving_touchdowns' in base_stats:
        value += base_stats['receiving_touchdowns'] * 2.5
    
    # Defensive value
    if 'tackles' in base_stats:
        value += base_stats['tackles'] * 0.1
    if 'sacks' in base_stats:
        value += base_stats['sacks'] * 2.0
    if 'interceptions_caught' in base_stats:
        value += base_stats['interceptions_caught'] * 3.0
    
    return max(0.0, value)
