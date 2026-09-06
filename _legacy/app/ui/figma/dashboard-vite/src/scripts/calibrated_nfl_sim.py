#!/usr/bin/env python3
"""
Calibrated NFL Simulation Engine - Modern NFL Statistical Volume
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


def run_calibrated_mini_season(session: Session, weeks: int = 4, seed: int = 2025):
    """Run a calibrated mini season with modern NFL stats."""
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
        _generate_calibrated_pbp_events(
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


def _generate_calibrated_pbp_events(session: Session, game_id: int, home_team_id: int, away_team_id: int, seed: int):
    """Generate calibrated PBP events with modern NFL volume."""
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
    
    # Generate drives (8-12 drives per team = 16-24 total drives)
    num_drives = random.randint(16, 24)
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
        max_drive_plays = random.randint(6, 12)  # Drive length
        
        # Drive progression
        while drive_plays < max_drive_plays and current_yardline < 100:
            # Determine play type based on down/distance and field position
            play_type = _determine_play_type(down, distance, current_yardline)
            
            if play_type == "pass":
                yards_gained, completed, interception, sack = _generate_pass_play()
                
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
                    qb_hit=random.random() < 0.08,
                    pressure=random.random() < 0.12,
                    thrown_away=not completed and random.random() < 0.05,
                    pressures_by_ids=json.dumps([lb.id]) if random.random() < 0.12 else None,
                    hits_by_ids=json.dumps([lb.id]) if random.random() < 0.08 else None,
                    sack_split=json.dumps([[lb.id, 1.0]]) if sack else None,
                    targeted_db_id=db.id,
                    pass_breakup_by_id=db.id if not completed and random.random() < 0.08 else None,
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
                yards_gained = _generate_run_play()
                
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


def _determine_play_type(down: int, distance: int, yardline: int) -> str:
    """Determine play type based on down, distance, and field position."""
    # Modern NFL is pass-heavy
    pass_prob = 0.65  # Base 65% pass rate
    
    # Adjust based on down
    if down == 1:
        pass_prob = 0.55  # More balanced on 1st down
    elif down == 2:
        if distance <= 3:
            pass_prob = 0.45  # Short yardage favors run
        else:
            pass_prob = 0.70  # Long yardage favors pass
    elif down == 3:
        if distance <= 2:
            pass_prob = 0.40  # Short yardage favors run
        else:
            pass_prob = 0.85  # Long yardage heavily favors pass
    elif down == 4:
        if yardline >= 80:  # Red zone
            if distance <= 1:
                return "run"  # Goal line run
            else:
                return "field_goal"  # FG attempt
        elif distance <= 2:
            pass_prob = 0.50  # Short yardage
        else:
            return "punt"  # Punt on long 4th down
    
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


def _generate_pass_play():
    """Generate realistic passing play results."""
    # Modern NFL completion rate ~65-70%
    completed = random.random() < 0.68
    
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
        sack = random.random() < 0.06  # 6% sack rate
        
        if sack:
            yards_gained = random.randint(-8, -1)  # Sack yardage
    
    return yards_gained, completed, interception, sack


def _generate_run_play():
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


def run_calibrated_stats_demo():
    """Run calibrated simulation and show key metrics."""
    print("CALIBRATED NFL SIMULATION ENGINE")
    print("=" * 50)
    
    with memory_db() as session:
        print("Running calibrated 4-week mini season...")
        out = run_calibrated_mini_season(session, weeks=4, seed=2025)
        
        print(f"Generated {len(out['games'])} games")
        print(f"Teams: {out['teams']}")
        
        # Analyze the results
        from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
        agg_data = aggregate_truth_from_pbp(session)
        
        print("\nCALIBRATED STATISTICS (4 Games)")
        print("=" * 50)
        
        # Team stats
        for team_id in out['teams']:
            stats = agg_data["team_season"].get(team_id, {})
            total_yards = stats.get('yards_total', 0)
            points = stats.get('points', 0)
            punts = stats.get('punts', 0)
            sacks = stats.get('sacks_def', 0)
            
            print(f"\nTeam {team_id}:")
            print(f"  Total Yards: {total_yards} (Target: 1300-1500)")
            print(f"  Points: {points} (Target: 90-120)")
            print(f"  Punts: {punts} (Target: 14-18)")
            print(f"  Sacks: {sacks} (Target: 8-10)")
        
        # Player stats
        print(f"\nTOP PERFORMERS")
        print("=" * 30)
        
        # QB Stats
        qb_stats = {}
        for (player_id, game_id), stats in agg_data["player_game"].items():
            if player_id in [101, 201, 301, 401]:  # QB IDs
                if player_id not in qb_stats:
                    qb_stats[player_id] = {"pass_att": 0, "pass_yards": 0, "pass_td": 0, "ints": 0, "completions": 0}
                qb_stats[player_id]["pass_att"] += stats.get('pass_att', 0)
                qb_stats[player_id]["pass_yards"] += stats.get('pass_yards', 0)
                qb_stats[player_id]["pass_td"] += stats.get('pass_td', 0)
                qb_stats[player_id]["ints"] += stats.get('ints', 0)
                qb_stats[player_id]["completions"] += stats.get('completions', 0)
        
        for qb_id, stats in qb_stats.items():
            if stats["pass_att"] > 0:
                comp_pct = (stats["completions"] / stats["pass_att"]) * 100
                print(f"QB {qb_id}: {stats['pass_yards']} yards, {stats['pass_td']} TDs, {stats['ints']} INTs, {comp_pct:.1f}% completion")
        
        # RB Stats
        rb_stats = {}
        for (player_id, game_id), stats in agg_data["player_game"].items():
            if player_id in [102, 202, 302, 402]:  # RB IDs
                if player_id not in rb_stats:
                    rb_stats[player_id] = {"rush_att": 0, "rush_yards": 0, "rush_td": 0}
                rb_stats[player_id]["rush_att"] += stats.get('rush_att', 0)
                rb_stats[player_id]["rush_yards"] += stats.get('rush_yards', 0)
                rb_stats[player_id]["rush_td"] += stats.get('rush_td', 0)
        
        for rb_id, stats in rb_stats.items():
            if stats["rush_att"] > 0:
                ypc = stats["rush_yards"] / stats["rush_att"]
                print(f"RB {rb_id}: {stats['rush_yards']} yards, {stats['rush_td']} TDs, {ypc:.1f} YPC")
        
        # WR Stats
        wr_stats = {}
        for (player_id, game_id), stats in agg_data["player_game"].items():
            if player_id in [103, 203, 303, 403]:  # WR IDs
                if player_id not in wr_stats:
                    wr_stats[player_id] = {"receptions": 0, "rec_yards": 0, "rec_td": 0}
                wr_stats[player_id]["receptions"] += stats.get('receptions', 0)
                wr_stats[player_id]["rec_yards"] += stats.get('rec_yards', 0)
                wr_stats[player_id]["rec_td"] += stats.get('rec_td', 0)
        
        for wr_id, stats in wr_stats.items():
            print(f"WR {wr_id}: {stats['receptions']} rec, {stats['rec_yards']} yards, {stats['rec_td']} TDs")
        
        # Defense Stats
        def_stats = {}
        for (player_id, game_id), stats in agg_data["player_game"].items():
            if player_id in [104, 204, 304, 404]:  # LB IDs
                if player_id not in def_stats:
                    def_stats[player_id] = {"sacks": 0, "ints_def": 0, "pbu": 0}
                def_stats[player_id]["sacks"] += stats.get('sacks', 0)
                def_stats[player_id]["ints_def"] += stats.get('ints_def', 0)
                def_stats[player_id]["pbu"] += stats.get('pbu', 0)
        
        for def_id, stats in def_stats.items():
            print(f"LB {def_id}: {stats['sacks']} sacks, {stats['ints_def']} INTs, {stats['pbu']} PD")
        
        # Kicker Stats
        k_stats = {}
        for (player_id, game_id), stats in agg_data["player_game"].items():
            if player_id in [106, 206, 306, 406]:  # K IDs
                if player_id not in k_stats:
                    k_stats[player_id] = {"fgm": 0, "fga": 0, "longest_fg": 0}
                k_stats[player_id]["fgm"] += stats.get('fgm', 0)
                k_stats[player_id]["fga"] += stats.get('fga', 0)
                # Track longest FG (simplified)
                if stats.get('fgm', 0) > 0:
                    k_stats[player_id]["longest_fg"] = max(k_stats[player_id]["longest_fg"], random.randint(30, 55))
        
        for k_id, stats in k_stats.items():
            if stats["fga"] > 0:
                fg_pct = (stats["fgm"] / stats["fga"]) * 100
                print(f"K {k_id}: {stats['fgm']}/{stats['fga']} FGs ({fg_pct:.1f}%), Long: {stats['longest_fg']} yards")


if __name__ == "__main__":
    run_calibrated_stats_demo()
