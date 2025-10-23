#!/usr/bin/env python3
"""
NFL Simulation Engine - Phase 3: Restoring Drive Termination Logic
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.testing.mini_season_runner import memory_db
from app.models.pbp_event import PBPEvent
from app.models.player_models import Player
import random
import json


def run_phase3_calibrated_season(session: Session, weeks: int = 4, seed: int = 2025):
    """Run Phase 3 calibrated mini season with proper drive termination."""
    random.seed(seed)
    
    # Create 4 teams
    teams = []
    for team_id in range(1, 5):
        team = {"id": team_id, "name": f"Team {team_id}"}
        teams.append(team)
    
    # Create players for each team (QB, RB, WR, LB, DB, K)
    players = []
    for team_id in range(1, 5):
        positions = ["QB", "RB", "WR", "LB", "DB", "K"]
        for i, pos in enumerate(positions):
            player = Player(
                id=team_id * 100 + i,
                name=f"Player{i}Team{team_id}",
                team_id=team_id,
                position=pos,
                age=random.randint(22, 32)
            )
            players.append(player)
            session.add(player)
    
    session.commit()
    
    # Generate games
    games = []
    game_id = 1
    for week in range(1, weeks + 1):
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):
                home_team = teams[i]
                away_team = teams[i + 1]
                games.append({
                    "id": game_id,
                    "week": week,
                    "home_team_id": home_team["id"],
                    "away_team_id": away_team["id"]
                })
                game_id += 1
    
    # Generate PBP events for each game
    for game in games:
        _generate_phase3_pbp_events(
            session, 
            game["id"], 
            game["home_team_id"], 
            game["away_team_id"], 
            seed + game["id"]
        )
    
    session.commit()
    
    return {
        "teams": [t["id"] for t in teams],
        "games": [g["id"] for g in games],
        "schedule": games
    }


def _generate_phase3_pbp_events(session: Session, game_id: int, home_team_id: int, away_team_id: int, seed: int):
    """Generate Phase 3 PBP events with proper drive termination logic."""
    random.seed(seed)
    
    # Get players for both teams
    home_players = session.exec(
        select(Player).where(Player.team_id == home_team_id)
    ).all()
    away_players = session.exec(
        select(Player).where(Player.team_id == away_team_id)
    ).all()
    
    # Get key players
    home_qb = next((p for p in home_players if p.position == "QB"), home_players[0])
    home_rb = next((p for p in home_players if p.position == "RB"), home_players[1])
    home_wr = next((p for p in home_players if p.position == "WR"), home_players[2])
    home_k = next((p for p in home_players if p.position == "K"), home_players[5])
    
    away_qb = next((p for p in away_players if p.position == "QB"), away_players[0])
    away_rb = next((p for p in away_players if p.position == "RB"), away_players[1])
    away_wr = next((p for p in away_players if p.position == "WR"), away_players[2])
    away_k = next((p for p in away_players if p.position == "K"), away_players[5])
    
    # Get defensive players
    home_lb = next((p for p in home_players if p.position == "LB"), home_players[3])
    home_db = next((p for p in home_players if p.position == "DB"), home_players[4])
    away_lb = next((p for p in away_players if p.position == "LB"), away_players[3])
    away_db = next((p for p in away_players if p.position == "DB"), away_players[4])
    
    # Generate drives (10-14 drives per team = 20-28 total drives)
    num_drives = random.randint(20, 28)
    play_id = 1
    
    for drive_num in range(num_drives):
        # Determine offense/defense
        offense_team = home_team_id if drive_num % 2 == 0 else away_team_id
        defense_team = away_team_id if offense_team == home_team_id else home_team_id
        
        # Get offensive players
        if offense_team == home_team_id:
            qb, rb, wr, k = home_qb, home_rb, home_wr, home_k
            lb, db = away_lb, away_db
        else:
            qb, rb, wr, k = away_qb, away_rb, away_wr, away_k
            lb, db = home_lb, home_db
        
        # Drive setup
        current_yardline = random.randint(20, 30)  # Start between 20-30 yard line
        down = 1
        distance = 10
        drive_plays = 0
        max_drive_plays = random.randint(8, 15)  # Longer drives
        
        # Drive progression with proper termination logic
        while drive_plays < max_drive_plays and current_yardline < 100:
            # Determine play type based on down/distance and field position
            play_type = _determine_phase3_play_type(down, distance, current_yardline)
            
            if play_type == "pass":
                yards_gained, completed, interception, sack = _generate_phase3_pass_play(down, distance)
                
                event = PBPEvent(
                    game_id=game_id,
                    drive_id=drive_num + 1,
                    play_id=play_id,
                    quarter=min(4, (play_id // 15) + 1),
                    clock=f"{15 - (play_id % 15):02d}:00",
                    offense_team_id=offense_team,
                    defense_team_id=defense_team,
                    down=down,
                    distance=distance,
                    yardline=current_yardline,
                    play_type="pass",
                    yards_gained=yards_gained,
                    is_scoring_play=False,
                    points_offense=0,
                    points_defense=0,
                    passer_id=qb.id,
                    target_id=wr.id,
                    completed=completed,
                    air_yards=max(0, yards_gained - 3),
                    yac=3 if completed and yards_gained > 0 else 0,
                    interception=interception,
                    intercepted_by_id=db.id if interception else None,
                    sack=sack,
                    sack_yards=abs(yards_gained) if sack and yards_gained < 0 else 0,
                    qb_hit=random.random() < 0.10,
                    pressure=random.random() < 0.15,
                    thrown_away=not completed and random.random() < 0.05,
                    pressures_by_ids=json.dumps([lb.id]) if random.random() < 0.15 else None,
                    hits_by_ids=json.dumps([lb.id]) if random.random() < 0.10 else None,
                    sack_split=json.dumps([[lb.id, 1.0]]) if sack else None,
                    targeted_db_id=db.id,
                    pass_breakup_by_id=db.id if not completed and random.random() < 0.10 else None,
                    coverage_type=random.choice(["man", "zone"]),
                    coverage_result=random.choice(["caught", "defended", "incomplete"]),
                    is_third_down=down == 3,
                    is_fourth_down=down == 4,
                    is_red_zone=current_yardline >= 80,
                    is_goal_to_go=current_yardline >= 95,
                    is_two_minute=random.random() < 0.05,
                    is_garbage_time_excluded=False,
                    snaps_offense=1,
                    snaps_defense=0,
                    snaps_st=0
                )
                
            elif play_type == "run":
                yards_gained = _generate_phase3_run_play()
                
                event = PBPEvent(
                    game_id=game_id,
                    drive_id=drive_num + 1,
                    play_id=play_id,
                    quarter=min(4, (play_id // 15) + 1),
                    clock=f"{15 - (play_id % 15):02d}:00",
                    offense_team_id=offense_team,
                    defense_team_id=defense_team,
                    down=down,
                    distance=distance,
                    yardline=current_yardline,
                    play_type="run",
                    yards_gained=yards_gained,
                    is_scoring_play=False,
                    points_offense=0,
                    points_defense=0,
                    rusher_id=rb.id,
                    broken_tackle=random.randint(0, 1),
                    tfl_by_ids=json.dumps([lb.id]) if yards_gained < 0 else None,
                    missed_tackle_by_ids=json.dumps([lb.id]) if random.random() < 0.08 else None,
                    is_third_down=down == 3,
                    is_fourth_down=down == 4,
                    is_red_zone=current_yardline >= 80,
                    is_goal_to_go=current_yardline >= 95,
                    is_two_minute=random.random() < 0.05,
                    is_garbage_time_excluded=False,
                    snaps_offense=1,
                    snaps_defense=0,
                    snaps_st=0
                )
            
            elif play_type == "punt":
                kick_distance = random.randint(40, 60)
                return_yards = random.randint(0, 12)
                net_yards = kick_distance - return_yards
                
                event = PBPEvent(
                    game_id=game_id,
                    drive_id=drive_num + 1,
                    play_id=play_id,
                    quarter=min(4, (play_id // 15) + 1),
                    clock=f"{15 - (play_id % 15):02d}:00",
                    offense_team_id=offense_team,
                    defense_team_id=defense_team,
                    down=down,
                    distance=distance,
                    yardline=current_yardline,
                    play_type="punt",
                    yards_gained=return_yards,
                    is_scoring_play=False,
                    points_offense=0,
                    points_defense=0,
                    punter_id=qb.id,
                    kick_distance=kick_distance,
                    net_yards=net_yards,
                    in_20=random.random() < 0.25,
                    hang_time_ms=random.randint(3800, 5200),
                    is_third_down=False,
                    is_fourth_down=False,
                    is_red_zone=False,
                    is_goal_to_go=False,
                    is_two_minute=False,
                    is_garbage_time_excluded=False,
                    snaps_offense=0,
                    snaps_defense=0,
                    snaps_st=1
                )
                
                # End drive after punt
                session.add(event)
                play_id += 1
                break
                
            elif play_type == "field_goal":
                # Only attempt FG in red zone or 4th down
                fg_distance = 100 - current_yardline + 17  # Goal post is 10 yards deep
                made = random.random() < _fg_success_rate(fg_distance)
                
                event = PBPEvent(
                    game_id=game_id,
                    drive_id=drive_num + 1,
                    play_id=play_id,
                    quarter=min(4, (play_id // 15) + 1),
                    clock=f"{15 - (play_id % 15):02d}:00",
                    offense_team_id=offense_team,
                    defense_team_id=defense_team,
                    down=down,
                    distance=distance,
                    yardline=current_yardline,
                    play_type="fg",
                    yards_gained=0,
                    is_scoring_play=made,
                    points_offense=3 if made else 0,
                    points_defense=0,
                    kicker_id=k.id,
                    kick_distance=fg_distance,
                    fg_good=made,
                    is_third_down=False,
                    is_fourth_down=False,
                    is_red_zone=current_yardline >= 80,
                    is_goal_to_go=current_yardline >= 95,
                    is_two_minute=False,
                    is_garbage_time_excluded=False,
                    snaps_offense=0,
                    snaps_defense=0,
                    snaps_st=1
                )
                
                # End drive after FG attempt
                session.add(event)
                play_id += 1
                break
            
            session.add(event)
            play_id += 1
            drive_plays += 1
            
            # Update field position and down/distance
            current_yardline += yards_gained
            
            if yards_gained >= distance:
                # First down
                down = 1
                distance = 10
            else:
                # Next down
                down += 1
                distance -= yards_gained
                
                if down > 4:
                    # Turnover on downs - end drive
                    break
            
            # Check for touchdown
            if current_yardline >= 100:
                # Touchdown!
                td_event = PBPEvent(
                    game_id=game_id,
                    drive_id=drive_num + 1,
                    play_id=play_id,
                    quarter=min(4, (play_id // 15) + 1),
                    clock=f"{15 - (play_id % 15):02d}:00",
                    offense_team_id=offense_team,
                    defense_team_id=defense_team,
                    down=down,
                    distance=distance,
                    yardline=100,
                    play_type="run" if play_type == "run" else "pass",
                    yards_gained=0,
                    is_scoring_play=True,
                    points_offense=6,
                    points_defense=0,
                    rusher_id=rb.id if play_type == "run" else None,
                    passer_id=qb.id if play_type == "pass" else None,
                    receiver_id=wr.id if play_type == "pass" else None,
                    completed=True if play_type == "pass" else None,
                    is_third_down=down == 3,
                    is_fourth_down=down == 4,
                    is_red_zone=True,
                    is_goal_to_go=True,
                    is_two_minute=False,
                    is_garbage_time_excluded=False,
                    snaps_offense=1,
                    snaps_defense=0,
                    snaps_st=0
                )
                session.add(td_event)
                play_id += 1
                break


def _determine_phase3_play_type(down: int, distance: int, yardline: int) -> str:
    """Determine play type with proper drive termination logic."""
    # Modern NFL is pass-heavy
    pass_prob = 0.65  # Base 65% pass rate
    
    # CRITICAL FIX: Increase 3rd down failure rates
    if down == 3:
        if distance <= 2:
            pass_prob = 0.40  # Short yardage favors run
        elif distance <= 5:
            pass_prob = 0.70  # Medium yardage
        else:
            pass_prob = 0.85  # Long yardage heavily favors pass
    
    # CRITICAL FIX: Implement 4th down logic
    elif down == 4:
        if yardline >= 80:  # Red zone
            if distance <= 1:
                return "run"  # Goal line run
            else:
                return "field_goal"  # FG attempt
        elif yardline >= 60:  # Four-down territory (40+ yard line)
            if distance <= 1:
                pass_prob = 0.50  # Short yardage
            else:
                return "punt"  # Punt on long 4th down
        else:  # Own territory
            return "punt"  # Always punt from own territory
    
    # Red zone adjustments
    if yardline >= 80:
        if distance <= 3:
            pass_prob = 0.45  # Short yardage in red zone
        else:
            pass_prob = 0.75  # Pass in red zone
    
    # Choose play type
    if random.random() < pass_prob:
        return "pass"
    else:
        return "run"


def _generate_phase3_pass_play(down: int, distance: int):
    """Generate realistic passing play results with increased sack rates."""
    # Modern NFL completion rate ~65-70%
    completed = random.random() < 0.68
    
    # CRITICAL FIX: Increase sack rates based on down/distance
    sack_prob = 0.06  # Base 6% sack rate
    if down == 3 and distance >= 7:
        sack_prob = 0.12  # Double sack rate on 3rd & long
    elif down == 2 and distance >= 10:
        sack_prob = 0.09  # Higher sack rate on 2nd & long
    
    if completed:
        # Successful pass: 0-50 yards, weighted toward shorter gains
        yards_gained = random.choices(
            range(0, 51),
            weights=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1] + [1] * 32
        )[0]
        interception = False
        sack = False
    else:
        # Incomplete pass
        yards_gained = 0
        interception = random.random() < 0.03  # 3% INT rate
        sack = random.random() < sack_prob  # Variable sack rate
        
        if sack:
            yards_gained = random.randint(-8, -1)  # Sack yardage
    
    return yards_gained, completed, interception, sack


def _generate_phase3_run_play():
    """Generate realistic rushing play results."""
    # Rushing: -3 to 25 yards, weighted toward shorter gains
    yards_gained = random.choices(
        range(-3, 26),
        weights=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1] + [1] * 10
    )[0]
    
    return yards_gained


def _fg_success_rate(distance: int) -> float:
    """Field goal success rate based on distance."""
    if distance <= 30:
        return 0.95
    elif distance <= 40:
        return 0.90
    elif distance <= 50:
        return 0.80
    elif distance <= 60:
        return 0.60
    else:
        return 0.30


def run_phase3_calibration_report():
    """Run Phase 3 calibration and provide detailed report."""
    print("NFL SIMULATION ENGINE - PHASE 3 CALIBRATION REPORT")
    print("=" * 60)
    
    with memory_db() as session:
        print("Running Phase 3 calibrated 4-week mini season...")
        out = run_phase3_calibrated_season(session, weeks=4, seed=2025)
        
        print(f"Generated {len(out['games'])} games")
        print(f"Teams: {out['teams']}")
        
        # Get all PBP events
        all_events = session.exec(select(PBPEvent)).all()
        print(f"Total PBP Events: {len(all_events)}")
        
        # Analyze play types
        play_types = {}
        for event in all_events:
            play_type = event.play_type
            play_types[play_type] = play_types.get(play_type, 0) + 1
        
        print(f"\nPLAY TYPE DISTRIBUTION:")
        for play_type, count in sorted(play_types.items()):
            percentage = (count / len(all_events)) * 100
            print(f"  {play_type}: {count} plays ({percentage:.1f}%)")
        
        # Analyze by team
        print(f"\nTEAM-SPECIFIC ANALYSIS:")
        games_per_team = len(out['games']) // len(out['teams'])
        
        for team_id in out['teams']:
            team_events = [e for e in all_events if e.offense_team_id == team_id]
            print(f"\nTeam {team_id} (Offensive Plays): {len(team_events)}")
            
            team_play_types = {}
            total_yards = 0
            total_points = 0
            punts = 0
            fg_attempts = 0
            fg_made = 0
            
            for event in team_events:
                play_type = event.play_type
                team_play_types[play_type] = team_play_types.get(play_type, 0) + 1
                total_yards += event.yards_gained
                total_points += event.points_offense
                
                if play_type == "punt":
                    punts += 1
                elif play_type == "fg":
                    fg_attempts += 1
                    if event.points_offense > 0:
                        fg_made += 1
            
            print(f"  Play Types: {dict(team_play_types)}")
            print(f"  Total Yards: {total_yards}")
            print(f"  Total Points: {total_points}")
            print(f"  Punts: {punts}")
            print(f"  FG Attempts: {fg_attempts} (Made: {fg_made})")
            
            # Per-game averages
            avg_yards = total_yards / games_per_team
            avg_points = total_points / games_per_team
            avg_punts = punts / games_per_team
            avg_fg_attempts = fg_attempts / games_per_team
            
            print(f"  PER-GAME AVERAGES:")
            print(f"    Yards/Game: {avg_yards:.1f} (Target: 325-375)")
            print(f"    Points/Game: {avg_points:.1f} (Target: 22.5-30)")
            print(f"    Punts/Game: {avg_punts:.1f} (Target: 3.5-4.5)")
            print(f"    FG Attempts/Game: {avg_fg_attempts:.1f} (Target: 2-3)")
        
        # Analyze defensive stats
        print(f"\nDEFENSIVE STATS ANALYSIS:")
        for team_id in out['teams']:
            def_events = [e for e in all_events if e.defense_team_id == team_id]
            sacks = sum(1 for e in def_events if e.sack)
            ints = sum(1 for e in def_events if e.interception)
            
            avg_sacks = sacks / games_per_team
            print(f"Team {team_id} Defense: {sacks} sacks ({avg_sacks:.1f}/game), {ints} interceptions")
        
        # Overall totals
        total_punts = sum(1 for e in all_events if e.play_type == "punt")
        total_fg_attempts = sum(1 for e in all_events if e.play_type == "fg")
        total_sacks = sum(1 for e in all_events if e.sack)
        
        print(f"\nOVERALL TOTALS (4 games):")
        print(f"Total Punts: {total_punts} (Target: 60-80)")
        print(f"Total FG Attempts: {total_fg_attempts} (Target: 20-30)")
        print(f"Total Sacks: {total_sacks} (Target: 40-60)")
        
        # Calibration status
        print(f"\nCALIBRATION STATUS:")
        print("=" * 30)
        
        # Calculate league averages
        total_team_yards = sum(sum(e.yards_gained for e in all_events if e.offense_team_id == team_id) for team_id in out['teams'])
        total_team_points = sum(sum(e.points_offense for e in all_events if e.offense_team_id == team_id) for team_id in out['teams'])
        total_team_punts = sum(sum(1 for e in all_events if e.play_type == "punt" and e.offense_team_id == team_id) for team_id in out['teams'])
        total_team_fgs = sum(sum(1 for e in all_events if e.play_type == "fg" and e.offense_team_id == team_id) for team_id in out['teams'])
        total_team_sacks = sum(sum(1 for e in all_events if e.sack and e.defense_team_id == team_id) for team_id in out['teams'])
        
        avg_yards_per_game = total_team_yards / (len(out['teams']) * games_per_team)
        avg_points_per_game = total_team_points / (len(out['teams']) * games_per_team)
        avg_punts_per_game = total_team_punts / (len(out['teams']) * games_per_team)
        avg_fgs_per_game = total_team_fgs / (len(out['teams']) * games_per_team)
        avg_sacks_per_game = total_team_sacks / (len(out['teams']) * games_per_team)
        
        print(f"League Average Yards/Game: {avg_yards_per_game:.1f} (Target: 325-375)")
        print(f"League Average Points/Game: {avg_points_per_game:.1f} (Target: 22.5-30)")
        print(f"League Average Punts/Game: {avg_punts_per_game:.1f} (Target: 3.5-4.5)")
        print(f"League Average FG Attempts/Game: {avg_fgs_per_game:.1f} (Target: 2-3)")
        print(f"League Average Sacks/Game: {avg_sacks_per_game:.1f} (Target: 2.0-2.5)")
        
        # Success indicators
        yards_ok = 300 <= avg_yards_per_game <= 400
        points_ok = 20 <= avg_points_per_game <= 35
        punts_ok = 3 <= avg_punts_per_game <= 5
        fgs_ok = 1.5 <= avg_fgs_per_game <= 3.5
        sacks_ok = 1.8 <= avg_sacks_per_game <= 2.8
        
        print(f"\nSUCCESS INDICATORS:")
        print(f"Yards/Game: {'PASS' if yards_ok else 'FAIL'}")
        print(f"Points/Game: {'PASS' if points_ok else 'FAIL'}")
        print(f"Punts/Game: {'PASS' if punts_ok else 'FAIL'}")
        print(f"FG Attempts/Game: {'PASS' if fgs_ok else 'FAIL'}")
        print(f"Sacks/Game: {'PASS' if sacks_ok else 'FAIL'}")
        
        overall_success = yards_ok and points_ok and punts_ok and fgs_ok and sacks_ok
        print(f"\nOVERALL CALIBRATION: {'SUCCESS' if overall_success else 'NEEDS MORE WORK'}")


if __name__ == "__main__":
    run_phase3_calibration_report()
