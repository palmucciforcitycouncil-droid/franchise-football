from __future__ import annotations

from typing import Annotated, List, Optional, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.database import get_session, create_db_and_tables
from app.models import Team, Player, DepthChart, GameResult, Coach  # PlayerInjury temporarily disabled
from app.models.player_stats import PlayerSeasonStats
from app.models.season import Season
from app.models.dtos import TeamDTO, PlayerDTO, DepthChartDTO, GameResultDTO
from app.engine.types import TeamStub, GameConfig
from app.engine.sim_v1 import simulate_game as sim_v1
from app.engine.sim_v2 import simulate_game as sim_v2
from app.engine.sim_v3 import simulate_game as sim_v3
from app.engine.sim_v4 import simulate_game as sim_v4
# from app.engine.sim_pbp import simulate_game as sim_pbp  # Temporarily disabled due to missing calibration file
from app.engine.power_ranking import update_ratings, predict_prob
from app.engine.playoff_system import determine_playoff_teams, create_playoff_bracket
from app.engine.score_fidelity_system import ScoreFidelitySystem
from app.engine.drive_engine import simulate_drive_with_engine
from app.engine.official_schedule_generator import generate_official_schedule, create_schedule_from_db, OfficialScheduleGenerator
from app.models.awards import AwardsSystem, AwardType, AwardCategory
# from app.engine.season_progression import get_season_progression_manager  # Temporarily disabled
# from app.services.season_runner import run_season  # Temporarily disabled
# from app.services.report_writer import write_season_report  # Temporarily disabled
from app.ui.api_diag import router as diag_router
from app.ui.api_sim import router as sim_router

# Create the FastAPI app FIRST, then use it in route decorators
app = FastAPI(title="Franchise Football API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files for JavaScript
app.mount("/js", StaticFiles(directory="app/ui/templates/js"), name="js")

# Include diagnostic router
app.include_router(diag_router, prefix="")

# Include simulation router
app.include_router(sim_router, prefix="")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    create_db_and_tables()

@app.get("/health")
def health():
    # tests expect a "version" key
    return {"status": "ok", "version": app.version}

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """Serve the main frontend interface"""
    from pathlib import Path
    import os
    
    # Get the absolute path to the template
    current_dir = Path(__file__).parent
    template_path = current_dir / "templates" / "index.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found at {template_path}")
    
    # Force reload
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)

@app.get("/simple", response_class=HTMLResponse)
def serve_simple_frontend():
    """Serve the simple frontend interface"""
    from pathlib import Path
    import os
    
    # Get the absolute path to the simple template
    current_dir = Path(__file__).parent
    template_path = current_dir / "templates" / "simple.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found at {template_path}")
    
    # Force reload
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)

@app.get("/debug", response_class=HTMLResponse)
def serve_debug_frontend():
    """Serve the debug frontend interface"""
    from pathlib import Path
    import os
    
    # Get the absolute path to the debug template
    current_dir = Path(__file__).parent
    template_path = current_dir / "templates" / "debug.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found at {template_path}")
    
    # Force reload
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)

@app.get("/test", response_class=HTMLResponse)
def serve_test_frontend():
    """Serve the test frontend interface"""
    from pathlib import Path
    import os
    
    # Get the absolute path to the test template
    current_dir = Path(__file__).parent
    template_path = current_dir / "templates" / "test.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found at {template_path}")
    
    # Force reload
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)

@app.get("/test-pbp", response_class=HTMLResponse)
def serve_test_pbp_frontend():
    """Serve the PlayByPlayBox test HTML"""
    from pathlib import Path
    
    # Get the absolute path to the test template
    current_dir = Path(__file__).parent
    template_path = current_dir / "templates" / "test_pbp.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found at {template_path}")
    
    # Force reload
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)

@app.get("/debug-main", response_class=HTMLResponse)
def serve_debug_main_frontend():
    """Serve the debug main page HTML"""
    from pathlib import Path
    
    # Get the absolute path to the debug template
    current_dir = Path(__file__).parent
    template_path = current_dir / "templates" / "debug_main.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found at {template_path}")
    
    # Force reload
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)

@app.get("/simple-v2", response_class=HTMLResponse)
def serve_simple_frontend_v2():
    """Serve the simple frontend interface v2 with deterministic simulation and boxscore"""
    from pathlib import Path
    import os
    
    # Get the absolute path to the simple template
    current_dir = Path(__file__).parent
    template_path = current_dir / "templates" / "simple_v2.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found at {template_path}")
    
    # Force reload
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)


@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    """Serve the enhanced season dashboard"""
    from pathlib import Path
    
    # Get the absolute path to the dashboard template
    current_dir = Path(__file__).parent.parent.parent
    template_path = current_dir / "dashboard.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Dashboard template not found at {template_path}")
    
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)


@app.get("/advanced", response_class=HTMLResponse)
def serve_advanced_ui():
    """Serve the advanced football management UI"""
    from pathlib import Path
    
    # Get the absolute path to the advanced UI template
    current_dir = Path(__file__).parent.parent.parent
    template_path = current_dir / "advanced_ui.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Advanced UI template not found at {template_path}")
    
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)


@app.get("/playoffs", response_class=HTMLResponse)
def serve_playoff_frontend():
    """Serve the playoff bracket frontend"""
    from pathlib import Path
    import os
    
    # Get the absolute path to the playoff template
    current_dir = Path(__file__).parent.parent.parent
    template_path = current_dir / "playoffs.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found at {template_path}")
    
    # Force reload
    return HTMLResponse(content=template_path.read_text(encoding='utf-8'), status_code=200)

SessionDep = Annotated[Session, Depends(get_session)]

# --- Teams ---
@app.get("/teams", response_model=List[TeamDTO])
def list_teams(session: SessionDep) -> List[TeamDTO]:
    try:
        rows = session.query(Team).all()
        # Convert None nicknames to empty strings to avoid validation errors
        teams_data = []
        for team in rows:
            team_dict = {
                "id": team.id,
                "location_name": team.location_name,
                "nickname": team.nickname or "",
                "conference": team.conference,
                "division": team.division,
                "power_rating": team.power_rating,
                "cap_space": team.cap_space
            }
            teams_data.append(TeamDTO.model_validate(team_dict))
        return teams_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/teams/{team_id}", response_model=TeamDTO)
def get_team(team_id: int, session: SessionDep) -> TeamDTO:
    row = session.get(Team, team_id)
    if not row:
        raise HTTPException(status_code=404, detail="team not found")
    return TeamDTO.model_validate(row)

# --- Players ---
@app.get("/players", response_model=List[PlayerDTO])
def list_players(session: SessionDep, team_id: Optional[int] = Query(default=None)) -> List[PlayerDTO]:
    query = session.query(Player)
    if team_id is not None:
        query = query.filter(Player.team_id == team_id)
    rows = query.all()
    # Convert to DTO format, ensuring jersey_number is properly mapped
    players_data = []
    for player in rows:
        player_dict = {
            "id": player.id,
            "team_id": player.team_id,
            "first_name": player.first_name,
            "last_name": player.last_name,
            "position": player.position,
            "jersey": player.jersey,  # This maps to the 'jersey' DB column
            "age": player.age,
            "salary": player.salary,
            "contract_years": player.contract_years,
            "speed": player.speed,
            "strength": player.strength,
            "agility": player.agility,
            "throw_power": player.throw_power,
            "throw_accuracy": player.throw_accuracy,
            "catching": player.catching,
            "tackling": player.tackling,
            "awareness": player.awareness,
            "potential": player.potential,
            "stamina": player.stamina,
            "injury_proneness": player.injury_proneness,
            "morale": player.morale
        }
        players_data.append(PlayerDTO.model_validate(player_dict))
    return players_data

@app.get("/players/{player_id}", response_model=PlayerDTO)
def get_player(player_id: int, session: SessionDep) -> PlayerDTO:
    row = session.get(Player, player_id)
    if not row:
        raise HTTPException(status_code=404, detail="player not found")
    return PlayerDTO.model_validate(row)

# --- Depth Chart ---
@app.get("/depth-chart/{team_id}", response_model=List[DepthChartDTO])
def get_depth_chart(team_id: int, session: SessionDep) -> List[DepthChartDTO]:
    rows = session.query(DepthChart).filter(DepthChart.team_id == team_id).all()
    return [DepthChartDTO.model_validate(r) for r in rows]

# --- Games ---
@app.get("/games", response_model=List[GameResultDTO])
def list_games(session: SessionDep, season: Optional[int] = Query(default=None)) -> List[GameResultDTO]:
    q = session.query(GameResult)
    if season is not None:
        q = q.filter(GameResult.season == season)
    rows = q.all()
    return [GameResultDTO.model_validate(r) for r in rows]

# Best-effort: create tables for local sqlite if missing
def _ensure_db():
    try:
        create_db_and_tables()
    except Exception:
        pass

_ensure_db()

class SimRequest(BaseModel):
    home_team_id: int
    away_team_id: int
    version: Literal["v0","v1"] = "v1"
    season_year: int = 2025
    week: int | None = None
    game_id: str | None = None

class SimResponse(BaseModel):
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    plays: list[str]

@app.post("/simulate", response_model=SimResponse)
def simulate(req: SimRequest, session: SessionDep) -> SimResponse:
    # from app.engine.sim_v0 import TeamStub as TeamStub0, GameConfig as GC0, simulate_game as sim0
    from app.engine.sim_v1 import TeamStub as TeamStub1, GameConfigV1 as GC1, simulate_game_v1 as sim1

    home = session.get(Team, req.home_team_id)
    away = session.get(Team, req.away_team_id)
    if not home or not away:
        raise HTTPException(status_code=404, detail="team not found")

    def team_name(t):
        loc = getattr(t, "location_name", None)
        nick = getattr(t, "nickname", None)
        if loc and nick:
            return f"{loc} {nick}"
        return getattr(t, "name", None) or (nick or "Team")

    hp = getattr(home, "power_rating", None) or 50
    ap = getattr(away, "power_rating", None) or 50

    # Default to v1 simulation
    hs = TeamStub1(id=home.id, name=team_name(home), power_rating=hp)
    as_ = TeamStub1(id=away.id, name=team_name(away), power_rating=ap)
    cfg = GC1(season_year=req.season_year, week=req.week, game_id=req.game_id or f"{away.id}@{home.id}")
    res = sim1(hs, as_, cfg)
    return SimResponse(home_team_id=req.home_team_id, away_team_id=req.away_team_id, home_score=res.home_score, away_score=res.away_score, plays=res.plays)

@app.get("/schedule")
def get_schedule():
    from app.engine.schedule_generator import generate_schedule
    
    schedule = generate_schedule(2025)
    
    # Convert to API format
    weeks = []
    for week_num, week_games in enumerate(schedule.weeks, 1):
        games = []
        for game in week_games:
            games.append({
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "week": game.week,
                "game_type": game.game_type
            })
        weeks.append({
            "week": week_num,
            "games": games
        })
    
    return {"weeks": weeks, "year": schedule.year}

# --- Free Agents ---
@app.get("/free-agents")
def get_free_agents(session: SessionDep):
    """Get all free agents (players without teams)"""
    try:
        free_agents = session.query(Player).filter(Player.team_id.is_(None)).all()
        return [{
            "id": player.id,
            "name": f"{player.first_name} {player.last_name}",
            "first_name": player.first_name,
            "last_name": player.last_name,
            "position": player.position,
            "age": player.age,
            "overall_rating": getattr(player, 'overall_rating', 50),  # Fallback if not available
            "speed": player.speed,
            "strength": player.strength,
            "agility": player.agility,
            "throw_power": player.throw_power,
            "throw_accuracy": player.throw_accuracy,
            "catching": player.catching,
            "tackling": player.tackling,
            "awareness": player.awareness,
            "potential": player.potential,
            "stamina": player.stamina,
            "injury_proneness": player.injury_proneness,
            "morale": player.morale
        } for player in free_agents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching free agents: {str(e)}")

# --- Enhanced Season Management ---
@app.get("/season/state")
def get_season_state(session: SessionDep, season_year: int = 2025):
    """Get current season progression state"""
    try:
        # manager = get_season_progression_manager(session, season_year)
        state = manager.get_current_state()
        summary = manager.get_season_summary()
        
        return {
            "season_year": season_year,
            "current_phase": state.current_phase.value,
            "current_week": state.current_week,
            "regular_season_complete": state.regular_season_complete,
            "playoffs_complete": state.playoffs_complete,
            "offseason_complete": state.offseason_complete,
            "champion": {
                "id": state.champion_id,
                "name": state.champion_name
            },
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Season state error: {str(e)}")

@app.post("/season/advance-to-regular")
# def advance_to_regular_season(session: SessionDep, season_year: int = 2025):
#     """Advance from preseason to regular season"""
#     try:
#         # manager = get_season_progression_manager(session, season_year)
#         result = manager.advance_to_regular_season()
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Advance to regular season error: {str(e)}")

def _generate_player_stats_for_game(session, home_team, away_team, home_score, away_score, season, week):
    """Generate realistic player statistics for a game"""
    try:
        # Get players for both teams
        home_players = session.query(Player).filter(Player.team_id == home_team.id).all()
        away_players = session.query(Player).filter(Player.team_id == away_team.id).all()
        
        # Generate stats for home team
        _generate_team_player_stats(session, home_players, home_team.id, home_score, season, week)
        
        # Generate stats for away team  
        _generate_team_player_stats(session, away_players, away_team.id, away_score, season, week)
        
    except Exception as e:
        print(f"Error generating player stats: {e}")
        # Don't fail the simulation if stats generation fails
        pass

def _generate_team_player_stats(session, players, team_id, team_score, season, week):
    """Generate statistics for all players on a team"""
    import random
    
    # Focus on key offensive players (QB, RB, WR)
    offensive_players = [p for p in players if p.position in ['QB', 'RB', 'WR', 'TE']]
    defensive_players = [p for p in players if p.position in ['LB', 'CB', 'S', 'DL']]
    
    # Generate QB stats (primary contributor to scoring) - Always use the same QB for consistency
    qbs = [p for p in offensive_players if p.position == 'QB']
    if qbs:
        # Sort by ID to ensure consistent QB selection
        qb = sorted(qbs, key=lambda x: x.id)[0]
        _update_or_create_player_stats(session, qb, team_id, season, {
            'games': 1,
            'pass_att': random.randint(25, 45),
            'pass_cmp': random.randint(15, 35),
            'pass_yds': random.randint(150, 350),
            'pass_td': random.randint(0, 4),
            'pass_int': random.randint(0, 2),
            'rush_att': random.randint(2, 8),
            'rush_yds': random.randint(5, 40),
            'rush_td': random.randint(0, 1)
        })
    
    # Generate RB stats - Always use the same RB for consistency
    rbs = [p for p in offensive_players if p.position == 'RB']
    if rbs:
        # Sort by ID to ensure consistent RB selection
        rb = sorted(rbs, key=lambda x: x.id)[0]
        _update_or_create_player_stats(session, rb, team_id, season, {
            'games': 1,
            'rush_att': random.randint(10, 25),
            'rush_yds': random.randint(40, 120),
            'rush_td': random.randint(0, 2),
            'rec_tgt': random.randint(2, 8),
            'rec_rec': random.randint(1, 6),
            'rec_yds': random.randint(5, 60),
            'rec_td': random.randint(0, 1)
        })
    
    # Generate WR stats - Always use the same WRs for consistency
    wrs = [p for p in offensive_players if p.position in ['WR', 'TE']]
    if wrs:
        # Sort by ID to ensure consistent WR selection
        sorted_wrs = sorted(wrs, key=lambda x: x.id)
        
        # Primary WR
        wr1 = sorted_wrs[0]
        _update_or_create_player_stats(session, wr1, team_id, season, {
            'games': 1,
            'rec_tgt': random.randint(6, 12),
            'rec_rec': random.randint(4, 8),
            'rec_yds': random.randint(50, 120),
            'rec_td': random.randint(0, 2)
        })
        
        # Secondary WR if available
        if len(sorted_wrs) > 1:
            wr2 = sorted_wrs[1]
            _update_or_create_player_stats(session, wr2, team_id, season, {
                'games': 1,
                'rec_tgt': random.randint(3, 8),
                'rec_rec': random.randint(2, 5),
                'rec_yds': random.randint(20, 80),
                'rec_td': random.randint(0, 1)
            })
    
    # Generate defensive stats (simplified) - Always use the same defenders for consistency
    if defensive_players:
        # Sort by ID to ensure consistent defender selection
        sorted_defenders = sorted(defensive_players, key=lambda x: x.id)
        for i, defender in enumerate(sorted_defenders[:5]):  # Top 5 defenders
            _update_or_create_player_stats(session, defender, team_id, season, {
                'games': 1,
                'def_tkl': random.randint(2, 8),
                'def_sack': random.randint(0, 2),
                'def_int': random.randint(0, 1)
            })
    
    # All other players get minimal stats
    for player in players:
        if player not in offensive_players and player not in defensive_players[:5]:
            _update_or_create_player_stats(session, player, team_id, season, {
                'games': 1,
                'snaps': random.randint(10, 50)
            })

def _update_or_create_player_stats(session, player, team_id, season, stats_dict):
    """Update or create player season stats"""
    try:
        # Check if stats already exist for this player/season
        existing_stats = session.query(PlayerSeasonStats).filter(
            PlayerSeasonStats.player_id == player.id,
            PlayerSeasonStats.season == season
        ).first()
        
        if existing_stats:
            # Update existing stats
            for key, value in stats_dict.items():
                current_value = getattr(existing_stats, key, 0)
                setattr(existing_stats, key, current_value + value)
        else:
            # Create new stats
            stats_dict.update({
                'player_id': player.id,
                'team_id': team_id,
                'season': season
            })
            new_stats = PlayerSeasonStats(**stats_dict)
            session.add(new_stats)
            
    except Exception as e:
        print(f"Error updating player stats for {player.id}: {e}")

@app.post("/test-simple")
def test_simple(session: SessionDep):
    """Simple test endpoint to debug config issues"""
    try:
        return {"message": "Test endpoint working", "teams_count": session.query(Team).count()}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Test error: {str(e)}")

@app.post("/season/simulate-week")
def simulate_week(session: SessionDep, season_year: int = 2025):
    """Simulate the current week (regular season or playoffs)"""
    try:
        # Simple simulation without complex imports
        import random
        
        # Get current week from season state - use the most recent season
        season = session.query(Season).order_by(Season.year.desc()).first()
        
        if not season:
            # Initialize season if it doesn't exist
            season = Season(
                year=season_year,
                current_phase="regular_season",
                current_week=1,
                is_active=True
            )
            session.add(season)
            session.commit()
        else:
            # Use the existing season, but update the year if needed
            if season.year != season_year:
                season.year = season_year
                session.commit()
        
        # If season is in offseason, reset to regular season week 1
        if season.current_phase == "offseason":
            season.current_phase = "regular_season"
            season.current_week = 1
            season.regular_season_complete = False
            season.playoffs_complete = False
            season.offseason_complete = False
            
            # Clear all game results and player stats for fresh start
            session.query(GameResult).filter(GameResult.season == season_year).delete()
            session.query(PlayerSeasonStats).filter(PlayerSeasonStats.season == season_year).delete()
            session.commit()
        
        current_week = season.current_week
        if current_week <= 0:
            current_week = 1
            season.current_week = 1
            session.commit()
            
        if current_week > 18:
            return {
                "message": "Regular season complete! Ready for playoffs.",
                "phase": "regular_season_complete",
                "week": current_week,
                "games_played": 0
            }
        
        # Simple simulation - just create some mock game results
        teams = session.query(Team).all()
        if len(teams) < 2:
            return {
                "message": "Need at least 2 teams to simulate",
                "phase": "error",
                "week": current_week,
                "games_played": 0
            }
        
        # Create realistic game results for this week
        # Use deterministic RNG instead of global seed
        from app.engine.rng import make_rng, get_league_seed
        rng = make_rng(get_league_seed(), season_year, current_week, 1000, "api")
        
        games_played = 0
        game_results = []
        
        # Simulate ALL teams each week
        # With 32 teams, we need 16 games per week (32 teams ÷ 2 = 16 games)
        num_games = len(teams) // 2  # All teams must play
        
        # Create team pairs using a deterministic approach to ensure all teams play exactly once
        team_pairs = []
        
        # Use a simple round-robin approach to ensure all teams are paired
        # This guarantees that each team plays exactly once per week
        teams_list = list(teams)  # Convert to list to ensure indexing works
        
        # Create pairs by taking teams in order
        for i in range(0, len(teams_list), 2):
            if i + 1 < len(teams_list):
                team_pairs.append((teams_list[i], teams_list[i + 1]))
        
        # Verify we have exactly the right number of pairs
        if len(team_pairs) != num_games:
            raise Exception(f"Team pairing failed: expected {num_games} pairs, got {len(team_pairs)}")
        
        # Verify no team appears in multiple games
        all_team_ids = []
        for pair in team_pairs:
            all_team_ids.extend([pair[0].id, pair[1].id])
        
        unique_team_ids = set(all_team_ids)
        if len(unique_team_ids) != len(all_team_ids):
            raise Exception(f"Duplicate teams found in games: {all_team_ids}")
        
        # Verify all teams are included
        all_teams_in_db = {team.id for team in teams}
        if unique_team_ids != all_teams_in_db:
            missing_teams = all_teams_in_db - unique_team_ids
            raise Exception(f"Missing teams from games: {missing_teams}")
        
        # Debug logging
        print(f"DEBUG: Total teams: {len(teams)}")
        print(f"DEBUG: Expected games: {num_games}")
        print(f"DEBUG: Team pairs created: {len(team_pairs)}")
        print(f"DEBUG: Teams in games: {len(unique_team_ids)}")
        print(f"DEBUG: First few team pairs: {[(pair[0].nickname, pair[1].nickname) for pair in team_pairs[:3]]}")
        
        # Validate we have the right number of games
        if len(team_pairs) != num_games:
            print(f"WARNING: Expected {num_games} games but only have {len(team_pairs)} team pairs")
        
        # Simulate games with robust error handling
        for i, (home_team, away_team) in enumerate(team_pairs):
            try:
                print(f"DEBUG: Simulating game {i+1}/{len(team_pairs)}: {home_team.nickname} vs {away_team.nickname}")
                
                # More realistic scoring based on team power ratings
                home_power = home_team.power_rating or 50
                away_power = away_team.power_rating or 50
                
                # Base score around 21 points (NFL average)
                base_score = 21
                
                # Adjust based on power rating difference
                power_diff = (home_power - away_power) / 10.0  # Scale down the difference
                
                # Home field advantage
                hfa = 2.5
                
                # Calculate expected scores
                home_expected = base_score + power_diff + hfa
                away_expected = base_score - power_diff
                
                # Add randomness
                home_score = max(0, int(home_expected + rng.gauss(0, 7)))
                away_score = max(0, int(away_expected + rng.gauss(0, 7)))
                
                # Ensure reasonable score range
                home_score = min(50, max(0, home_score))
                away_score = min(50, max(0, away_score))
                
                # Create game result
                game_result = GameResult(
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    home_score=home_score,
                    away_score=away_score,
                    season=season_year,
                    week=current_week,
                    winner_team_id=home_team.id if home_score > away_score else away_team.id if away_score > home_score else None
                )
                
                session.add(game_result)
                games_played += 1
                
                print(f"DEBUG: Added game result to session: {home_score}-{away_score}")
                
                # Generate player statistics for this game (non-critical)
                try:
                    _generate_player_stats_for_game(session, home_team, away_team, home_score, away_score, season_year, current_week)
                except Exception as e:
                    print(f"DEBUG: Player stats generation failed: {e}")
                    # Don't fail the entire simulation for player stats
                
                game_results.append({
                    "home_team": f"{home_team.location_name} {home_team.nickname}",
                    "away_team": f"{away_team.location_name} {away_team.nickname}",
                    "home_score": home_score,
                    "away_score": away_score,
                    "winner": "home" if home_score > away_score else "away" if away_score > home_score else "tie"
                })
                
            except Exception as e:
                print(f"ERROR: Failed to simulate game {i+1}: {home_team.nickname} vs {away_team.nickname} - {e}")
                # Continue with other games even if one fails
                continue
        
        # Update season week
        season.current_week = current_week + 1
        session.commit()
        
        # Verify all games were saved
        saved_games = session.query(GameResult).filter(
            GameResult.season == season_year,
            GameResult.week == current_week
        ).count()
        
        print(f"DEBUG: Expected {games_played} games, saved {saved_games} games")
        
        if saved_games != games_played:
            print(f"WARNING: Game count mismatch - expected {games_played}, saved {saved_games}")
        
        return {
            "message": f"Week {current_week} simulated successfully!",
            "phase": "regular_season",
            "week": current_week,
            "games_played": games_played,
            "games_saved": saved_games,
            "next_week": current_week + 1,
            "game_results": game_results
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Simulate week error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Week simulation error: {str(e)}")

# @app.post("/season/advance-to-playoffs")
# def advance_to_playoffs(session: SessionDep, season_year: int = 2025):
#     """Advance to playoff phase"""
#     try:
#         # manager = get_season_progression_manager(session, season_year)
#         result = manager.advance_to_playoffs()
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Advance to playoffs error: {str(e)}")

# @app.post("/season/advance-to-offseason")
# def advance_to_offseason(session: SessionDep, season_year: int = 2025):
#     """Advance to offseason phase"""
#     try:
#         # manager = get_season_progression_manager(session, season_year)
#         result = manager.advance_to_offseason()
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Advance to offseason error: {str(e)}")

# @app.post("/season/start-new-season")
# def start_new_season(session: SessionDep, new_season_year: int = 2026):
#     """Start a new season after the current one is complete"""
#     try:
#         # Get current season year to determine the progression manager
#         current_season = session.query(Season).filter(Season.year < new_season_year).order_by(Season.year.desc()).first()
#         if not current_season:
#             raise HTTPException(status_code=400, detail=f"No previous season found to transition from")
#         
#         current_year = current_season.year
#         manager = get_season_progression_manager(session, current_year)
#         result = manager.start_new_season(new_season_year)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error starting new season: {str(e)}")

@app.post("/api/v1/sim/season")
def simulate_season_api(season: int = 2025, seed: int = 2025):
    """Simulate a complete season and return results with report file path"""
    try:
        # Temporarily disabled - season runner needs fixing
        raise HTTPException(status_code=503, detail="Season simulation temporarily disabled - fixing imports")
        
        # # Run season simulation
        # summary = run_season(season, seed)
        # 
        # if "error" in summary:
        #     raise HTTPException(status_code=400, detail=summary["error"])
        # 
        # # Write report to disk
        # report_path = write_season_report(summary)
        # 
        # # Log brief summary
        # print(f"Season {season} simulated: {summary['games_played']} games, "
        #       f"{summary['avg_points_per_game']:.1f} PPG avg, "
        #       f"{summary['home_win_rate']:.1%} home win rate")
        # 
        # # Return JSON response
        # return {
        #     "ok": True,
        #     "season": season,
        #     "summary": summary,
        #     "report_path": report_path
        # }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Season simulation error: {str(e)}")

@app.post("/api/v1/sim/week")
def simulate_week_api(session: SessionDep, season: int = 2025, week: int = 1, seed: int = 2025):
    """Simulate a single week using the new deterministic engine with official NFL scheduling"""
    try:
        from app.engine.game_core import simulate_game, TeamStub
        from app.engine.power_ranking import update_ratings, convert_power_rating_to_elo, convert_elo_to_power_rating
        from app.engine.nfl_scheduler_simple import NFLSchedulerSimple, create_teams_from_database
        
        # Get teams from database
        teams = session.query(Team).all()
        if len(teams) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 teams to simulate games")
        
        # Convert database teams to scheduler format
        teams_data = []
        for team in teams:
            teams_data.append({
                "id": team.id,
                "location_name": team.location_name,
                "nickname": team.nickname,
                "conference": team.conference.value if hasattr(team.conference, 'value') else str(team.conference),
                "division": team.division.value if hasattr(team.division, 'value') else str(team.division),
                "power_rating": team.power_rating
            })
        
        scheduler_teams = create_teams_from_database(teams_data)
        
        # Generate official NFL schedule for the season
        full_schedule = NFLSchedulerSimple(scheduler_teams, season, seed).generate_season_schedule()
        
        # Get games for this specific week
        week_games = [game for game in full_schedule if game.week == week]
        
        # Handle bye weeks (week 6 has no games in NFL schedule)
        if not week_games:
            return {
                "ok": True,
                "season": season,
                "week": week,
                "games_played": 0,
                "game_results": [],
                "message": f"Week {week} is a bye week - no games scheduled"
            }
        
        games_this_week = []
        game_results = []
        
        # Create team lookup by ID
        teams_by_id = {team.id: team for team in teams}
        
        # Simulate each game in the week
        for game in week_games:
            home_team = teams_by_id[game.home_team_id]
            away_team = teams_by_id[game.away_team_id]
            
            # Create team stubs
            home_stub = TeamStub(
                id=home_team.id,
                power_rating=home_team.power_rating,
                name=f"{home_team.location_name} {home_team.nickname}"
            )
            away_stub = TeamStub(
                id=away_team.id,
                power_rating=away_team.power_rating,
                name=f"{away_team.location_name} {away_team.nickname}"
            )
            
            # Simulate game
            game_result = simulate_game(home_stub, away_stub, season, week, seed)
            
            # Update power rankings
            home_elo = convert_power_rating_to_elo(home_team.power_rating)
            away_elo = convert_power_rating_to_elo(away_team.power_rating)
            
            new_home_elo, new_away_elo = update_ratings(
                home_elo, away_elo, 
                game_result.home_score, game_result.away_score
            )
            
            # Update team power ratings
            home_team.power_rating = convert_elo_to_power_rating(new_home_elo)
            away_team.power_rating = convert_elo_to_power_rating(new_away_elo)
            
            # Store game result
            game_results.append({
                "home_team": {
                    "id": home_team.id,
                    "name": f"{home_team.location_name} {home_team.nickname}",
                    "score": game_result.home_score,
                    "power_rating": home_team.power_rating
                },
                "away_team": {
                    "id": away_team.id,
                    "name": f"{away_team.location_name} {away_team.nickname}",
                    "score": game_result.away_score,
                    "power_rating": away_team.power_rating
                },
                "week": week,
                "season": season,
                "game_type": game.game_type,
                "summary": f"Week {week}: {home_stub.name} {game_result.home_score}, {away_stub.name} {game_result.away_score} ({game.game_type})"
            })
            
            games_this_week.append(game_result)
        
        # Commit changes
        session.commit()
        
        # Return results
        return {
            "ok": True,
            "season": season,
            "week": week,
            "games_played": len(games_this_week),
            "game_results": game_results,
            "message": f"Week {week} simulated successfully"
        }
        
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Week simulation error: {str(e)}")

@app.get("/api/v1/standings")
def get_standings(session: SessionDep, season: int = 2025):
    """Get current standings for all teams"""
    try:
        teams = session.query(Team).all()
        
        # For now, we'll use power ratings as a proxy for standings
        # In a full implementation, we'd track actual wins/losses from game results
        standings = []
        for team in teams:
            standings.append({
                "id": team.id,
                "name": f"{team.location_name} {team.nickname}",
                "conference": team.conference.value if hasattr(team.conference, 'value') else str(team.conference),
                "division": team.division.value if hasattr(team.division, 'value') else str(team.division),
                "wins": team.wins if hasattr(team, 'wins') else 0,
                "losses": team.losses if hasattr(team, 'losses') else 0,
                "power_rating": team.power_rating
            })
        
        # Sort by power rating (proxy for success)
        standings.sort(key=lambda x: x["power_rating"], reverse=True)
        
        return {
            "ok": True,
            "season": season,
            "standings": standings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting standings: {str(e)}")


@app.post("/api/v1/playoffs/generate")
def generate_playoff_bracket_api(session: SessionDep, season: int = 2025, seed: int = 2025):
    """Generate NFL-style playoff bracket (14 teams, 7 per conference)"""
    try:
        from app.engine.playoff_scheduler import NFLPlayoffScheduler, TeamRecord
        
        # Get teams from database and calculate standings
        teams = session.query(Team).all()
        
        # Group teams by conference and division
        teams_by_conf_div = {"AFC": {"East": [], "North": [], "South": [], "West": []},
                           "NFC": {"East": [], "North": [], "South": [], "West": []}}
        
        for team in teams:
            conf = team.conference.value if hasattr(team.conference, 'value') else str(team.conference)
            div = team.division.value if hasattr(team.division, 'value') else str(team.division)
            
            # Calculate wins/losses from game results
            home_games = session.query(GameResult).filter(
                GameResult.home_team_id == team.id,
                GameResult.season == season
            ).all()
            
            away_games = session.query(GameResult).filter(
                GameResult.away_team_id == team.id,
                GameResult.season == season
            ).all()
            
            wins = 0
            losses = 0
            ties = 0
            
            # Count wins/losses/ties from home games
            for game in home_games:
                if game.home_score > game.away_score:
                    wins += 1
                elif game.home_score < game.away_score:
                    losses += 1
                else:
                    ties += 1
            
            # Count wins/losses/ties from away games
            for game in away_games:
                if game.away_score > game.home_score:
                    wins += 1
                elif game.away_score < game.home_score:
                    losses += 1
                else:
                    ties += 1
            
            team_data = {
                "id": team.id,
                "name": f"{team.location_name} {team.nickname}",
                "conference": conf,
                "division": div,
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "power_rating": team.power_rating
            }
            
            if conf in teams_by_conf_div and div in teams_by_conf_div[conf]:
                teams_by_conf_div[conf][div].append(team_data)
        
        # Sort each division by wins (or power rating as proxy)
        for conf in teams_by_conf_div:
            for div in teams_by_conf_div[conf]:
                teams_by_conf_div[conf][div].sort(key=lambda t: (-t.get("wins", 0), -t.get("power_rating", 0)))
        
        # Convert to playoff scheduler format
        playoff_standings = {"AFC": [], "NFC": []}
        
        # Create TeamRecord objects
        for conference_name, divisions in teams_by_conf_div.items():
            for division_name, teams in divisions.items():
                for i, team in enumerate(teams):
                    # Determine if team is division winner (1st place in division)
                    is_division_winner = i == 0
                    
                    team_record = TeamRecord(
                        team_id=team["id"],
                        team_name=team["name"],
                        conference=team["conference"],
                        division=team["division"],
                        wins=team.get("wins", 0),
                        losses=team.get("losses", 0),
                        ties=team.get("ties", 0),
                        is_division_winner=is_division_winner
                    )
                    
                    playoff_standings[conference_name].append(team_record)
        
        # Generate playoff bracket
        scheduler = NFLPlayoffScheduler(f"FF_PLAYOFFS_{season}_{seed}")
        bracket = scheduler.generate_playoff_bracket(playoff_standings, season)
        
        return bracket
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating playoff bracket: {str(e)}")

@app.post("/season/complete")
def complete_season(session: SessionDep, season_year: int = 2025):
    """Complete the season"""
    try:
        # manager = get_season_progression_manager(session, season_year)
        result = manager.complete_season()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Complete season error: {str(e)}")

@app.post("/season/reset")
def reset_season(session: SessionDep, season_year: int = 2025):
    """Reset the season by clearing all game results"""
    try:
        # Clear all game results for the season
        session.query(GameResult).filter(GameResult.season == season_year).delete()
        
        # Clear season record
        session.query(Season).filter(Season.year == season_year).delete()
        
        session.commit()
        
        return {
            "message": f"Season {season_year} reset successfully! All games cleared.",
            "season_year": season_year,
            "games_cleared": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")

@app.get("/season/summary")
def get_season_summary(session: SessionDep, season_year: int = 2025):
    """Get comprehensive season summary"""
    try:
        # manager = get_season_progression_manager(session, season_year)
        summary = manager.get_season_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Season summary error: {str(e)}")

@app.get("/season/player-stats")
def get_player_stats(session: SessionDep, team_id: int = 3, season: int = 2025, limit: int = 10):
    """Get player statistics for a specific team and season"""
    try:
        # Get player stats for the team
        stats = session.query(PlayerSeasonStats).join(Player).filter(
            PlayerSeasonStats.team_id == team_id,
            PlayerSeasonStats.season == season
        ).order_by(
            (PlayerSeasonStats.pass_yds + PlayerSeasonStats.rush_yds + PlayerSeasonStats.rec_yds).desc()
        ).limit(limit).all()
        
        results = []
        for stat in stats:
            player = session.query(Player).filter(Player.id == stat.player_id).first()
            if player:
                results.append({
                    "player_id": stat.player_id,
                    "player_name": f"{player.first_name} {player.last_name}",
                    "position": player.position,
                    "games": stat.games,
                    "pass_yds": stat.pass_yds,
                    "rush_yds": stat.rush_yds,
                    "rec_yds": stat.rec_yds,
                    "total_yds": stat.pass_yds + stat.rush_yds + stat.rec_yds,
                    "pass_td": stat.pass_td,
                    "rush_td": stat.rush_td,
                    "rec_td": stat.rec_td,
                    "total_td": stat.pass_td + stat.rush_td + stat.rec_td,
                    "def_tkl": stat.def_tkl,
                    "def_sack": stat.def_sack,
                    "def_int": stat.def_int
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Player stats error: {str(e)}")

@app.get("/season/schedule")
def get_season_schedule(session: SessionDep, team_id: int = 3, season: int = 2025):
    """Get full season schedule for a team with results"""
    try:
        # Get unique games for the team (home or away) - use DISTINCT to avoid duplicates
        from sqlalchemy import distinct
        
        # First get all unique week/team combinations for this team
        team_games = session.query(GameResult.week, GameResult.home_team_id, GameResult.away_team_id).filter(
            (GameResult.home_team_id == team_id) | (GameResult.away_team_id == team_id),
            GameResult.season == season
        ).distinct().all()
        
        # Now get the actual game results for each unique combination
        games = []
        for week, home_id, away_id in team_games:
            game = session.query(GameResult).filter(
                GameResult.week == week,
                GameResult.home_team_id == home_id,
                GameResult.away_team_id == away_id,
                GameResult.season == season
            ).first()
            if game:
                games.append(game)
        
        # Sort by week
        games.sort(key=lambda x: x.week)
        
        result = []
        for game in games:
            # Get team names
            home_team = session.query(Team).filter(Team.id == game.home_team_id).first()
            away_team = session.query(Team).filter(Team.id == game.away_team_id).first()
            
            if home_team and away_team:
                # Determine if this team is home or away
                is_home = game.home_team_id == team_id
                opponent_id = game.away_team_id if is_home else game.home_team_id
                opponent_team = away_team if is_home else home_team
                
                # Determine result
                if game.winner_team_id == team_id:
                    result_str = "W"
                elif game.winner_team_id == opponent_id:
                    result_str = "L"
                else:
                    result_str = "T"
                
                result.append({
                    'week': game.week,
                    'opponent': f"{opponent_team.location_name} {opponent_team.nickname}",
                    'is_home': is_home,
                    'home_score': game.home_score,
                    'away_score': game.away_score,
                    'result': result_str,
                    'played': game.home_score is not None and game.away_score is not None
                })
        
        return result
        
    except Exception as e:
        print(f"Error getting season schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting season schedule: {str(e)}")

@app.get("/season/recent-games")
def get_recent_games(session: SessionDep, limit: int = 10, user_team_id: int = 3):
    """Get recent game results from the current season, prioritizing user's team"""
    try:
        # Get current season
        current_season = session.query(Season).first()
        if not current_season:
            raise HTTPException(status_code=404, detail="No season found")
        
        season_year = current_season.year
        
        # First, try to get recent games involving the user's team
        user_team_games = session.query(GameResult).filter(
            GameResult.season == season_year,
            (GameResult.home_team_id == user_team_id) | (GameResult.away_team_id == user_team_id)
        ).order_by(GameResult.id.desc()).limit(limit).all()
        
        # If we don't have enough user team games, fill with other recent games
        if len(user_team_games) < limit:
            remaining_limit = limit - len(user_team_games)
            user_team_ids = [g.id for g in user_team_games]
            
            other_games = session.query(GameResult).filter(
                GameResult.season == season_year,
                ~GameResult.id.in_(user_team_ids) if user_team_ids else True
            ).order_by(GameResult.id.desc()).limit(remaining_limit).all()
            
            recent_games = user_team_games + other_games
        else:
            recent_games = user_team_games
        
        results = []
        for game in recent_games:
            # Get team names
            home_team = session.query(Team).filter(Team.id == game.home_team_id).first()
            away_team = session.query(Team).filter(Team.id == game.away_team_id).first()
            
            # Mark if this is the user's team
            is_user_team = game.home_team_id == user_team_id or game.away_team_id == user_team_id
            
            results.append({
                "week": game.week,
                "home_team": f"{home_team.location_name} {home_team.nickname}" if home_team else f"Team {game.home_team_id}",
                "away_team": f"{away_team.location_name} {away_team.nickname}" if away_team else f"Team {game.away_team_id}",
                "home_score": game.home_score,
                "away_score": game.away_score,
                "winner": "home" if game.home_score > game.away_score else "away" if game.away_score > game.home_score else "tie",
                "is_user_team": is_user_team
            })
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recent games error: {str(e)}")

@app.get("/season/standings")
def get_standings(session: SessionDep):
    """Get current standings - simplified version"""
    try:
        # Get current season - use the most recent season
        current_season = session.query(Season).order_by(Season.year.desc()).first()
        if not current_season:
            raise HTTPException(status_code=404, detail="No season found")
        
        season_year = current_season.year
        
        # Get all teams
        teams = session.query(Team).all()
        
        # Get game results for current season only
        game_results = session.query(GameResult).filter(GameResult.season == season_year).all()
        
        # Initialize standings
        standings = []
        for team in teams:
            wins = 0
            losses = 0
            ties = 0
            points_for = 0
            points_against = 0
            
            # Calculate stats from game results
            for game in game_results:
                if game.home_team_id == team.id:
                    points_for += game.home_score
                    points_against += game.away_score
                    if game.winner_team_id == team.id:
                        wins += 1
                    elif game.winner_team_id == game.away_team_id:
                        losses += 1
                    else:
                        ties += 1
                elif game.away_team_id == team.id:
                    points_for += game.away_score
                    points_against += game.home_score
                    if game.winner_team_id == team.id:
                        wins += 1
                    elif game.winner_team_id == game.home_team_id:
                        losses += 1
                    else:
                        ties += 1
            
            standings.append({
                "team_id": team.id,
                "team_name": f"{team.location_name} {team.nickname or ''}".strip(),
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "points_for": points_for,
                "points_against": points_against,
                "division": team.division,
                "conference": team.conference,
                "power_rating": team.power_rating or 50
            })
        
        # Sort by wins, then point differential
        standings.sort(key=lambda x: (x["wins"], x["points_for"] - x["points_against"]), reverse=True)
        
        return standings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Standings error: {str(e)}")

# --- Power Rankings ---
@app.get("/power-rankings")
def get_power_rankings(session: SessionDep, season: int = 2025):
    """Get power rankings using ELO+MOV system as specified in GDD"""
    try:
        # Calculate power rankings using the proper ELO+MOV system
        # rankings = calculate_power_rankings(session, season)  # Temporarily disabled for stabilization
        rankings = []  # Empty for now
        
        # Convert to API format
        return [
            {
                "team_id": ranking.team_id,
                "team_name": ranking.team_name,
                "elo_rating": round(ranking.elo_rating, 1),
                "wins": ranking.wins,
                "losses": ranking.losses,
                "ties": ranking.ties,
                "points_for": ranking.points_for,
                "points_against": ranking.points_against,
                "margin_of_victory": ranking.margin_of_victory,
                "games_played": ranking.games_played,
                "conference": ranking.conference,
                "division": ranking.division
            }
            for ranking in rankings
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Power rankings error: {str(e)}")

@app.post("/power-rankings/update")
def update_power_rankings(session: SessionDep, season: int = 2025):
    """Update team ELO ratings in the database"""
    try:
        rankings = update_team_elo_ratings(session, season)
        
        return {
            "message": f"Power rankings updated for season {season}",
            "season": season,
            "teams_updated": len(rankings),
            "top_5": [
                {
                    "team_name": r.team_name,
                    "elo_rating": round(r.elo_rating, 1),
                    "record": f"{r.wins}-{r.losses}-{r.ties}"
                }
                for r in rankings[:5]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Power rankings update error: {str(e)}")

# --- Contract Negotiation ---
@app.post("/contracts/negotiate")
def start_negotiation(player_id: int, team_id: int, session: SessionDep):
    """Start a new contract negotiation"""
    from app.engine.contract_negotiation import ContractNegotiationSystem
    
    try:
        system = ContractNegotiationSystem(session)
        negotiation = system.start_negotiation(player_id, team_id)
        
        # Get player and team info for response
        player = session.get(Player, player_id)
        team = session.get(Team, team_id)
        
        if not player or not team:
            raise HTTPException(status_code=404, detail="Player or team not found")
        
        # Get market value and traits
        market_value = system.calculate_market_value(player)
        traits = system.get_player_traits(player)
        team_quality = system.calculate_team_quality(team, player)
        
        return {
            "player_id": player_id,
            "team_id": team_id,
            "player_name": f"{player.first_name} {player.last_name}",
            "position": player.position,
            "age": player.age,
            "market_value": market_value,
            "team_quality": team_quality,
            "traits": {
                "greedy": traits.greedy,
                "ring_chaser": traits.ring_chaser,
                "risk_averse": traits.risk_averse,
                "loyalist": traits.loyalist
            },
            "negotiation": {
                "status": negotiation.status.value,
                "minimum_acceptance_score": negotiation.minimum_acceptance_score,
                "mood": negotiation.mood,
                "rounds": negotiation.rounds
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Negotiation start error: {str(e)}")

@app.post("/contracts/offer")
def make_contract_offer(player_id: int, team_id: int, aav: int, years: int, session: SessionDep):
    """Make a contract offer"""
    from app.engine.contract_negotiation import ContractNegotiationSystem
    
    try:
        system = ContractNegotiationSystem(session)
        response = system.make_offer(player_id, team_id, aav, years)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contract offer error: {str(e)}")

@app.get("/contracts/negotiation/{player_id}")
def get_negotiation_status(player_id: int, session: SessionDep):
    """Get current negotiation status and summary"""
    from app.engine.contract_negotiation import ContractNegotiationSystem
    
    try:
        system = ContractNegotiationSystem(session)
        summary = system.get_negotiation_summary(player_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="No active negotiation found for this player")
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Negotiation status error: {str(e)}")

@app.post("/contracts/complete/{player_id}")
def complete_negotiation(player_id: int, session: SessionDep):
    """Complete a successful negotiation"""
    from app.engine.contract_negotiation import ContractNegotiationSystem
    
    try:
        system = ContractNegotiationSystem(session)
        success = system.complete_negotiation(player_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Cannot complete negotiation - not accepted or not found")
        
        return {
            "message": "Negotiation completed successfully",
            "player_id": player_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Negotiation completion error: {str(e)}")

@app.get("/contracts/market-value/{player_id}")
def get_player_market_value(player_id: int, session: SessionDep):
    """Get player's current market value and contract recommendations"""
    from app.engine.contract_negotiation import ContractNegotiationSystem
    
    try:
        player = session.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        system = ContractNegotiationSystem(session)
        market_value = system.calculate_market_value(player)
        optimal_years = system.get_optimal_contract_years(player)
        traits = system.get_player_traits(player)
        
        return {
            "player_id": player_id,
            "player_name": f"{player.first_name} {player.last_name}",
            "position": player.position,
            "age": player.age,
            "market_value": market_value,
            "optimal_contract_years": optimal_years,
            "traits": {
                "greedy": traits.greedy,
                "ring_chaser": traits.ring_chaser,
                "risk_averse": traits.risk_averse,
                "loyalist": traits.loyalist
            },
            "recommendations": {
                "suggested_aav_range": {
                    "min": int(market_value * 0.8),
                    "max": int(market_value * 1.2)
                },
                "suggested_years": optimal_years
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market value error: {str(e)}")

@app.post("/contracts/simulate-cpu-offers/{player_id}")
def simulate_cpu_offers(player_id: int, session: SessionDep, num_offers: int = 3):
    """Simulate CPU team offers for a player"""
    from app.engine.contract_negotiation import ContractNegotiationSystem
    
    try:
        system = ContractNegotiationSystem(session)
        offers = system.simulate_cpu_offers(player_id, num_offers)
        
        return {
            "player_id": player_id,
            "cpu_offers": [
                {
                    "team_id": offer.team_id,
                    "aav": offer.aav,
                    "years": offer.years,
                    "offer_score": offer.offer_score
                }
                for offer in offers
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CPU offers simulation error: {str(e)}")

# --- Coaching Staff ---
# --- Team Schedule ---
@app.get("/team-schedule/{team_id}")
def get_team_schedule(team_id: int, session: SessionDep):
    """Get team schedule with 2 past games and 2 upcoming games"""
    # Get the team
    team = session.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get past games (last 2)
    past_games = session.query(GameResult).filter(
        (GameResult.home_team_id == team_id) | (GameResult.away_team_id == team_id)
    ).order_by(GameResult.week.desc()).limit(2).all()
    
    # Get upcoming games (next 2) - for now, generate mock games
    upcoming_games = []
    if len(past_games) > 0:
        last_week = past_games[0].week
        for i in range(2):
            week = last_week + i + 1
            # Generate mock upcoming game
            mock_game = {
                "id": f"mock_{team_id}_{week}",
                "week": week,
                "home_team": "TBD",
                "away_team": "TBD",
                "home_score": None,
                "away_score": None,
                "status": "Scheduled"
            }
            upcoming_games.append(mock_game)
    
    # Format past games
    formatted_past = []
    for game in past_games:
        home_team = session.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = session.query(Team).filter(Team.id == game.away_team_id).first()
        
        formatted_past.append({
            "id": game.id,
            "week": game.week,
            "home_team": home_team.nickname if home_team else "Unknown",
            "away_team": away_team.nickname if away_team else "Unknown",
            "home_score": game.home_score,
            "away_score": game.away_score,
            "status": "Final"
        })
    
    return {
        "team": team.nickname,
        "past_games": formatted_past,
        "upcoming_games": upcoming_games
    }

# --- Top Performers ---
@app.get("/top-performers")
def get_top_performers(
    session: SessionDep,
    conference: str = Query(..., description="AFC or NFC"),
    side: str = Query(..., description="OFF or DEF"),
    limit: int = Query(10, description="Number of players to return")
):
    """Get top performing players by conference and side"""
    # Get players from the specified conference
    query = session.query(Player, Team).join(Team).filter(Team.conference == conference)
    
    if side == "OFF":
        # Offensive positions
        offensive_positions = ["QB", "HB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT"]
        query = query.filter(Player.position.in_(offensive_positions))
    else:
        # Defensive positions
        defensive_positions = ["LE", "RE", "DT", "LOLB", "MLB", "ROLB", "CB", "FS", "SS"]
        query = query.filter(Player.position.in_(defensive_positions))
    
    # Get players and calculate overall rating
    players_with_teams = query.limit(limit * 2).all()  # Get more to filter by rating
    
    # Calculate overall rating and create player data
    players_data = []
    for player, team in players_with_teams:
        # Calculate overall rating based on player attributes
        overall_rating = (
            player.speed + player.strength + player.agility + 
            player.awareness + player.potential
        ) // 5
        
        # Generate mock stats based on position and rating
        if side == "OFF":
            if player.position == "QB":
                stats = f"Pass Yards: {2000 + overall_rating * 20}, QB Rating: {70 + overall_rating // 2}"
            elif player.position in ["HB", "FB"]:
                stats = f"Rush Yards: {800 + overall_rating * 15}, TDs: {5 + overall_rating // 20}"
            elif player.position in ["WR", "TE"]:
                stats = f"Receptions: {40 + overall_rating // 3}, TDs: {3 + overall_rating // 25}"
            else:
                stats = f"Overall: {overall_rating}"
        else:
            stats = f"Tackles: {50 + overall_rating // 2}, Sacks: {2 + overall_rating // 30}, INTs: {1 + overall_rating // 40}"
        
        players_data.append({
            "name": f"{player.first_name} {player.last_name}",
            "position": player.position,
            "team": team.nickname,
            "stats": stats,
            "rating": overall_rating
        })
    
    # Sort by rating and take the top players
    players_data.sort(key=lambda x: x["rating"], reverse=True)
    top_players = players_data[:limit]
    
    return {
        "conference": conference,
        "side": side,
        "players": top_players
    }

# --- Box Score ---
@app.get("/box-score/{team_id}")
def get_team_box_score(team_id: int, session: SessionDep):
    """Get the last game box score for a team"""
    # Get the team
    team = session.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get the last game for this team
    last_game = session.query(GameResult).filter(
        (GameResult.home_team_id == team_id) | (GameResult.away_team_id == team_id)
    ).order_by(GameResult.week.desc()).first()
    
    if not last_game:
        # Return mock data if no games found
        return {
            "team": team.nickname,
            "opponent": "TBD",
            "week": 1,
            "date": "TBD",
            "home_score": 0,
            "away_score": 0,
            "quarters": [0, 0, 0, 0],
            "opponent_quarters": [0, 0, 0, 0],
            "status": "No games played",
            "leaders": {
                "passing": {"name": "N/A", "stats": "0-0, 0 Yds, 0 TD, 0 INT"},
                "rushing": {"name": "N/A", "stats": "0 Car, 0 Yds, 0 TD"},
                "receiving": {"name": "N/A", "stats": "0 Rec, 0 Yds, 0 TD"},
                "defense": {"name": "N/A", "stats": "0 Tack, 0 Sack, 0 INT"}
            }
        }
    
    # Get opponent team
    opponent_id = last_game.away_team_id if last_game.home_team_id == team_id else last_game.home_team_id
    opponent = session.query(Team).filter(Team.id == opponent_id).first()
    
    # Determine if team was home or away
    is_home = last_game.home_team_id == team_id
    team_score = last_game.home_score if is_home else last_game.away_score
    opponent_score = last_game.away_score if is_home else last_game.home_score
    
    # Generate mock quarter scores
    quarters = [team_score // 4 + (1 if i < team_score % 4 else 0) for i in range(4)]
    opponent_quarters = [opponent_score // 4 + (1 if i < opponent_score % 4 else 0) for i in range(4)]
    
    # Generate mock player leaders
    leaders = {
        "passing": {
            "name": f"{team.nickname} QB",
            "stats": f"{15 + (team_score // 10)}-{20 + (team_score // 8)}, {150 + team_score * 5} Yds, {team_score // 7} TD, {max(0, 2 - team_score // 10)} INT"
        },
        "rushing": {
            "name": f"{team.nickname} RB",
            "stats": f"{12 + team_score // 5} Car, {80 + team_score * 3} Yds, {team_score // 10} TD"
        },
        "receiving": {
            "name": f"{team.nickname} WR",
            "stats": f"{5 + team_score // 8} Rec, {60 + team_score * 2} Yds, {team_score // 12} TD"
        },
        "defense": {
            "name": f"{team.nickname} LB",
            "stats": f"{8 + team_score // 6} Tack, {1 + team_score // 15} Sack, {max(0, 1 - team_score // 20)} INT"
        }
    }
    
    return {
        "team": team.nickname,
        "opponent": opponent.nickname if opponent else "Unknown",
        "week": last_game.week,
        "date": f"Week {last_game.week}",
        "home_score": team_score,
        "away_score": opponent_score,
        "quarters": quarters,
        "opponent_quarters": opponent_quarters,
        "status": "Final",
        "leaders": leaders
    }

@app.get("/coaches")
def list_coaches(session: SessionDep, team_id: Optional[int] = Query(default=None)):
    try:
        query = session.query(Coach)
        if team_id:
            query = query.filter(Coach.team_id == team_id)
        else:
            # Show active coaches (with team assignments)
            query = query.filter(Coach.team_id.isnot(None))
        
        coaches = query.all()
    except Exception as e:
        # If there's an error, return empty list
        coaches = []
    
    return [
        {
            "id": coach.id,
            "first_name": coach.first_name,
            "last_name": coach.last_name,
            "full_name": coach.full_name,
            "position": coach.position,
            "team_id": coach.team_id,
            "offensive_rating": coach.offensive_rating,
            "defensive_rating": coach.defensive_rating,
            "special_teams_rating": coach.special_teams_rating,
            "leadership": coach.leadership,
            "experience": coach.experience,
            "overall_rating": coach.overall_rating,
            "salary": coach.salary,
            "contract_years": coach.contract_years,
            "age": coach.age,
            "years_pro": coach.years_pro
        }
        for coach in coaches
    ]

# --- Hall of Fame ---
@app.get("/hall-of-fame/coaches")
def get_hof_coaches(session: SessionDep):
    hof_coaches = session.query(Coach).filter(Coach.position == "HOF").all()
    
    return [
        {
            "id": coach.id,
            "first_name": coach.first_name,
            "last_name": coach.last_name,
            "full_name": coach.full_name,
            "position": coach.position,
            "offensive_rating": coach.offensive_rating,
            "defensive_rating": coach.defensive_rating,
            "special_teams_rating": coach.special_teams_rating,
            "leadership": coach.leadership,
            "experience": coach.experience,
            "overall_rating": coach.overall_rating,
            "age": coach.age,
            "years_pro": coach.years_pro
        }
        for coach in hof_coaches
    ]

@app.get("/hall-of-fame/players")
def get_hof_players(session: SessionDep):
    # For now, return top-rated players as "HOF" since we couldn't import HOF players without team_id
    hof_players = session.query(Player).order_by(Player.awareness.desc()).limit(20).all()
    
    return [
        {
            "id": player.id,
            "first_name": player.first_name,
            "last_name": player.last_name,
            "position": player.position,
            "team_id": player.team_id,
            "speed": player.speed,
            "strength": player.strength,
            "agility": player.agility,
            "throw_power": player.throw_power,
            "throw_accuracy": player.throw_accuracy,
            "catching": player.catching,
            "tackling": player.tackling,
            "awareness": player.awareness,
            "potential": player.potential,
            "age": player.age,
            "overall": round((player.speed + player.strength + player.agility + 
                            player.throw_power + player.throw_accuracy + player.catching + 
                            player.tackling + player.awareness) / 8)
        }
        for player in hof_players
    ]

# --- Injury System - Temporarily Disabled ---
# @app.get("/injuries")
# def list_injuries(session: SessionDep, team_id: Optional[int] = Query(default=None)):
#     """Get all active injuries, optionally filtered by team"""
#     query = session.query(PlayerInjury, Player).join(Player)
#     
#     if team_id:
#         query = query.filter(Player.team_id == team_id)
#     
#     # Only show active injuries
#     query = query.filter(PlayerInjury.status.in_([InjuryStatus.INJURED, InjuryStatus.RECOVERING]))
#     
#     results = query.all()
#     
#     return [
#         {
#             "id": injury.id,
#             "player_id": injury.player_id,
#             "player_name": f"{player.first_name} {player.last_name}",
#             "position": player.position,
#             "team_id": player.team_id,
#             "injury_type": injury.injury_type.value,
#             "severity": injury.severity.value,
#             "status": injury.status.value,
#             "weeks_remaining": injury.weeks_remaining,
#             "current_rtp_penalty": injury.current_rtp_penalty,
#             "injury_date": injury.injury_date.isoformat(),
#             "expected_return_date": injury.expected_return_date.isoformat() if injury.expected_return_date else None,
#             "affected_attributes": injury.affected_attributes.split(",") if injury.affected_attributes else []
#         }
#         for injury, player in results
#     ]

# @app.get("/injuries/{player_id}")
# def get_player_injuries(player_id: int, session: SessionDep):
#     """Get all injuries for a specific player"""
#     injuries = session.query(PlayerInjury).filter(PlayerInjury.player_id == player_id).all()
#     
#     return [
#         {
#             "id": injury.id,
#             "injury_type": injury.injury_type.value,
#             "severity": injury.severity.value,
#             "status": injury.status.value,
#             "weeks_remaining": injury.weeks_remaining,
#             "current_rtp_penalty": injury.current_rtp_penalty,
#             "injury_date": injury.injury_date.isoformat(),
#             "expected_return_date": injury.expected_return_date.isoformat() if injury.expected_return_date else None,
#             "affected_attributes": injury.affected_attributes.split(",") if injury.affected_attributes else []
#         }
#         for injury in injuries
#     ]

# @app.post("/injuries/process-weekly")
# def process_weekly_injuries(session: SessionDep, season_year: int = 2025, week: int = 1):
#     """Process weekly injury recovery"""
#     from app.engine.sim_v2 import process_weekly_injuries
#     
#     try:
#         process_weekly_injuries(session, season_year, week)
#         return {
#             "message": f"Weekly injury processing completed for season {season_year}, week {week}",
#             "season_year": season_year,
#             "week": week
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Injury processing error: {str(e)}")

@app.post("/simulate-v2")
def simulate_game_v2_endpoint(home_team_id: int, away_team_id: int, session: SessionDep):
    """Simulate a game using the enhanced v2 engine with injury system"""
    from app.engine.sim_v2 import simulate_game_v2, TeamStub as TeamStub2, GameConfigV2
    
    # Get teams
    home_team = session.query(Team).filter(Team.id == home_team_id).first()
    away_team = session.query(Team).filter(Team.id == away_team_id).first()
    
    if not home_team or not away_team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get players for both teams
    home_players = session.query(Player).filter(Player.team_id == home_team_id).limit(10).all()
    away_players = session.query(Player).filter(Player.team_id == away_team_id).limit(10).all()
    
    # Create team stubs with players
    home_stub = TeamStub2(
        id=home_team.id,
        name=home_team.location_name,
        power_rating=home_team.power_rating or 50,
        players=home_players
    )
    
    away_stub = TeamStub2(
        id=away_team.id,
        name=away_team.location_name,
        power_rating=away_team.power_rating or 50,
        players=away_players
    )
    
    # Create game config
    config = GameConfigV2(
        season_year=2025,
        week=1,
        game_id=f"{home_team_id}@{away_team_id}",
        enable_injuries=True
    )
    
    # Simulate game
    result = simulate_game_v2(home_stub, away_stub, config)
    
    # Process any injuries that occurred
    for player, injury_type in result.injuries:
        from app.engine.sim_v2 import create_injury_from_simulation
        create_injury_from_simulation(session, player, injury_type)
    
    return {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_score": result.home_score,
        "away_score": result.away_score,
        "plays": result.plays,
        "injuries": [
            {
                "player_id": player.id,
                "player_name": f"{player.first_name} {player.last_name}",
                "injury_type": injury_type.value,
                "description": f"{player.first_name} {player.last_name} injured - {injury_type.value}"
            }
            for player, injury_type in result.injuries
        ]
    }

# --- Playoff System ---
@app.get("/playoffs/seeds")
def get_playoff_seeds(session: SessionDep, season: int = 2025):
    """Get playoff seeds for both conferences"""
    try:
        seeds = determine_playoff_teams(session, season)
        
        # Convert to API format
        result = {}
        for conference, conf_seeds in seeds.items():
            result[conference] = [
                {
                    "seed": seed.seed,
                    "team_id": seed.team_record.team_id,
                    "team_name": seed.team_record.team_name,
                    "conference": seed.team_record.conference,
                    "division": seed.team_record.division,
                    "wins": seed.team_record.wins,
                    "losses": seed.team_record.losses,
                    "ties": seed.team_record.ties,
                    "win_percentage": round(seed.team_record.win_percentage, 3),
                    "points_for": seed.team_record.points_for,
                    "points_against": seed.team_record.points_against,
                    "point_differential": seed.team_record.point_differential,
                    "is_division_winner": seed.is_division_winner,
                    "bye": seed.bye
                }
                for seed in conf_seeds
            ]
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Playoff seeds error: {str(e)}")

@app.get("/playoffs/bracket")
def get_playoff_bracket(session: SessionDep, season: int = 2025):
    """Get playoff bracket structure"""
    try:
        bracket = create_playoff_bracket(session, season)
        
        # Convert to API format
        rounds = []
        for round_obj in bracket.rounds:
            games = []
            for game in round_obj.games:
                games.append({
                    "id": game.id,
                    "home_team_id": game.home_team_id,
                    "away_team_id": game.away_team_id,
                    "game_number": game.game_number,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "winner_team_id": game.winner_team_id,
                    "is_played": game.is_played
                })
            
            rounds.append({
                "round_name": round_obj.round_name,
                "round_number": round_obj.round_number,
                "games": games
            })
        
        return {
            "year": bracket.year,
            "created_at": bracket.created_at.isoformat(),
            "rounds": rounds
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Playoff bracket error: {str(e)}")

@app.get("/playoffs/standings")
def get_playoff_standings(session: SessionDep, season: int = 2025):
    """Get playoff standings showing who's in the hunt"""
    try:
        # Get all teams
        teams = session.query(Team).all()
        
        # Get all game results
        game_results = session.query(GameResult).filter(GameResult.season == season).all()
        
        # Calculate team records
        team_records = {}
        for team in teams:
            team_records[team.id] = {
                'team_id': team.id,
                'team_name': f"{team.location_name} {team.nickname or ''}".strip(),
                'conference': team.conference,
                'division': team.division,
                'wins': 0,
                'losses': 0,
                'ties': 0,
                'points_for': 0,
                'points_against': 0
            }
        
        # Process game results
        for game in game_results:
            home_record = team_records[game.home_team_id]
            away_record = team_records[game.away_team_id]
            
            home_record['points_for'] += game.home_score
            home_record['points_against'] += game.away_score
            away_record['points_for'] += game.away_score
            away_record['points_against'] += game.home_score
            
            if game.winner_team_id == game.home_team_id:
                home_record['wins'] += 1
                away_record['losses'] += 1
            elif game.winner_team_id == game.away_team_id:
                away_record['wins'] += 1
                home_record['losses'] += 1
            else:
                home_record['ties'] += 1
                away_record['ties'] += 1
        
        # Get playoff seeds
        seeds = determine_playoff_teams(session, season)
        
        # Create playoff standings
        standings = {}
        for conference in ["AFC", "NFC"]:
            conf_teams = [tr for tr in team_records.values() if tr['conference'] == conference]
            conf_seeds = seeds.get(conference, [])
            
            # Mark teams as in playoffs or in the hunt
            playoff_team_ids = {seed.team_record.team_id for seed in conf_seeds}
            
            for team in conf_teams:
                team['in_playoffs'] = team['team_id'] in playoff_team_ids
                team['playoff_seed'] = next((seed.seed for seed in conf_seeds if seed.team_record.team_id == team['team_id']), None)
                team['win_percentage'] = round((team['wins'] + 0.5 * team['ties']) / max(team['wins'] + team['losses'] + team['ties'], 1), 3)
                team['point_differential'] = team['points_for'] - team['points_against']
            
            # Sort by win percentage
            conf_teams.sort(key=lambda x: x['win_percentage'], reverse=True)
            standings[conference] = conf_teams
        
        return standings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Playoff standings error: {str(e)}")

# --- Score Fidelity System (SFS) ---
@app.get("/sfs/status")
def get_sfs_status(session: SessionDep, season: int = 2025):
    """Get SFS status and calibration information"""
    try:
        # Get recent game results for analysis
        recent_games = session.query(GameResult).filter(GameResult.season == season).limit(100).all()
        
        if not recent_games:
            return {
                "status": "no_data",
                "message": "No game results available for SFS analysis",
                "season": season
            }
        
        # Convert to format expected by SFS
        game_data = []
        for game in recent_games:
            game_data.append({
                "home_score": game.home_score,
                "away_score": game.away_score,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id
            })
        
        # Create SFS system
        sfs = ScoreFidelitySystem()
        
        # Check tolerances
        tolerance_check = sfs.check_tolerances(game_data)
        
        # Calculate current statistics
        all_scores = []
        for game in recent_games:
            all_scores.extend([game.home_score, game.away_score])
        
        current_mean = sum(all_scores) / len(all_scores) if all_scores else 0
        current_stdev = (sum((x - current_mean) ** 2 for x in all_scores) / len(all_scores)) ** 0.5 if all_scores else 0
        
        return {
            "status": "active" if tolerance_check["all_passed"] else "needs_calibration",
            "season": season,
            "games_analyzed": len(recent_games),
            "current_stats": {
                "ppg_mean": round(current_mean, 2),
                "ppg_stdev": round(current_stdev, 2)
            },
            "target_stats": {
                "ppg_mean": 23.5,
                "ppg_stdev": 7.2
            },
            "tolerance_check": tolerance_check,
            "sfs_enabled": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SFS status error: {str(e)}")

@app.post("/sfs/calibrate")
def calibrate_sfs(session: SessionDep, season: int = 2025):
    """Calibrate SFS to match NFL scoring patterns"""
    try:
        # Get all game results for the season
        game_results = session.query(GameResult).filter(GameResult.season == season).all()
        
        if not game_results:
            raise HTTPException(status_code=400, detail="No game results available for calibration")
        
        # Convert to format expected by SFS
        game_data = []
        for game in game_results:
            game_data.append({
                "home_score": game.home_score,
                "away_score": game.away_score,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id
            })
        
        # Create SFS system
        sfs = ScoreFidelitySystem()
        
        # Run auto-calibration
        success = sfs.auto_calibrate(game_data, max_iterations=5)
        
        if success:
            # Save calibration data
            sfs.save_calibration(season)
            
            return {
                "message": f"SFS calibration completed successfully for season {season}",
                "season": season,
                "games_calibrated": len(game_results),
                "calibration_successful": True
            }
        else:
            return {
                "message": f"SFS calibration failed for season {season}",
                "season": season,
                "games_calibrated": len(game_results),
                "calibration_successful": False
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SFS calibration error: {str(e)}")

@app.get("/sfs/config")
def get_sfs_config(season: int = 2025):
    """Get current SFS configuration"""
    try:
        # Return default SFS configuration
        return {
            "season": season,
            "enabled": False,
            "targets": {
                "ppg_mean": 23.5,
                "ppg_stdev": 7.2,
                "quarter_shares": [0.25, 0.25, 0.25, 0.25],
                "score_composition": {"td": 0.6, "fg": 0.3, "safety": 0.1}
            },
            "tolerances": {"ppg": 1.0, "quarter_share": 0.05},
            "knobs": {
                "pace_factor": 1.0,
                "red_zone_td_bias": 1.0,
                "fg_make_bias": {
                    "short": 1.0,
                    "mid": 1.0,
                    "long": 1.0
                },
                "pat_make_bias": 1.0,
                "two_point_attempt_bias": 1.0,
                "two_point_make_bias": 1.0,
                "turnover_bias": 1.0,
                "quarter_shape": {
                    "q1": 1.0,
                    "q2": 1.0,
                    "q3": 1.0,
                    "q4": 1.0
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SFS config error: {str(e)}")

# --- Drive Engine ---
@app.post("/simulate-v3")
def simulate_game_v3_endpoint(home_team_id: int, away_team_id: int, session: SessionDep):
    """Simulate a game using the enhanced v3 engine with drive system"""
    try:
        # Get teams
        home_team = session.query(Team).filter(Team.id == home_team_id).first()
        away_team = session.query(Team).filter(Team.id == away_team_id).first()
        
        if not home_team or not away_team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Get players for both teams
        home_players = session.query(Player).filter(Player.team_id == home_team_id).limit(15).all()
        away_players = session.query(Player).filter(Player.team_id == away_team_id).limit(15).all()
        
        # Create team stubs
        home_stub = TeamStub3(
            id=home_team.id,
            name=home_team.location_name,
            power_rating=home_team.power_rating or 50,
            players=home_players,
            run_pass_ratio=0.4,
            aggression=0.5,
            pace=0.5
        )
        
        away_stub = TeamStub3(
            id=away_team.id,
            name=away_team.location_name,
            power_rating=away_team.power_rating or 50,
            players=away_players,
            run_pass_ratio=0.4,
            aggression=0.5,
            pace=0.5
        )
        
        # Create game config
        config = GameConfigV3(
            season_year=2025,
            week=1,
            game_id=f"{home_team_id}@{away_team_id}",
            enable_injuries=True,
            enable_drive_engine=True,
            enable_sfs=True
        )
        
        # Simulate game
        result = simulate_game_v3(home_stub, away_stub, config)
        
        # Process any injuries that occurred
        for player, injury_type in result.injuries:
            from app.engine.sim_v2 import create_injury_from_simulation
            create_injury_from_simulation(session, player, injury_type)
        
        return {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_score": result.home_score,
            "away_score": result.away_score,
            "home_offense_yards": result.home_offense_yards,
            "away_offense_yards": result.away_offense_yards,
            "home_turnovers": result.home_turnovers,
            "away_turnovers": result.away_turnovers,
            "quarter_scores": result.quarter_scores,
            "plays": result.plays,
            "drives": [
                {
                    "drive_number": drive.drive_number,
                    "team": drive.team,
                    "starting_position": drive.starting_position,
                    "plays": drive.plays,
                    "yards": drive.yards,
                    "time_elapsed": drive.time_elapsed,
                    "outcome": drive.outcome,
                    "points": drive.points
                }
                for drive in result.drives
            ],
            "injuries": [
                {
                    "player_id": player.id,
                    "player_name": f"{player.first_name} {player.last_name}",
                    "injury_type": injury_type.value,
                    "description": f"{player.first_name} {player.last_name} injured - {injury_type.value}"
                }
                for player, injury_type in result.injuries
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Game simulation error: {str(e)}")

@app.post("/simulate-v4")
def simulate_game_v4_endpoint(home_team_id: int, away_team_id: int, session: SessionDep):
    """Simulate a game using the realistic v4 engine with proper stats distribution"""
    try:
        # Get teams
        home_team = session.query(Team).filter(Team.id == home_team_id).first()
        away_team = session.query(Team).filter(Team.id == away_team_id).first()
        
        if not home_team or not away_team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Create team data for realistic simulation
        home_team_data = {
            "id": home_team.id,
            "name": home_team.location_name,
            "power_rating": home_team.power_rating or 50
        }
        away_team_data = {
            "id": away_team.id,
            "name": away_team.location_name,
            "power_rating": away_team.power_rating or 50
        }
        
        # Create team stubs with realistic profiles
        home_stub = create_team_stub_from_db(home_team_data)
        away_stub = create_team_stub_from_db(away_team_data)
        
        # Create game config
        config = GameConfigV4(
            season_year=2025,
            week=1,
            game_id=f"{home_team_id}_{away_team_id}"
        )
        
        # Simulate game with realistic stats
        result = simulate_game_v4(home_stub, away_stub, config)
        
        return {
            "home_team": home_team.location_name,
            "away_team": away_team.location_name,
            "home_score": result.home_score,
            "away_score": result.away_score,
            "home_offense_yards": result.home_offense_yards,
            "away_offense_yards": result.away_offense_yards,
            "home_rushing_yards": result.home_rushing_yards,
            "away_rushing_yards": result.away_rushing_yards,
            "home_passing_yards": result.home_passing_yards,
            "away_passing_yards": result.away_passing_yards,
            "home_turnovers": result.home_turnovers,
            "away_turnovers": result.away_turnovers,
            "home_first_downs": result.home_first_downs,
            "away_first_downs": result.away_first_downs,
            "home_third_down_conversions": result.home_third_down_conversions,
            "away_third_down_conversions": result.away_third_down_conversions,
            "home_third_down_attempts": result.home_third_down_attempts,
            "away_third_down_attempts": result.away_third_down_attempts,
            "home_red_zone_attempts": result.home_red_zone_attempts,
            "away_red_zone_attempts": result.away_red_zone_attempts,
            "home_red_zone_scores": result.home_red_zone_scores,
            "away_red_zone_scores": result.away_red_zone_scores,
            "home_time_of_possession": result.home_time_of_possession,
            "away_time_of_possession": result.away_time_of_possession,
            "home_plays": result.home_plays,
            "away_plays": result.away_plays,
            "home_runs": result.home_runs,
            "away_runs": result.away_runs,
            "home_passes": result.home_passes,
            "away_passes": result.away_passes,
            "plays": result.plays,
            "quarters": result.quarters,
            "version": "v4"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")

@app.post("/simulate-drive")
def simulate_drive_endpoint(
    team_power: int,
    opponent_power: int,
    starting_yard_line: int,
    is_home: bool = True,
    run_pass_ratio: float = 0.4,
    aggression: float = 0.5,
    pace: float = 0.5,
    season_year: int = 2025,
    week: int = 1,
    game_id: str = "1"
):
    """Simulate a single drive using the drive engine"""
    try:
        result = simulate_drive_with_engine(
            team_power=team_power,
            opponent_power=opponent_power,
            starting_yard_line=starting_yard_line,
            is_home=is_home,
            run_pass_ratio=run_pass_ratio,
            aggression=aggression,
            pace=pace,
            season_year=season_year,
            week=week,
            game_id=game_id
        )
        
        return {
            "outcome": result.outcome.value,
            "total_yards": result.total_yards,
            "time_elapsed": result.time_elapsed,
            "points_scored": result.points_scored,
            "starting_position": {
                "yard_line": result.starting_position.yard_line,
                "down": result.starting_position.down,
                "distance": result.starting_position.distance
            },
            "ending_position": {
                "yard_line": result.ending_position.yard_line,
                "down": result.ending_position.down,
                "distance": result.ending_position.distance
            },
            "plays": [
                {
                    "play_type": play.play_type.value,
                    "description": play.description,
                    "yards_gained": play.yards_gained,
                    "success": play.success,
                    "turnover": play.turnover,
                    "touchdown": play.touchdown,
                    "time_elapsed": play.time_elapsed
                }
                for play in result.plays
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drive simulation error: {str(e)}")

@app.get("/drive-engine/config")
def get_drive_engine_config():
    """Get drive engine configuration options"""
    return {
        "play_types": ["run", "pass", "kick", "punt", "field_goal", "touchdown", "interception", "fumble", "safety", "turnover"],
        "drive_outcomes": ["touchdown", "field_goal", "punt", "turnover", "safety", "end_half", "end_game"],
        "slider_ranges": {
            "run_pass_ratio": {"min": 0.0, "max": 1.0, "description": "0.0 = all pass, 1.0 = all run"},
            "aggression": {"min": 0.0, "max": 1.0, "description": "0.0 = conservative, 1.0 = aggressive"},
            "pace": {"min": 0.0, "max": 1.0, "description": "0.0 = slow, 1.0 = fast"},
            "weather_penalty": {"min": 0.0, "max": 1.0, "description": "0.0 = no penalty, 1.0 = severe penalty"},
            "time_pressure": {"min": 0.0, "max": 1.0, "description": "0.0 = no pressure, 1.0 = urgent"}
        },
        "field_position_info": {
            "yard_line_range": {"min": 0, "max": 100, "description": "0 = own goal line, 50 = midfield, 100 = opponent goal line"},
            "red_zone": "Yard line 80+ (inside 20)",
            "goal_line": "Yard line 99+",
            "own_territory": "Yard line 0-50"
        }
    }

# --- Official Schedule Generator ---
@app.post("/schedule/generate")
def generate_schedule(session: SessionDep, year: int = 2025):
    """Generate official 17-game NFL schedule for a season"""
    try:
        # Get all teams
        teams = session.query(Team).all()
        
        if len(teams) != 32:
            raise HTTPException(status_code=400, detail="Must have exactly 32 teams for NFL schedule")
        
        # Generate schedule
        schedule = generate_official_schedule(teams, year)
        
        # Validate schedule
        generator = OfficialScheduleGenerator(year)
        validation = generator.validate_schedule(schedule)
        
        return {
            "year": schedule.year,
            "total_games": schedule.total_games,
            "weeks": len(schedule.weeks),
            "validation": validation,
            "schedule": [
                {
                    "week": week.week,
                    "games": [
                        {
                            "home_team_id": game.home_team_id,
                            "away_team_id": game.away_team_id,
                            "game_type": game.game_type.value,
                            "source": game.source
                        }
                        for game in week.games
                    ]
                }
                for week in schedule.weeks
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schedule generation error: {str(e)}")

@app.get("/schedule/team/{team_id}")
def get_team_schedule(team_id: int, session: SessionDep, season: int = 2025):
    """Get schedule for a specific team"""
    try:
        team = session.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # This would query the actual schedule from database
        # For now, return a placeholder
        return {
            "team_id": team_id,
            "team_name": f"{team.location_name} {team.nickname}",
            "season": season,
            "games": []  # Would be populated from database
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team schedule error: {str(e)}")

@app.get("/schedule/week/{week}")
def get_week_schedule(week: int, session: SessionDep, season: int = 2025):
    """Get schedule for a specific week"""
    try:
        if week < 1 or week > 18:
            raise HTTPException(status_code=400, detail="Week must be between 1 and 18")
        
        # This would query the actual schedule from database
        return {
            "week": week,
            "season": season,
            "games": []  # Would be populated from database
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Week schedule error: {str(e)}")

# --- Awards System ---
@app.post("/awards/calculate/{season}")
def calculate_season_awards(season: int, session: SessionDep):
    """Calculate all awards for a season"""
    try:
        awards_system = AwardsSystem(session)
        awards = awards_system.calculate_season_awards(season)
        
        # Save awards to database
        for award in awards:
            session.add(award)
        session.commit()
        
        return {
            "season": season,
            "awards_calculated": len(awards),
            "awards": [
                {
                    "id": award.id,
                    "award_type": award.award_type.value,
                    "category": award.category.value,
                    "player_id": award.player_id,
                    "coach_id": award.coach_id,
                    "team_id": award.team_id,
                    "conference": award.conference,
                    "division": award.division,
                    "stats": award.stats
                }
                for award in awards
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Awards calculation error: {str(e)}")

@app.get("/awards/player/{player_id}")
def get_player_awards(player_id: int, session: SessionDep, season: Optional[int] = None):
    """Get all awards for a specific player"""
    try:
        player = session.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        awards_system = AwardsSystem(session)
        awards = awards_system.get_player_awards(player_id, season)
        
        return {
            "player_id": player_id,
            "player_name": f"{player.first_name} {player.last_name}",
            "season": season,
            "awards": [
                {
                    "id": award.id,
                    "award_type": award.award_type.value,
                    "category": award.category.value,
                    "season": award.season,
                    "team_id": award.team_id,
                    "conference": award.conference,
                    "division": award.division,
                    "stats": award.stats
                }
                for award in awards
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Player awards error: {str(e)}")

@app.get("/awards/team/{team_id}")
def get_team_awards(team_id: int, session: SessionDep, season: Optional[int] = None):
    """Get all awards for a specific team"""
    try:
        team = session.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        awards_system = AwardsSystem(session)
        awards = awards_system.get_team_awards(team_id, season)
        
        return {
            "team_id": team_id,
            "team_name": f"{team.location_name} {team.nickname}",
            "season": season,
            "awards": [
                {
                    "id": award.id,
                    "award_type": award.award_type.value,
                    "category": award.category.value,
                    "season": award.season,
                    "player_id": award.player_id,
                    "coach_id": award.coach_id,
                    "conference": award.conference,
                    "division": award.division,
                    "stats": award.stats
                }
                for award in awards
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team awards error: {str(e)}")

@app.get("/awards/season/{season}")
def get_season_awards_summary(season: int, session: SessionDep):
    """Get summary of all awards for a season"""
    try:
        awards_system = AwardsSystem(session)
        summary = awards_system.get_season_awards_summary(season)
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Season awards summary error: {str(e)}")

@app.get("/awards/types")
def get_award_types():
    """Get all available award types"""
    return {
        "award_types": [
            {
                "type": award_type.value,
                "name": award_type.value.replace("_", " ").title(),
                "description": f"{award_type.value.replace('_', ' ').title()} Award"
            }
            for award_type in AwardType
        ],
        "categories": [
            {
                "category": category.value,
                "name": category.value.replace("_", " ").title(),
                "description": f"{category.value.replace('_', ' ').title()} Award"
            }
            for category in AwardCategory
        ]
    }


# === CHAMPIONSHIP & ENHANCED OFFS mixing ENDPOINTS ===

@app.get("/championships/history")
def get_championship_history_api(session: SessionDep):
    """Get championship history"""
    try:
        from app.services.championship_manager import ChampionshipManager
        
        championship_manager = ChampionshipManager(session)
        history = championship_manager.get_championship_history()
        
        return {
            "championships": history,
            "total_championships": len(history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting championship history: {str(e)}")


@app.get("/championships/leaders")
def get_championship_leaders_api(session: SessionDep):
    """Get teams ranked by championship count"""
    try:
        from app.services.championship_manager import ChampionshipManager
        
        championship_manager = ChampionshipManager(session)
        leaders = championship_manager.get_league_championship_leaders()
        
        return {
            "leaders": [
                {
                    "team_id": leader.team_id,
                    "team_name": leader.team_name,
                    "total_championships": leader.total_championships,
                    "last_championship": leader.last_championship
                }
                for leader in leaders
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting championship leaders: {str(e)}")


@app.get("/offseason/summary/{season}")
def get_offseason_summary_api(session: SessionDep, season: int):
    """Get offseason summary for a season"""
    try:
        from app.services.offseason_manager import OffseasonManager
        
        offseason_manager = OffseasonManager(session, season)
        summary = offseason_manager.get_offseason_summary()
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting offseason summary: {str(e)}")


@app.post("/offseason/process/{season}")
def process_offseason_api(session: SessionDep, season: int, champion_id: int = None):
    """Manually process offseason for a season"""
    try:
        from app.services.offseason_manager import OffseasonManager
        
        offseason_manager = OffseasonManager(session, season)
        results = offseason_manager.process_offseason(champion_id)
        
        return {
            "season": season,
            "draft_picks": len(results.draft_results),
            "free_agent_signings": len(results.free_agent_signings),
            "coaching_changes": len(results.coaching_changes),
            "team_progression": len(results.team_progression),
            "status": "completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing offseason: {str(e)}")


# === ENHANCED SEASON INTEGRATION ENDPOINTS ===

@app.get("/season/integration/status")
def get_season_integration_status_api(session: SessionDep, season: int = 2025):
    """Get comprehensive season integration status"""
    try:
        # from app.engine.season_progression import get_season_progression_manager  # Temporarily disabled
        
        # progression_manager = get_season_progression_manager(session, season)
        state = progression_manager.get_current_state()
        summary = progression_manager.get_season_summary()
        
        return {
            "season": season,
            "current_phase": state.current_phase.value,
            "current_week": state.current_week,
            "regular_season_complete": state.regular_season_complete,
            "playoffs_complete": state.playoffs_complete,
            "offseason_complete": state.offseason_complete,
            "champion": {
                "id": state.champion_id,
                "name": state.champion_name
            },
            "summary": summary,
            "integration_status": "enhanced"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting season integration status: {str(e)}")


@app.post("/season/integration/complete-season")
def complete_season_integration_api(session: SessionDep, season: int = 2025):
    """Complete the full season integration (awards + offseason + championship celebration)"""
    try:
        # from app.engine.season_progression import get_season_progression_manager  # Temporarily disabled
        
        # progression_manager = get_season_progression_manager(session, season)
        
        # Process complete offseason if not already done
        if not progression_manager.state.offseason_complete:
            result = progression_manager.complete_season()
        else:
            result = {"message": f"Season {season} already completed"}
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing season integration: {str(e)}")


# === NEW SIMULATION ENDPOINTS ===

@app.post("/simulate/game")
def simulate_game_endpoint(request: dict):
    """
    Simulate a single game and return detailed results with JSON logging
    
    Body: {
        "homeId": int,
        "awayId": int, 
        "engine": "v1"|"v2"|"v3"|"v4"|null,
        "season_year": int (optional, default 2025),
        "week": int (optional, default 1)
    }
    """
    import json
    import os
    from datetime import datetime
    
    try:
        # Extract request parameters
        home_id = request.get("homeId", 1)
        away_id = request.get("awayId", 2)
        engine = request.get("engine", "pbp")  # Default to PBP engine
        season_year = request.get("season_year", 2025)
        week = request.get("week", 1)
        
        # Build team stubs (placeholder names for now)
        home = TeamStub(id=home_id, name=f"Team {home_id}", offense=75, defense=75)
        away = TeamStub(id=away_id, name=f"Team {away_id}", offense=70, defense=70)
        config = GameConfig(season_year=season_year, week=week, game_id=1)
        
        # Choose engine
        engine_map = {
            "v1": sim_v1,
            "v2": sim_v2, 
            "v3": sim_v3,
            "v4": sim_v4,
            # "pbp": sim_pbp  # Temporarily disabled
        }
        
        if engine not in engine_map:
            engine = "v4"  # Default to v4 engine
        
        simulate_func = engine_map[engine]
        
        # Run simulation
        result = simulate_func(home, away, config)
        
        # Create JSON log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "home_team_id": home_id,
            "away_team_id": away_id,
            "engine": engine,
            "season_year": season_year,
            "week": week,
            "result": {
                "home_score": result.final_home,
                "away_score": result.final_away,
                "plays": [{"quarter": p.quarter, "clock": p.clock, "down": p.down, 
                          "distance": p.distance, "yardline": p.yardline, "desc": p.desc} 
                         for p in result.plays],
                "boxscore": result.boxscore
            }
        }
        
        # Ensure reports directory exists
        reports_dir = "data/reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        # Write JSON log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{reports_dir}/last_game_{timestamp}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_entry, f, indent=2)
        
        # Return the simulation result directly
        return {
            "home_team_id": result.home_team_id,
            "away_team_id": result.away_team_id,
            "final_home": result.final_home,
            "final_away": result.final_away,
            "plays": result.plays,
            "boxscore": result.boxscore,
            "log_file": log_file
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")


@app.get("/last-game")
def get_last_game():
    """Read the most recent game JSON log from data/reports"""
    import json
    import os
    import glob
    
    try:
        reports_dir = "data/reports"
        if not os.path.exists(reports_dir):
            return {"error": "No reports directory found"}
        
        # Find all last_game_*.json files
        pattern = os.path.join(reports_dir, "last_game_*.json")
        files = glob.glob(pattern)
        
        if not files:
            return {"error": "No game logs found"}
        
        # Get the most recent file
        latest_file = max(files, key=os.path.getctime)
        
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading last game: {str(e)}")


@app.post("/simulate/week")
def simulate_week_endpoint(request: dict):
    """
    Simulate a full week of games
    
    Body: {
        "season_year": int (optional, default 2025),
        "week": int (optional, default 1),
        "engine": str (optional, default "v4"),
        "num_games": int (optional, default 8)
    }
    """
    try:
        season_year = request.get("season_year", 2025)
        week = request.get("week", 1)
        engine = request.get("engine", "v4")
        num_games = request.get("num_games", 8)
        
        results = []
        
        for i in range(num_games):
            # Create team stubs with different IDs
            home_id = (i * 2) + 1
            away_id = (i * 2) + 2
            
            # Simulate the game
            game_request = {
                "homeId": home_id,
                "awayId": away_id,
                "engine": engine,
                "season_year": season_year,
                "week": week
            }
            
            game_result = simulate_game_endpoint(game_request)
            results.append({
                "game": i + 1,
                "home_team": f"Team {home_id}",
                "away_team": f"Team {away_id}",
                "score": f"{game_result['final_home']}-{game_result['final_away']}",
                "winner": "home" if game_result['final_home'] > game_result['final_away'] else "away"
            })
        
        return {
            "season_year": season_year,
            "week": week,
            "engine": engine,
            "games_simulated": num_games,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Week simulation error: {str(e)}")
