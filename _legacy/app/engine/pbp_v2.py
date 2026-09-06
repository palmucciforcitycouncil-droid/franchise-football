"""
Play-By-Play Engine v2

A modular, realistic PBP generator that produces NFL-like game sequences
with proper downs, distances, drive outcomes, and clock management.
"""

import json
import random
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlmodel import select, delete

from app.models.sim_models import Game, GameEvent, Team


def generate_for_game(
    db: Session, 
    game: Game, 
    *, 
    season: int, 
    week: int, 
    targets: Optional[Dict[str, Any]] = None
) -> None:
    """
    Generate realistic play-by-play for a completed game.
    
    Clears existing GameEvent rows for the game and generates new ones
    based on deterministic seeding and optional yardage/point targets.
    
    Args:
        db: Database session
        game: Completed Game record with final scores
        season: Season number for seeding
        week: Week number for seeding  
        targets: Optional dict with home/away yardage and point targets
    """
    # Clear existing events for this game
    db.exec(delete(GameEvent).where(GameEvent.game_id == game.id))
    
    # Deterministic seeding
    rng = _create_game_rng(season, week, game.home_team_id, game.away_team_id)
    
    # Get team abbreviations
    home_team = db.exec(select(Team).where(Team.id == game.home_team_id)).first()
    away_team = db.exec(select(Team).where(Team.id == game.away_team_id)).first()
    home_abbr = home_team.abbr if home_team else f"T{game.home_team_id}"
    away_abbr = away_team.abbr if away_team else f"T{game.away_team_id}"
    
    # Generate yardage targets if not provided
    if targets is None:
        targets = _generate_default_targets(rng, game.home_score, game.away_score)
    
    # Generate PBP events
    events = _generate_game_events(
        rng, game, home_abbr, away_abbr, targets
    )
    
    # Write events to database
    for event_data in events:
        event = GameEvent(
            game_id=game.id,
            quarter=event_data["quarter"],
            clock=event_data["clock"],
            down=event_data.get("down"),
            distance=event_data.get("to_go"),
            yard_line=event_data.get("yardline"),
            offense_team_id=event_data.get("offense_team_id"),
            defense_team_id=event_data.get("defense_team_id"),
            yards_gained=event_data.get("yards"),
            event_type=event_data["event_type"],
            description=event_data["description"],
            score_home=event_data["score_home"],
            score_away=event_data["score_away"],
            data_json=json.dumps(event_data.get("data", {}), separators=(",", ":"))
        )
        db.add(event)
    
    db.commit()


def _create_game_rng(season: int, week: int, home_id: int, away_id: int) -> random.Random:
    """Create deterministic RNG for a specific game."""
    base_seed = 2025  # Could be configurable
    game_seed = hash((season, week, home_id, away_id, base_seed)) & 0xFFFFFFFF
    return random.Random(game_seed)


def _generate_default_targets(rng: random.Random, home_points: int, away_points: int) -> Dict[str, Any]:
    """Generate realistic yardage targets based on final scores."""
    # Base yardage per point (typical NFL range)
    ypp_home = rng.triangular(13, 20, 16)
    ypp_away = rng.triangular(13, 20, 16)
    
    # Calculate base yardage from points
    home_total = int(home_points * ypp_home)
    away_total = int(away_points * ypp_away)
    
    # Add some variance (±10%)
    home_total = int(home_total * rng.triangular(0.9, 1.1, 1.0))
    away_total = int(away_total * rng.triangular(0.9, 1.1, 1.0))
    
    # Pass:rush ratio ~2.2:1
    home_pass_ratio = rng.triangular(0.64, 0.74, 0.69)
    away_pass_ratio = rng.triangular(0.64, 0.74, 0.69)
    
    return {
        "home": {
            "total_yards": max(200, min(500, home_total)),
            "pass_yards": int(home_total * home_pass_ratio)
        },
        "away": {
            "total_yards": max(200, min(500, away_total)),
            "pass_yards": int(away_total * away_pass_ratio)
        },
        "home_points": home_points,
        "away_points": away_points
    }


def _generate_game_events(
    rng: random.Random,
    game: Game,
    home_abbr: str,
    away_abbr: str,
    targets: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate the complete sequence of game events."""
    events = []
    
    # Initialize game state
    quarter = 1
    clock = 900  # 15:00
    home_score = 0
    away_score = 0
    
    # Track yardage budgets
    home_total_remaining = targets["home"]["total_yards"]
    home_pass_remaining = targets["home"]["pass_yards"]
    away_total_remaining = targets["away"]["total_yards"]
    away_pass_remaining = targets["away"]["pass_yards"]
    
    # Track scoring events to distribute
    scoring_events = _distribute_scoring_events(rng, targets["home_points"], targets["away_points"])
    
    # Generate drives (~11-12 per team)
    total_drives = rng.randint(20, 24)
    turnovers_count = 0
    
    for drive_num in range(total_drives):
        offense = "home" if drive_num % 2 == 0 else "away"
        offense_team_id = game.home_team_id if offense == "home" else game.away_team_id
        defense_team_id = game.away_team_id if offense == "home" else game.home_team_id
        
        # Drive setup
        down, to_go = 1, 10
        yardline = rng.randint(20, 80)  # Start somewhere on the field
        drive_yards = 0
        plays_in_drive = 0
        
        # Drive loop
        while down <= 4 and plays_in_drive < 12:
            plays_in_drive += 1
            
            # Check budget constraints
            if offense == "home":
                pass_remaining = home_pass_remaining
                total_remaining = home_total_remaining
            else:
                pass_remaining = away_pass_remaining
                total_remaining = away_total_remaining
            
            if pass_remaining <= 0 and total_remaining <= 0:
                break
            
            # Play selection
            play_type = _select_play_type(rng, pass_remaining, total_remaining - pass_remaining)
            
            # Generate play result
            yards, is_sack, complete, advanced_fields = _generate_play_result(rng, play_type)
            
            # Add situational flags
            situational_flags = _generate_situational_flags(rng, down, to_go, yardline, quarter, clock)
            advanced_fields.update(situational_flags)
            
            # Update budgets (only positive yards count against budget)
            if offense == "home":
                if play_type == "pass":
                    home_pass_remaining = max(0, home_pass_remaining - max(0, yards))
                home_total_remaining = max(0, home_total_remaining - max(0, yards))
            else:
                if play_type == "pass":
                    away_pass_remaining = max(0, away_pass_remaining - max(0, yards))
                away_total_remaining = max(0, away_total_remaining - max(0, yards))
            
            drive_yards += yards
            yardline = max(0, min(100, yardline + yards))
            first_down = yards >= to_go
            
            # Emit play event
            play_data = {
                "team": offense,
                "play": play_type,
                "yards": yards,
                "down": down,
                "to_go": to_go,
                "yardline": yardline,
                "first_down": first_down,
                **advanced_fields  # Include all advanced PBP fields
            }
            if is_sack:
                play_data["is_sack"] = True
            if play_type == "pass":
                play_data["complete"] = complete
            
            events.append({
                "quarter": quarter,
                "clock": _format_clock(clock),
                "down": down,
                "to_go": to_go,
                "yardline": yardline,
                "offense_team_id": offense_team_id,
                "defense_team_id": defense_team_id,
                "yards": yards,
                "event_type": "play",
                "description": f"{offense} {play_type}",
                "score_home": home_score,
                "score_away": away_score,
                "data": play_data
            })
            
            # Update clock
            clock -= _get_play_time(rng, play_type, complete)
            
            # Check for quarter end
            if clock <= 0:
                quarter = min(4, quarter + 1)
                clock = 900
                if quarter == 4 and rng.random() < 0.15:
                    break
            
            # Update down and distance
            if first_down:
                down, to_go = 1, 10
            else:
                down += 1
                to_go = max(1, to_go - yards)
            
            # Check for drive end conditions
            if down > 4:
                # Determine drive outcome
                outcome = _determine_drive_outcome(rng, yardline)
                
                if outcome == "punt":
                    punt_yards = _generate_punt_distance(rng)
                    return_yards = _generate_return_yards(rng)
                    
                    # Generate special teams advanced fields
                    st_fields = _generate_special_teams_fields(rng, "punt")
                    
                    events.append({
                        "quarter": quarter,
                        "clock": _format_clock(clock),
                        "offense_team_id": offense_team_id,
                        "defense_team_id": defense_team_id,
                        "event_type": "punt",
                        "description": f"{offense} punt",
                        "score_home": home_score,
                        "score_away": away_score,
                        "data": {
                            "team": offense,
                            "yards": punt_yards,
                            "return_yards": return_yards,
                            **st_fields  # Include special teams advanced fields
                        }
                    })
                    
                elif outcome == "turnover":
                    turnover_type = _choose_turnover_type(rng)
                    turnovers_count += 1
                    
                    events.append({
                        "quarter": quarter,
                        "clock": _format_clock(clock),
                        "offense_team_id": offense_team_id,
                        "defense_team_id": defense_team_id,
                        "event_type": "turnover",
                        "description": f"{offense} {turnover_type}",
                        "score_home": home_score,
                        "score_away": away_score,
                        "data": {
                            "team": offense,
                            "type": turnover_type
                        }
                    })
                    
                else:  # score
                    if scoring_events:
                        scoring_type = scoring_events.pop(0)
                        if scoring_type == "td":
                            if offense == "home":
                                home_score += 7
                            else:
                                away_score += 7
                            
                            td_type = rng.choice(["run", "pass"])
                            events.append({
                                "quarter": quarter,
                                "clock": _format_clock(clock),
                                "offense_team_id": offense_team_id,
                                "defense_team_id": defense_team_id,
                                "event_type": "td",
                                "description": f"{offense} touchdown",
                                "score_home": home_score,
                                "score_away": away_score,
                                "data": {
                                    "team": offense,
                                    "type": td_type
                                }
                            })
                            
                            # PAT attempt
                            pat_good = rng.random() < 0.94  # 94% success rate
                            
                            # Generate special teams advanced fields
                            st_fields = _generate_special_teams_fields(rng, "xp")
                            
                            events.append({
                                "quarter": quarter,
                                "clock": _format_clock(clock),
                                "offense_team_id": offense_team_id,
                                "defense_team_id": defense_team_id,
                                "event_type": "xp",
                                "description": f"{offense} PAT",
                                "score_home": home_score,
                                "score_away": away_score,
                                "data": {
                                    "team": offense,
                                    "good": pat_good,
                                    **st_fields  # Include special teams advanced fields
                                }
                            })
                            
                        elif scoring_type == "fg":
                            if offense == "home":
                                home_score += 3
                            else:
                                away_score += 3
                            
                            fg_distance = rng.randint(25, 55)
                            fg_good = _get_fg_probability(fg_distance)
                            
                            # Generate special teams advanced fields
                            st_fields = _generate_special_teams_fields(rng, "fg")
                            
                            events.append({
                                "quarter": quarter,
                                "clock": _format_clock(clock),
                                "offense_team_id": offense_team_id,
                                "defense_team_id": defense_team_id,
                                "event_type": "fg",
                                "description": f"{offense} field goal",
                                "score_home": home_score,
                                "score_away": away_score,
                                "data": {
                                    "team": offense,
                                    "good": fg_good,
                                    "distance": fg_distance,
                                    **st_fields  # Include special teams advanced fields
                                }
                            })
                            
                        elif scoring_type == "safety":
                            if offense == "home":
                                away_score += 2  # Safety scored by defense
                            else:
                                home_score += 2
                            
                            events.append({
                                "quarter": quarter,
                                "clock": _format_clock(clock),
                                "offense_team_id": defense_team_id,  # Defense scores
                                "defense_team_id": offense_team_id,
                                "event_type": "safety",
                                "description": f"{offense} safety",
                                "score_home": home_score,
                                "score_away": away_score,
                                "data": {
                                    "team": "defense"
                                }
                            })
                
                break  # End this drive
    
    # Ensure minimum turnovers
    while turnovers_count < 3 and rng.random() < 0.3:
        offense = "home" if rng.random() < 0.5 else "away"
        offense_team_id = game.home_team_id if offense == "home" else game.away_team_id
        defense_team_id = game.away_team_id if offense == "home" else game.home_team_id
        turnover_type = _choose_turnover_type(rng)
        
        events.append({
            "quarter": quarter,
            "clock": _format_clock(clock),
            "offense_team_id": offense_team_id,
            "defense_team_id": defense_team_id,
            "event_type": "turnover",
            "description": f"{offense} {turnover_type}",
            "score_home": home_score,
            "score_away": away_score,
            "data": {
                "team": offense,
                "type": turnover_type
            }
        })
        turnovers_count += 1
    
    # Final event
    events.append({
        "quarter": quarter,
        "clock": _format_clock(clock),
        "event_type": "final",
        "description": "Game final",
        "score_home": home_score,
        "score_away": away_score,
        "data": {
            "home": home_abbr,
            "away": away_abbr
        }
    })
    
    return events


def _distribute_scoring_events(rng: random.Random, home_points: int, away_points: int) -> List[str]:
    """Convert point totals into scoring event types."""
    events = []
    
    # Convert points to scoring units
    home_units = _points_to_scoring_units(rng, home_points)
    away_units = _points_to_scoring_units(rng, away_points)
    
    # Interleave home and away events
    all_units = []
    for i in range(max(len(home_units), len(away_units))):
        if i < len(home_units):
            all_units.append(home_units[i])
        if i < len(away_units):
            all_units.append(away_units[i])
    
    return all_units


def _points_to_scoring_units(rng: random.Random, points: int) -> List[str]:
    """Convert total points into realistic scoring units."""
    units = []
    remaining = points
    
    while remaining > 0:
        if remaining >= 7 and rng.random() < 0.65:  # TD preference
            units.append("td")
            remaining -= 7
        elif remaining >= 3 and rng.random() < 0.25:  # FG
            units.append("fg")
            remaining -= 3
        elif remaining >= 2 and rng.random() < 0.05:  # Safety (rare)
            units.append("safety")
            remaining -= 2
        else:
            # Force completion
            if remaining >= 7:
                units.append("td")
                remaining -= 7
            elif remaining >= 3:
                units.append("fg")
                remaining -= 3
            elif remaining >= 2:
                units.append("safety")
                remaining -= 2
            else:
                # Add extra FG for remaining 1 point
                units.append("fg")
                remaining = 0
    
    return units


def _select_play_type(rng: random.Random, pass_remaining: int, rush_remaining: int) -> str:
    """Select play type based on remaining budget."""
    if pass_remaining > rush_remaining and rng.random() < 0.6:
        return "pass"
    else:
        return "run"


def _generate_play_result(rng: random.Random, play_type: str) -> Tuple[int, bool, bool, Dict[str, Any]]:
    """Generate yards gained, play outcome, and advanced PBP fields."""
    advanced_fields = {}
    
    if play_type == "pass":
        # Sack chance (~6-8%)
        if rng.random() < 0.07:
            yards = -rng.randint(1, 8)
            # Generate sack-specific advanced fields
            advanced_fields.update(_generate_sack_fields(rng))
            return yards, True, False, advanced_fields
        else:
            yards = rng.randint(-2, 25)
            complete = rng.random() < 0.65  # ~65% completion rate
            # Generate pass-specific advanced fields
            advanced_fields.update(_generate_pass_fields(rng, complete, yards))
            return yards, False, complete, advanced_fields
    else:  # run
        yards = rng.randint(-2, 12)
        # Generate run-specific advanced fields
        advanced_fields.update(_generate_run_fields(rng, yards))
        return yards, False, True, advanced_fields  # Runs are always "complete"


def _get_play_time(rng: random.Random, play_type: str, complete: bool) -> int:
    """Get realistic play time in seconds."""
    if play_type == "pass" and not complete:
        return rng.randint(0, 8)  # Incomplete pass stops clock briefly
    else:
        return rng.randint(20, 35)  # Normal play time


def _determine_drive_outcome(rng: random.Random, yardline: int) -> str:
    """Determine how a drive ends."""
    # In FG range (inside 35), attempt FG
    if yardline >= 65:  # Inside opponent's 35
        if rng.random() < 0.8:  # 80% chance to attempt FG
            return "score"
    
    # Otherwise, punt most of the time
    x = rng.random()
    if x < 0.40:  # 40% punts
        return "punt"
    elif x < 0.55:  # 15% turnovers
        return "turnover"
    else:  # 45% scores
        return "score"


def _choose_turnover_type(rng: random.Random) -> str:
    """Choose between interception or fumble."""
    return "interception" if rng.random() < 0.65 else "fumble"


def _generate_punt_distance(rng: random.Random) -> int:
    """Generate realistic punt distance."""
    return int(rng.gauss(45, 8))  # Mean 45 yards, std 8


def _generate_return_yards(rng: random.Random) -> int:
    """Generate realistic return yards."""
    return max(0, int(rng.gauss(8, 6)))  # Mean 8 yards, std 6


def _get_fg_probability(distance: int) -> bool:
    """Get field goal make probability by distance."""
    if distance <= 30:
        return 0.99
    elif distance <= 39:
        return 0.95
    elif distance <= 49:
        return 0.85
    elif distance <= 55:
        return 0.70
    else:
        return 0.50


def _format_clock(seconds: int) -> str:
    """Format seconds as MM:SS clock."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def _generate_sack_fields(rng: random.Random) -> Dict[str, Any]:
    """Generate advanced fields for sack plays."""
    fields = {}
    
    # Offensive line responsibility
    fields["ol_block"] = {
        "blocker_id": rng.randint(1000, 1999) if rng.random() < 0.8 else None,
        "assignment": "pass_pro",
        "beaten_by_id": rng.randint(2000, 2999) if rng.random() < 0.7 else None,
        "outcome": rng.choice(["pressure", "hit", "sack"])
    }
    
    # Front-seven attribution
    num_pressures = rng.randint(1, 3)
    fields["pressures_by_ids"] = [rng.randint(2000, 2999) for _ in range(num_pressures)]
    
    num_hits = rng.randint(1, 2)
    fields["hits_by_ids"] = [rng.randint(2000, 2999) for _ in range(num_hits)]
    
    # Sack split (sum to 1.0)
    sack_defenders = rng.randint(1, 2)
    shares = [rng.random() for _ in range(sack_defenders)]
    total_share = sum(shares)
    normalized_shares = [s / total_share for s in shares]
    fields["sack_split"] = [(rng.randint(2000, 2999), share) for share in normalized_shares]
    
    return fields


def _generate_pass_fields(rng: random.Random, complete: bool, yards: int) -> Dict[str, Any]:
    """Generate advanced fields for pass plays."""
    fields = {}
    
    # Offensive line responsibility
    if rng.random() < 0.15:  # 15% chance of pressure/hit
        fields["ol_block"] = {
            "blocker_id": rng.randint(1000, 1999) if rng.random() < 0.8 else None,
            "assignment": "pass_pro",
            "beaten_by_id": rng.randint(2000, 2999) if rng.random() < 0.6 else None,
            "outcome": rng.choice(["win", "pressure", "hit"])
        }
        
        # Front-seven attribution for pressure
        if rng.random() < 0.3:
            fields["pressures_by_ids"] = [rng.randint(2000, 2999)]
    
    # Coverage / Secondary
    fields["targeted_db_id"] = rng.randint(2000, 2999) if rng.random() < 0.8 else None
    fields["coverage_type"] = rng.choice(["man", "zone"])
    
    if complete:
        fields["coverage_result"] = "caught"
        fields["completions_allowed"] = 1
        fields["yards_allowed"] = yards
        # YAC is typically 30-40% of total yards
        yac = int(yards * rng.uniform(0.3, 0.4))
        fields["yac_allowed"] = yac
    else:
        fields["coverage_result"] = rng.choice(["defended", "incomplete"])
        if rng.random() < 0.15:  # 15% of incompletions are PBUs
            fields["pass_breakup_by_id"] = rng.randint(2000, 2999)
    
    return fields


def _generate_run_fields(rng: random.Random, yards: int) -> Dict[str, Any]:
    """Generate advanced fields for run plays."""
    fields = {}
    
    # Offensive line responsibility
    if rng.random() < 0.2:  # 20% chance of TFL or pressure
        fields["ol_block"] = {
            "blocker_id": rng.randint(1000, 1999) if rng.random() < 0.8 else None,
            "assignment": "run_block",
            "beaten_by_id": rng.randint(2000, 2999) if rng.random() < 0.4 else None,
            "outcome": rng.choice(["win", "tfl"])
        }
        
        if yards < 0:  # TFL
            fields["tfl_by_ids"] = [rng.randint(2000, 2999)]
    
    # Tackling attribution
    tackler_id = rng.randint(2000, 2999) if rng.random() < 0.8 else None
    fields["tackler_id"] = tackler_id
    
    if rng.random() < 0.3:  # 30% chance of assist tackler
        fields["assist_tackler_id"] = rng.randint(2000, 2999)
    
    # Missed tackles
    if rng.random() < 0.05:  # 5% chance of missed tackle
        fields["missed_tackle_by_ids"] = [rng.randint(2000, 2999)]
    
    # Broken tackles
    if yards > 5 and rng.random() < 0.2:  # 20% chance on good runs
        fields["broken_tackle"] = rng.randint(1, 2)
    
    return fields


def _generate_situational_flags(rng: random.Random, down: int, to_go: int, yardline: int, quarter: int, clock: int) -> Dict[str, Any]:
    """Generate situational flags for plays."""
    fields = {}
    
    # Down flags
    fields["is_third_down"] = (down == 3)
    fields["is_fourth_down"] = (down == 4)
    
    # Field position flags
    fields["is_red_zone"] = (yardline <= 20)
    fields["is_goal_to_go"] = (yardline <= 10)
    
    # Time flags
    fields["is_two_minute"] = (quarter >= 4 and clock <= 120)
    fields["is_hurry_up"] = (quarter >= 4 and clock <= 60 and rng.random() < 0.3)
    
    # Garbage time (simplified: Q4 with large lead)
    fields["is_garbage_time_excluded"] = False  # Would need game score context
    
    return fields


def _generate_special_teams_fields(rng: random.Random, event_type: str) -> Dict[str, Any]:
    """Generate advanced fields for special teams plays."""
    fields = {}
    
    if event_type == "punt":
        fields["kick_type"] = "punt"
        fields["punter_id"] = rng.randint(1000, 1999) if rng.random() < 0.8 else None
        fields["returner_id"] = rng.randint(2000, 2999) if rng.random() < 0.8 else None
        fields["hang_time_ms"] = rng.randint(3500, 5500)  # 3.5-5.5 seconds
        fields["net_yards"] = rng.randint(35, 50)
        fields["in_20"] = rng.random() < 0.3  # 30% inside 20
        fields["fair_catch"] = rng.random() < 0.15  # 15% fair catch
        fields["touchback"] = rng.random() < 0.1  # 10% touchback
        
    elif event_type == "fg":
        fields["kick_type"] = "fg"
        fields["kicker_id"] = rng.randint(1000, 1999) if rng.random() < 0.8 else None
        fields["kick_distance"] = rng.randint(25, 55)
        fields["blocked"] = rng.random() < 0.02  # 2% blocked
        fields["blocked_by_id"] = rng.randint(2000, 2999) if fields["blocked"] else None
        
    elif event_type == "xp":
        fields["kick_type"] = "xp"
        fields["kicker_id"] = rng.randint(1000, 1999) if rng.random() < 0.8 else None
        fields["kick_distance"] = 33  # Standard XP distance
        fields["blocked"] = rng.random() < 0.01  # 1% blocked
        
    elif event_type == "kickoff":
        fields["kick_type"] = "kickoff"
        fields["kicker_id"] = rng.randint(1000, 1999) if rng.random() < 0.8 else None
        fields["returner_id"] = rng.randint(2000, 2999) if rng.random() < 0.8 else None
        fields["kick_distance"] = rng.randint(60, 75)
        fields["touchback"] = rng.random() < 0.6  # 60% touchback
        fields["return_yards"] = rng.randint(0, 30) if not fields["touchback"] else 0
    
    return fields


# Major heuristics and tuning knobs:
# - Punt rate: ~40% of drives (adjustable in _determine_drive_outcome)
# - Turnover rate: ~15% of drives, minimum 3 per game
# - Sack rate: ~7% of pass plays
# - Pass completion rate: ~65%
# - FG make rates: 99% inside 30, 95% 30-39, 85% 40-49, 70% 50-55, 50% beyond
# - Play time: 0-8s incomplete passes, 20-35s normal plays
# - Pass:rush ratio: ~2.2:1 baseline with variance
# - Drive length: 12 plays max, budget-aware termination
# - Clock management: 15:00 per quarter, realistic consumption
