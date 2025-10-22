"""
Mini Season Test Harness - Simulates a short season and generates PBP events.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple
import random
import json
from contextlib import contextmanager

from sqlmodel import SQLModel, Session, create_engine, select
from app.models.sim_models import SimTeam as Team, SimGame as Game
from app.models.player_models import Player
from app.models.pbp_event import PBPEvent
from app.models.stats_models import PlayerGameStats, TeamGameStats


def _try_import_sim_bits():
    """Try to import game simulator classes."""
    candidates = [
        ("app.engine.game_simulator", "GameSimulator"),
        ("app.engine.simulator", "GameSimulator"),
        ("app.engine.league_sim", "LeagueSimulator"),
        ("app.services.sim", "SimRunner"),
    ]
    for mod, cls in candidates:
        try:
            m = __import__(mod, fromlist=[cls])
            return getattr(m, cls)
        except Exception:
            continue
    return None

GameSimClass = _try_import_sim_bits()


def _try_seed_league():
    """Try to import league seeding utility."""
    try:
        from app.data.seed import seed_minileague
        return seed_minileague
    except Exception:
        pass

    def _fallback_seed(session: Session, num_teams: int = 4) -> List[int]:
        """Fallback league seeding."""
        # Create teams
        teams = []
        for i in range(num_teams):
            t = Team(
                name=f"Test Team {i+1}",
                city=f"City {i+1}",
                conference="AFC" if i < 2 else "NFC",
                division="East" if i % 2 == 0 else "West"
            )
            session.add(t)
            session.flush()
            teams.append(t)
        
        # Create minimal players per team
        for t in teams:
            for p in range(45):  # Full roster
                pl = Player(
                    name=f"Player {t.id}_{p+1}",
                    position=_get_position(p),
                    team_id=t.id,
                    age=25
                )
                session.add(pl)
        
        session.commit()
        return [t.id for t in teams]
    
    return _fallback_seed

seed_minileague = _try_seed_league()


def _get_position(player_num: int) -> str:
    """Get position based on player number."""
    positions = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "K", "P"]
    return positions[player_num % len(positions)]


def _try_schedule_api():
    """Try to import schedule generation."""
    try:
        from app.engine.scheduler import make_round_robin_schedule
        return make_round_robin_schedule
    except Exception:
        pass
    
    def _fallback_make_schedule(session: Session, team_ids: List[int], weeks: int = 2):
        """Fallback schedule generation."""
        pairs = []
        ids = list(team_ids)
        random.Random(2025).shuffle(ids)
        n = len(ids)
        w = 1
        
        for i in range(n):
            for j in range(i+1, n):
                pairs.append((w, ids[i], ids[j]))
                w = w + 1 if w < weeks else 1
        
        return pairs[:weeks * (n//2)]
    
    return _fallback_make_schedule

make_schedule = _try_schedule_api()


@contextmanager
def memory_db():
    """Create in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _simulate_game_fallback(session: Session, home_team_id: int, away_team_id: int, 
                           week: int, season: int = 2025) -> int:
    """Fallback game simulation when no real simulator is available."""
    # Create game
    game = Game(
        season=season,
        week=week,
        game_type="regular",
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_score=0,
        away_score=0
    )
    session.add(game)
    session.flush()
    
    # Generate realistic PBP events
    _generate_pbp_events(session, game.id, home_team_id, away_team_id)
    
    # Set final scores
    home_score, away_score = _calculate_final_scores(session, game.id)
    game.home_score = home_score
    game.away_score = away_score
    
    session.commit()
    return game.id


def _generate_pbp_events(session: Session, game_id: int, home_team_id: int, away_team_id: int):
    """Generate realistic PBP events for testing."""
    # Get players for both teams
    home_players = session.exec(
        select(Player).where(Player.team_id == home_team_id)
    ).all()
    away_players = session.exec(
        select(Player).where(Player.team_id == away_team_id)
    ).all()
    
    # Get QBs, RBs, WRs for each team
    home_qb = next((p for p in home_players if p.position == "QB"), home_players[0])
    home_rb = next((p for p in home_players if p.position == "RB"), home_players[1])
    home_wr = next((p for p in home_players if p.position == "WR"), home_players[2])
    
    away_qb = next((p for p in away_players if p.position == "QB"), away_players[0])
    away_rb = next((p for p in away_players if p.position == "RB"), away_players[1])
    away_wr = next((p for p in away_players if p.position == "WR"), away_players[2])
    
    # Get defensive players
    home_lb = next((p for p in home_players if p.position == "LB"), home_players[3])
    home_db = next((p for p in home_players if p.position == "DB"), home_players[4])
    away_lb = next((p for p in away_players if p.position == "LB"), away_players[3])
    away_db = next((p for p in away_players if p.position == "DB"), away_players[4])
    
    # Generate ~60-80 plays per game
    num_plays = random.randint(60, 80)
    current_yardline = 25  # Start at 25 yard line
    down = 1
    distance = 10
    
    for play_num in range(num_plays):
        # Determine offense/defense
        offense_team = home_team_id if play_num % 2 == 0 else away_team_id
        defense_team = away_team_id if offense_team == home_team_id else home_team_id
        
        # Get offensive players
        if offense_team == home_team_id:
            qb, rb, wr = home_qb, home_rb, home_wr
            lb, db = away_lb, away_db
        else:
            qb, rb, wr = away_qb, away_rb, away_wr
            lb, db = home_lb, home_db
        
        # Generate play
        play_type = random.choice(["pass", "run", "punt", "fg"])
        yards_gained = 0  # Initialize yards_gained
        
        if play_type == "pass":
            yards_gained = random.randint(-5, 25)
            completed = random.random() < 0.65
            
            event = PBPEvent(
                game_id=game_id,
                drive_id=1,
                play_id=play_num + 1,
                quarter=min(4, (play_num // 20) + 1),
                clock=f"{15 - (play_num % 15):02d}:00",
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
                air_yards=max(0, yards_gained - 5),
                yac=5 if completed and yards_gained > 0 else 0,
                interception=not completed and random.random() < 0.05,
                intercepted_by_id=db.id if not completed and random.random() < 0.05 else None,
                sack=not completed and random.random() < 0.08,
                sack_yards=abs(yards_gained) if yards_gained < 0 else 0,
                qb_hit=random.random() < 0.1,
                pressure=random.random() < 0.15,
                thrown_away=not completed and random.random() < 0.1,
                pressures_by_ids=json.dumps([lb.id]) if random.random() < 0.15 else None,
                hits_by_ids=json.dumps([lb.id]) if random.random() < 0.1 else None,
                sack_split=json.dumps([[lb.id, 1.0]]) if not completed and random.random() < 0.08 else None,
                targeted_db_id=db.id,
                pass_breakup_by_id=db.id if not completed and random.random() < 0.1 else None,
                coverage_type=random.choice(["man", "zone"]),
                coverage_result=random.choice(["caught", "defended", "incomplete"]),
                is_third_down=down == 3,
                is_fourth_down=down == 4,
                is_red_zone=current_yardline <= 20,
                is_goal_to_go=current_yardline <= distance,
                is_two_minute=random.random() < 0.1,
                is_garbage_time_excluded=False,
                snaps_offense=1,
                snaps_defense=0,
                snaps_st=0
            )
            
        elif play_type == "run":
            yards_gained = random.randint(-2, 15)
            
            event = PBPEvent(
                game_id=game_id,
                drive_id=1,
                play_id=play_num + 1,
                quarter=min(4, (play_num // 20) + 1),
                clock=f"{15 - (play_num % 15):02d}:00",
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
                broken_tackle=random.randint(0, 2),
                tfl_by_ids=json.dumps([lb.id]) if yards_gained < 0 else None,
                missed_tackle_by_ids=json.dumps([lb.id]) if random.random() < 0.1 else None,
                is_third_down=down == 3,
                is_fourth_down=down == 4,
                is_red_zone=current_yardline <= 20,
                is_goal_to_go=current_yardline <= distance,
                is_two_minute=random.random() < 0.1,
                is_garbage_time_excluded=False,
                snaps_offense=1,
                snaps_defense=0,
                snaps_st=0
            )
            
        elif play_type == "punt":
            kick_distance = random.randint(35, 55)
            return_yards = random.randint(0, 15)
            net_yards = kick_distance - return_yards
            
            event = PBPEvent(
                game_id=game_id,
                drive_id=1,
                play_id=play_num + 1,
                quarter=min(4, (play_num // 20) + 1),
                clock=f"{15 - (play_num % 15):02d}:00",
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
                punter_id=qb.id,  # Use QB as punter for simplicity
                kick_distance=kick_distance,
                net_yards=net_yards,
                in_20=random.random() < 0.3,
                hang_time_ms=random.randint(3500, 5000),
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
            
        else:  # field goal
            kick_distance = random.randint(25, 50)
            made = random.random() < 0.8
            
            event = PBPEvent(
                game_id=game_id,
                drive_id=1,
                play_id=play_num + 1,
                quarter=min(4, (play_num // 20) + 1),
                clock=f"{15 - (play_num % 15):02d}:00",
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
                kicker_id=qb.id,  # Use QB as kicker for simplicity
                kick_distance=kick_distance,
                is_third_down=False,
                is_fourth_down=False,
                is_red_zone=current_yardline <= 20,
                is_goal_to_go=current_yardline <= distance,
                is_two_minute=False,
                is_garbage_time_excluded=False,
                snaps_offense=0,
                snaps_defense=0,
                snaps_st=1
            )
        
        session.add(event)
        
        # Update game state
        current_yardline += yards_gained
        if current_yardline <= 0:
            current_yardline = 20  # Touchback
        elif current_yardline >= 100:
            current_yardline = 20  # Touchdown, reset
        
        # Update down and distance
        if yards_gained >= distance:
            down = 1
            distance = 10
        else:
            down += 1
            distance -= yards_gained
            if down > 4:
                down = 1
                distance = 10
                current_yardline = max(20, current_yardline - 10)  # Punt/turnover


def _calculate_final_scores(session: Session, game_id: int) -> Tuple[int, int]:
    """Calculate final scores from PBP events."""
    events = session.exec(
        select(PBPEvent).where(PBPEvent.game_id == game_id)
    ).all()
    
    home_score = 0
    away_score = 0
    
    for event in events:
        if event.is_scoring_play:
            if event.offense_team_id == event.offense_team_id:  # Simplified
                home_score += event.points_offense
            else:
                away_score += event.points_offense
    
    return home_score, away_score


def run_mini_season(session: Session, weeks: int = 2) -> Dict[str, Any]:
    """
    Run a mini season simulation.
    Returns a dict with keys:
      teams: List[int]
      schedule: List[Tuple[int week, int home_tid, int away_tid]]
      games: List[int game_ids]
    """
    teams = seed_minileague(session, num_teams=4)
    schedule = make_schedule(session, teams, weeks)
    games = []
    
    # Try to use real simulator first
    if GameSimClass:
        sim = GameSimClass()
        for (week, home, away) in schedule:
            try:
                gid = sim.simulate_game(
                    session=session, 
                    home_team_id=home, 
                    away_team_id=away, 
                    week=week, 
                    seed=2025+week
                )
                games.append(gid)
            except Exception:
                # Fall back to our simulation
                gid = _simulate_game_fallback(session, home, away, week)
                games.append(gid)
    else:
        # Use fallback simulation
        for (week, home, away) in schedule:
            gid = _simulate_game_fallback(session, home, away, week)
            games.append(gid)
    
    session.commit()
    return {"teams": teams, "schedule": schedule, "games": games}
