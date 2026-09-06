"""
Garbage Time Detection Helper

Implements GDD-defined garbage time logic for excluding plays from certain statistical calculations.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class GameState:
    """Current state of the game for garbage time detection."""
    quarter: int
    clock_seconds: int
    home_score: int
    away_score: int
    home_team_id: int
    away_team_id: int

class GarbageTimeDetector:
    """Detects garbage time situations based on GDD rules."""
    
    # GDD-defined thresholds
    GARBAGE_TIME_SCORE_DIFF_Q4 = 21  # 21+ point lead in Q4
    GARBAGE_TIME_SCORE_DIFF_Q3 = 28  # 28+ point lead in Q3
    GARBAGE_TIME_SCORE_DIFF_Q2 = 35  # 35+ point lead in Q2
    GARBAGE_TIME_SCORE_DIFF_Q1 = 42  # 42+ point lead in Q1
    
    # Clock thresholds (seconds remaining)
    GARBAGE_TIME_CLOCK_Q4 = 300  # 5 minutes in Q4
    GARBAGE_TIME_CLOCK_Q3 = 600  # 10 minutes in Q3
    GARBAGE_TIME_CLOCK_Q2 = 900  # 15 minutes in Q2
    GARBAGE_TIME_CLOCK_Q1 = 1200  # 20 minutes in Q1
    
    def __init__(self):
        self.garbage_time_thresholds = {
            1: (self.GARBAGE_TIME_SCORE_DIFF_Q1, self.GARBAGE_TIME_CLOCK_Q1),
            2: (self.GARBAGE_TIME_SCORE_DIFF_Q2, self.GARBAGE_TIME_CLOCK_Q2),
            3: (self.GARBAGE_TIME_SCORE_DIFF_Q3, self.GARBAGE_TIME_CLOCK_Q3),
            4: (self.GARBAGE_TIME_SCORE_DIFF_Q4, self.GARBAGE_TIME_CLOCK_Q4),
        }
    
    def is_garbage_time(self, game_state: GameState, offense_team_id: int) -> bool:
        """
        Determine if the current play is in garbage time.
        
        Args:
            game_state: Current state of the game
            offense_team_id: ID of the offensive team
            
        Returns:
            True if the play is in garbage time, False otherwise
        """
        # Calculate score difference from offense perspective
        if offense_team_id == game_state.home_team_id:
            score_diff = game_state.home_score - game_state.away_score
        else:
            score_diff = game_state.away_score - game_state.home_score
        
        # Get thresholds for current quarter
        score_threshold, clock_threshold = self.garbage_time_thresholds.get(
            game_state.quarter, (self.GARBAGE_TIME_SCORE_DIFF_Q4, self.GARBAGE_TIME_CLOCK_Q4)
        )
        
        # Check if score difference exceeds threshold
        if abs(score_diff) >= score_threshold:
            # Check if enough time remains for comeback
            if game_state.clock_seconds <= clock_threshold:
                return True
        
        return False
    
    def is_garbage_time_for_team(self, game_state: GameState, team_id: int) -> bool:
        """
        Determine if the current situation is garbage time for a specific team.
        
        Args:
            game_state: Current state of the game
            team_id: ID of the team to check
            
        Returns:
            True if the situation is garbage time for the team, False otherwise
        """
        # Calculate score difference from team perspective
        if team_id == game_state.home_team_id:
            score_diff = game_state.home_score - game_state.away_score
        else:
            score_diff = game_state.away_score - game_state.home_score
        
        # Get thresholds for current quarter
        score_threshold, clock_threshold = self.garbage_time_thresholds.get(
            game_state.quarter, (self.GARBAGE_TIME_SCORE_DIFF_Q4, self.GARBAGE_TIME_CLOCK_Q4)
        )
        
        # Check if team is behind by enough and time is running out
        if score_diff <= -score_threshold and game_state.clock_seconds <= clock_threshold:
            return True
        
        return False
    
    def get_garbage_time_reason(self, game_state: GameState, offense_team_id: int) -> Optional[str]:
        """
        Get the reason why a play is considered garbage time.
        
        Args:
            game_state: Current state of the game
            offense_team_id: ID of the offensive team
            
        Returns:
            String describing the garbage time reason, or None if not garbage time
        """
        if not self.is_garbage_time(game_state, offense_team_id):
            return None
        
        # Calculate score difference from offense perspective
        if offense_team_id == game_state.home_team_id:
            score_diff = game_state.home_score - game_state.away_score
        else:
            score_diff = game_state.away_score - game_state.home_score
        
        # Get thresholds for current quarter
        score_threshold, clock_threshold = self.garbage_time_thresholds.get(
            game_state.quarter, (self.GARBAGE_TIME_SCORE_DIFF_Q4, self.GARBAGE_TIME_CLOCK_Q4)
        )
        
        if abs(score_diff) >= score_threshold and game_state.clock_seconds <= clock_threshold:
            return f"Q{game_state.quarter}: {abs(score_diff)}pt lead, {game_state.clock_seconds}s remaining"
        
        return None

def is_garbage_time_play(event_data: Dict[str, Any], game_state: GameState) -> bool:
    """
    Convenience function to check if a play event is in garbage time.
    
    Args:
        event_data: PBP event data dictionary
        game_state: Current state of the game
        
    Returns:
        True if the play is in garbage time, False otherwise
    """
    detector = GarbageTimeDetector()
    
    # Extract offense team ID from event data
    offense_team_id = event_data.get("offense_team_id")
    if not offense_team_id:
        return False
    
    return detector.is_garbage_time(game_state, offense_team_id)

def should_exclude_from_stats(event_data: Dict[str, Any], game_state: GameState) -> bool:
    """
    Determine if a play should be excluded from statistical calculations.
    
    Args:
        event_data: PBP event data dictionary
        game_state: Current state of the game
        
    Returns:
        True if the play should be excluded, False otherwise
    """
    # Check if play is already marked as garbage time excluded
    if event_data.get("is_garbage_time_excluded", False):
        return True
    
    # Check if play is in garbage time
    if is_garbage_time_play(event_data, game_state):
        return True
    
    return False

def get_garbage_time_stats(game_events: list, game_state: GameState) -> Dict[str, int]:
    """
    Calculate garbage time statistics for a game.
    
    Args:
        game_events: List of PBP events for the game
        game_state: Current state of the game
        
    Returns:
        Dictionary with garbage time statistics
    """
    detector = GarbageTimeDetector()
    
    stats = {
        "total_plays": 0,
        "garbage_time_plays": 0,
        "garbage_time_excluded": 0,
        "garbage_time_by_quarter": {1: 0, 2: 0, 3: 0, 4: 0},
        "garbage_time_by_team": {},
    }
    
    for event in game_events:
        if event.get("event_type") != "play":
            continue
        
        stats["total_plays"] += 1
        
        # Check if play is in garbage time
        offense_team_id = event.get("offense_team_id")
        if offense_team_id and detector.is_garbage_time(game_state, offense_team_id):
            stats["garbage_time_plays"] += 1
            stats["garbage_time_by_quarter"][game_state.quarter] += 1
            
            # Track by team
            team_id = offense_team_id
            if team_id not in stats["garbage_time_by_team"]:
                stats["garbage_time_by_team"][team_id] = 0
            stats["garbage_time_by_team"][team_id] += 1
        
        # Check if play is marked as excluded
        if event.get("is_garbage_time_excluded", False):
            stats["garbage_time_excluded"] += 1
    
    return stats

# Global detector instance for convenience
garbage_time_detector = GarbageTimeDetector()
