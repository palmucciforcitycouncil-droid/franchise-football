#!/usr/bin/env python3
"""
NFL Simulation Engine - Phase 5: Option C Implementation Test
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import math
import random
import json
from sqlmodel import Session, select
from app.testing.mini_season_runner import memory_db
from app.models.pbp_event import PBPEvent
from app.models.player_models import Player
from app.models.team_priors import TeamPriors
from app.config_sim_calibration import bands, safety
from app.engine.pbp_resolver import PBPPlayResolver
from app.engine.pbp_curves import third_down_logit, red_zone_td_prob, fourth_down_decision, weather_adjustments
from app.engine.pbp_modifiers import compose_pass_complete_logit, pressure_probability_logit, sack_prob_from_pressure
from app.engine.safety_controller import SafetyController
from app.telemetry.game_metrics import GameMetrics
from app.engine.scoring import apply_touchdown, apply_pat_or_two, apply_field_goal, apply_punt
from app.engine.special_teams import attempt_field_goal
import random
import json


def run_phase5_calibrated_season(session: Session, weeks: int = 4, seed: int = 2025):
    """Run Phase 5 calibrated mini season with Option C implementation."""
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
    
    # Create team priors (neutral for now)
    for team_id in range(1, 5):
        priors = TeamPriors(
            season=2025,
            team_id=team_id,
            off_epa_mod=0.0,
            def_stop_mod=0.0,
            third_down_mod=0.0,
            red_zone_td_mod=0.0,
            pressure_mod=0.0,
            fg_make_mod=0.0,
            punt_net_mod=0.0,
            turnover_mod=0.0
        )
        session.add(priors)
    
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
    
    # Generate PBP events for each game using Option C
    for game in games:
        _generate_phase5_pbp_events(
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


def _generate_phase5_pbp_events(session: Session, game_id: int, home_team_id: int, away_team_id: int, seed: int):
    """Generate Phase 5 PBP events using Option C implementation."""
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
    
    # Initialize Option C components
    resolver = PBPPlayResolver(
        session=session,
        season=2025,
        game_seed=seed,
        is_indoor=False,  # Outdoor game
        wind_mph=random.uniform(5, 15),  # Moderate wind
        precip=random.choice(["clear", "rain", "snow"])
    )
    
    # Generate drives (6-9 drives per team = 12-18 total drives) - Balanced for target range
    num_drives = random.randint(12, 18)
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
        max_drive_plays = random.randint(4, 7)  # Slightly longer drives for more scoring
        
        # Drive progression with Option C logic
        while drive_plays < max_drive_plays and current_yardline < 100:
            # Create context for Option C resolver
            ctx = type('Context', (), {
                'offense_team_id': offense_team,
                'defense_team_id': defense_team,
                'down': down,
                'ytg': distance,
                'to_go': distance,
                'yardline': current_yardline,
                'quarter': min(4, (play_id // 15) + 1),
                'depth_secs': random.uniform(2.0, 3.5),
                'qb_cov': random.uniform(0.3, 0.8),
                'wr_db': random.uniform(0.2, 0.7),
                'ol_dl': random.uniform(0.2, 0.8),
                'coach_agg': random.uniform(0.3, 0.9),
                'kicker_max': random.randint(45, 55),
                'is_indoor': False
            })()
            
            # Determine play type using Option C logic
            if down == 4:
                # Use modern 4th down analytics
                decision = resolver.fourth_down_call(ctx)
                if decision == "PUNT":
                    play_type = "punt"
                elif decision == "FG":
                    play_type = "field_goal"
                else:  # GO
                    play_type = "pass" if random.random() < 0.65 else "run"
            elif current_yardline >= 80 and down == 3:
                # Red zone 3rd down - check if we should attempt FG
                fg_dist = 100 - current_yardline + 17
                if fg_dist <= ctx.kicker_max and random.random() < 0.8:  # Increased FG attempt rate
                    play_type = "field_goal"
                else:
                    play_type = "pass" if random.random() < 0.75 else "run"
            else:
                # Regular down - use situational curves
                if down == 3:
                    # Use third down logit table
                    sit_logit = third_down_logit(distance)
                    pass_prob = 1 / (1 + math.exp(-sit_logit))
                else:
                    pass_prob = 0.65  # Base pass rate
                
                play_type = "pass" if random.random() < pass_prob else "run"
            
            # Generate play outcome
            if play_type == "pass":
                # Use Option C pass resolution
                ctx.outcome = None
                resolver.resolve_pass_play(ctx)
                
                if ctx.outcome == "SACK":
                    yards_gained = random.randint(-8, -1)
                    completed = False
                    interception = False
                    sack = True
                elif ctx.outcome == "COMPLETE":
                    # Balanced yardage distribution for target range
                    yards_gained = random.choices(
                        range(0, 26),  # Increased max to 25 yards
                        weights=[3, 4, 5, 6, 7, 8, 9, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1] + [1] * 9
                    )[0]
                    completed = True
                    interception = False
                    sack = False
                else:  # INCOMPLETE
                    yards_gained = 0
                    completed = False
                    interception = random.random() < 0.03
                    sack = False
                
                event = PBPEvent(
                    game_id=game_id,
                    drive_id=drive_num + 1,
                    play_id=play_id,
                    quarter=ctx.quarter,
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
                # Balanced run yardage distribution for target range
                yards_gained = random.choices(
                    range(-2, 15),  # 17 elements: -2, -1, 0, 1, ..., 12, 13, 14
                    weights=[2, 3, 4, 5, 6, 7, 8, 9, 10, 9, 8, 7, 6, 5, 4, 3, 2]  # 17 weights
                )[0]
                
                event = PBPEvent(
                    game_id=game_id,
                    drive_id=drive_num + 1,
                    play_id=play_id,
                    quarter=ctx.quarter,
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
                    quarter=ctx.quarter,
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
                
                # Apply punt scoring
                apply_punt(session, game_id, offense_team)
                
                # End drive after punt
                session.add(event)
                play_id += 1
                resolver.metrics.punts += 1
                break
                
            elif play_type == "field_goal":
                # Use new special teams system
                made, fg_distance, p_make = attempt_field_goal(
                    resolver.rng, session, game_id, current_yardline, 
                    ctx.kicker_power, ctx.kicker_base_40_49, 
                    resolver.weather, offense_team
                )
                
                event = PBPEvent(
                    game_id=game_id,
                    drive_id=drive_num + 1,
                    play_id=play_id,
                    quarter=ctx.quarter,
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
                
                # Update metrics
                resolver.metrics.fg_attempts += 1
                if made:
                    resolver.metrics.total_points += 3
                
                # End drive after FG attempt
                session.add(event)
                play_id += 1
                break
            
            session.add(event)
            play_id += 1
            drive_plays += 1
            
            # Update metrics
            resolver.metrics.total_yards += yards_gained
            resolver.metrics.total_points += event.points_offense
            
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
                    quarter=ctx.quarter,
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
                
                # Apply touchdown scoring
                apply_touchdown(session, game_id, offense_team)
                
                # Attempt PAT (simple 94% success rate)
                pat_good = resolver.rng.random() < 0.94
                apply_pat_or_two(session, game_id, offense_team, pat_good, two_point=False)
                
                resolver.metrics.total_points += 7 if pat_good else 6
                break


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


def run_phase5_calibration_report():
    """Run Phase 5 calibration and provide detailed report."""
    print("NFL SIMULATION ENGINE - PHASE 5 CALIBRATION REPORT")
    print("=" * 60)
    print("Option C Implementation: Team Priors + Situational Curves + Modern 4th Down + Weather + Guardrails")
    print("=" * 60)
    
    with memory_db() as session:
        print("Running Phase 5 calibrated 4-week mini season...")
        out = run_phase5_calibrated_season(session, weeks=4, seed=2025)
        
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
        
        # Option C Features Test
        print(f"\nOPTION C FEATURES TEST:")
        print("=" * 30)
        
        # Test third down logit table
        print(f"Third Down Conversion Rates:")
        for ytg in [1, 3, 6, 9, 12]:
            logit = third_down_logit(ytg)
            prob = 1 / (1 + 2.718**(-logit))
            print(f"  3rd & {ytg}: {prob:.1%}")
        
        # Test red zone TD probability
        print(f"Red Zone TD Probability:")
        for yardline in [80, 85, 90, 95, 99]:
            prob = red_zone_td_prob(yardline, 0.0)
            print(f"  {yardline}-yard line: {prob:.1%}")
        
        # Test weather adjustments
        print(f"Weather Adjustments:")
        weather_clear = weather_adjustments(False, 5, "clear")
        weather_rain = weather_adjustments(False, 15, "rain")
        weather_snow = weather_adjustments(False, 20, "snow")
        print(f"  Clear: {weather_clear}")
        print(f"  Rain: {weather_rain}")
        print(f"  Snow: {weather_snow}")


if __name__ == "__main__":
    run_phase5_calibration_report()
