import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.core.db import engine
from app.models.sim_models import Game
from app.models.results import TeamGameStats, PlayerBox
from app.services.results_service import (
    record_game_result, upsert_team_game, bulk_upsert_player_boxes,
    week_scoreboard, team_schedule, game_box
)
from app.engine.results_hooks import persist_full_game

def test_record_game_result(seeded_db):
    """Test recording game results."""
    # Create a game first
    game = Game(season=2034, week=1, home_team_id=1, away_team_id=2)
    seeded_db.add(game)
    seeded_db.commit()
    seeded_db.refresh(game)
    
    # Record the result
    record_game_result(seeded_db, 2034, 1, game.id, 24, 17)
    
    # Verify the result was recorded
    game_updated = seeded_db.get(Game, game.id)
    assert game_updated is not None
    assert game_updated.home_score == 24
    assert game_updated.away_score == 17
    assert game_updated.status == "final"

def test_upsert_team_game(seeded_db):
    """Test upserting team game stats."""
    # Create a game
    game = Game(season=2034, week=1, home_team_id=1, away_team_id=2)
    seeded_db.add(game)
    seeded_db.commit()
    seeded_db.refresh(game)
    
    # Upsert team stats
    team_stats = {
        "game_id": game.id,
        "season": 2034,
        "week": 1,
        "team_id": 1,
        "points": 24,
        "yards_offense": 350,
        "pass_yds": 250,
        "rush_yds": 100,
        "takeaways": 2,
        "giveaways": 1,
        "sacks": 3,
        "third_down_pct": 0.45,
        "red_zone_td_pct": 0.67,
        "time_of_possession_sec": 1800
    }
    
    result = upsert_team_game(seeded_db, team_stats)
    assert result is not None
    assert result.team_id == 1
    assert result.points == 24
    assert result.yards_offense == 350
    
    # Test update (upsert again with different values)
    team_stats["points"] = 28
    team_stats["yards_offense"] = 400
    result2 = upsert_team_game(seeded_db, team_stats)
    assert result2.id == result.id  # Same record
    assert result2.points == 28
    assert result2.yards_offense == 400

def test_bulk_upsert_player_boxes(seeded_db):
    """Test bulk upserting player box scores."""
    # Create a game
    game = Game(season=2034, week=1, home_team_id=1, away_team_id=2)
    seeded_db.add(game)
    seeded_db.commit()
    seeded_db.refresh(game)
    
    # Create player boxes
    player_boxes = [
        {
            "game_id": game.id,
            "season": 2034,
            "week": 1,
            "team_id": 1,
            "opponent_id": 2,
            "player_id": 101,
            "pos": "QB",
            "pass_att": 30,
            "pass_cmp": 20,
            "pass_yds": 250,
            "pass_td": 2,
            "pass_int": 1,
            "rush_att": 5,
            "rush_yds": 25,
            "rush_td": 0
        },
        {
            "game_id": game.id,
            "season": 2034,
            "week": 1,
            "team_id": 1,
            "opponent_id": 2,
            "player_id": 102,
            "pos": "WR",
            "rec_tgt": 8,
            "rec_rec": 6,
            "rec_yds": 120,
            "rec_td": 1
        }
    ]
    
    bulk_upsert_player_boxes(seeded_db, player_boxes)
    
    # Verify the boxes were created
    boxes = list(seeded_db.exec(select(PlayerBox).where(PlayerBox.game_id == game.id)))
    assert len(boxes) == 2
    
    qb_box = next(box for box in boxes if box.player_id == 101)
    assert qb_box.pos == "QB"
    assert qb_box.pass_yds == 250
    assert qb_box.pass_td == 2
    
    wr_box = next(box for box in boxes if box.player_id == 102)
    assert wr_box.pos == "WR"
    assert wr_box.rec_yds == 120
    assert wr_box.rec_td == 1

def test_week_scoreboard(seeded_db):
    """Test getting week scoreboard."""
    # Create games for week 1
    game1 = Game(season=2034, week=1, home_team_id=1, away_team_id=2)
    game2 = Game(season=2034, week=1, home_team_id=3, away_team_id=4)
    seeded_db.add(game1)
    seeded_db.add(game2)
    seeded_db.commit()
    seeded_db.refresh(game1)
    seeded_db.refresh(game2)
    
    # Add results by updating the games
    game1.home_score = 24
    game1.away_score = 17
    game1.status = "final"
    game2.home_score = 14
    game2.away_score = 28
    game2.status = "final"
    seeded_db.add(game1)
    seeded_db.add(game2)
    seeded_db.commit()
    
    # Get scoreboard
    scoreboard = week_scoreboard(seeded_db, 2034, 1)
    assert len(scoreboard) == 2
    
    # Check first game
    game1_data = next(g for g in scoreboard if g["game_id"] == game1.id)
    assert game1_data["home_team_id"] == 1
    assert game1_data["away_team_id"] == 2
    assert game1_data["home_score"] == 24
    assert game1_data["away_score"] == 17
    
    # Check second game
    game2_data = next(g for g in scoreboard if g["game_id"] == game2.id)
    assert game2_data["home_team_id"] == 3
    assert game2_data["away_team_id"] == 4
    assert game2_data["home_score"] == 14
    assert game2_data["away_score"] == 28

def test_team_schedule(seeded_db):
    """Test getting team schedule."""
    # Create games for team 1
    game1 = Game(season=2034, week=1, home_team_id=1, away_team_id=2)
    game2 = Game(season=2034, week=2, home_team_id=3, away_team_id=1)
    game3 = Game(season=2034, week=3, home_team_id=1, away_team_id=4)
    seeded_db.add(game1)
    seeded_db.add(game2)
    seeded_db.add(game3)
    seeded_db.commit()
    seeded_db.refresh(game1)
    seeded_db.refresh(game2)
    seeded_db.refresh(game3)
    
    # Add results by updating the games
    game1.home_score = 24
    game1.away_score = 17
    game1.status = "final"
    game2.home_score = 14
    game2.away_score = 21
    game2.status = "final"
    game3.home_score = 28
    game3.away_score = 14
    game3.status = "final"
    seeded_db.add(game1)
    seeded_db.add(game2)
    seeded_db.add(game3)
    seeded_db.commit()
    
    # Get team schedule
    schedule = team_schedule(seeded_db, 2034, 1)
    assert len(schedule) == 3
    
    # Check that games are sorted by week
    assert schedule[0]["week"] == 1
    assert schedule[1]["week"] == 2
    assert schedule[2]["week"] == 3
    
    # Check week 1 (home game)
    week1 = schedule[0]
    assert week1["home_team_id"] == 1
    assert week1["away_team_id"] == 2
    assert week1["home_score"] == 24
    assert week1["away_score"] == 17
    
    # Check week 2 (away game)
    week2 = schedule[1]
    assert week2["home_team_id"] == 3
    assert week2["away_team_id"] == 1
    assert week2["home_score"] == 14
    assert week2["away_score"] == 21

def test_game_box(seeded_db):
    """Test getting game box score."""
    # Create a game
    game = Game(season=2034, week=1, home_team_id=1, away_team_id=2)
    seeded_db.add(game)
    seeded_db.commit()
    seeded_db.refresh(game)
    
    # Add team stats
    home_stats = TeamGameStats(
        game_id=game.id, season=2034, week=1, team_id=1,
        points=24, yards_offense=350, pass_yds=250, rush_yds=100,
        takeaways=2, giveaways=1, sacks=3,
        third_down_pct=0.45, red_zone_td_pct=0.67, time_of_possession_sec=1800
    )
    away_stats = TeamGameStats(
        game_id=game.id, season=2034, week=1, team_id=2,
        points=17, yards_offense=280, pass_yds=200, rush_yds=80,
        takeaways=1, giveaways=2, sacks=2,
        third_down_pct=0.35, red_zone_td_pct=0.50, time_of_possession_sec=1500
    )
    seeded_db.add(home_stats)
    seeded_db.add(away_stats)
    
    # Add player boxes
    qb_box = PlayerBox(
        game_id=game.id, season=2034, week=1, team_id=1, opponent_id=2,
        player_id=101, pos="QB", pass_att=30, pass_cmp=20, pass_yds=250, pass_td=2, pass_int=1
    )
    wr_box = PlayerBox(
        game_id=game.id, season=2034, week=1, team_id=1, opponent_id=2,
        player_id=102, pos="WR", rec_tgt=8, rec_rec=6, rec_yds=120, rec_td=1
    )
    seeded_db.add(qb_box)
    seeded_db.add(wr_box)
    seeded_db.commit()
    
    # Get box score
    box = game_box(seeded_db, game.id)
    
    # Check teams
    assert len(box["teams"]) == 2
    home_team_data = next(t for t in box["teams"] if t["team_id"] == 1)
    assert home_team_data["points"] == 24
    assert home_team_data["yards_offense"] == 350
    
    away_team_data = next(t for t in box["teams"] if t["team_id"] == 2)
    assert away_team_data["points"] == 17
    assert away_team_data["yards_offense"] == 280
    
    # Check players
    assert len(box["players"]) == 2
    qb_data = next(p for p in box["players"] if p["player_id"] == 101)
    assert qb_data["pos"] == "QB"
    assert qb_data["pass_yds"] == 250
    assert qb_data["pass_td"] == 2
    
    wr_data = next(p for p in box["players"] if p["player_id"] == 102)
    assert wr_data["pos"] == "WR"
    assert wr_data["rec_yds"] == 120
    assert wr_data["rec_td"] == 1

def test_persist_full_game(seeded_db):
    """Test the complete game persistence hook."""
    season, week, game_id = 2034, 1, 5001
    home_team, away_team = 1, 2
    
    # Persist a full game
    persist_full_game(
        seeded_db, season=season, week=week, game_id=game_id,
        home_score=27, away_score=23,
        home_team_line={
            "team_id": home_team, 
            "yards_offense": 360, 
            "pass_yds": 245, 
            "rush_yds": 115, 
            "takeaways": 2, 
            "giveaways": 1, 
            "sacks": 3, 
            "third_down_pct": 0.42, 
            "red_zone_td_pct": 0.67, 
            "time_of_possession_sec": 1850
        },
        away_team_line={
            "team_id": away_team, 
            "yards_offense": 330, 
            "pass_yds": 280, 
            "rush_yds": 50, 
            "takeaways": 1, 
            "giveaways": 2, 
            "sacks": 2, 
            "third_down_pct": 0.38, 
            "red_zone_td_pct": 0.50, 
            "time_of_possession_sec": 1750
        },
        player_boxes=[
            {
                "game_id": game_id, 
                "season": season, 
                "week": week, 
                "team_id": home_team, 
                "opponent_id": away_team, 
                "player_id": 101, 
                "pos": "QB", 
                "pass_att": 30, 
                "pass_cmp": 20, 
                "pass_yds": 245, 
                "pass_td": 2, 
                "pass_int": 1
            },
            {
                "game_id": game_id, 
                "season": season, 
                "week": week, 
                "team_id": away_team, 
                "opponent_id": home_team, 
                "player_id": 201, 
                "pos": "WR", 
                "rec_tgt": 9, 
                "rec_rec": 6, 
                "rec_yds": 110, 
                "rec_td": 1
            }
        ]
    )
    
    # Verify game result
    game_updated = seeded_db.get(Game, game_id)
    assert game_updated is not None
    assert game_updated.home_score == 27
    assert game_updated.away_score == 23
    assert game_updated.status == "final"
    
    # Verify team stats
    home_stats = seeded_db.exec(select(TeamGameStats).where(
        TeamGameStats.game_id == game_id, 
        TeamGameStats.team_id == home_team
    )).first()
    assert home_stats is not None
    assert home_stats.points == 27
    assert home_stats.yards_offense == 360
    
    away_stats = seeded_db.exec(select(TeamGameStats).where(
        TeamGameStats.game_id == game_id, 
        TeamGameStats.team_id == away_team
    )).first()
    assert away_stats is not None
    assert away_stats.points == 23
    assert away_stats.yards_offense == 330
    
    # Verify player boxes
    qb_box = seeded_db.exec(select(PlayerBox).where(
        PlayerBox.game_id == game_id, 
        PlayerBox.player_id == 101
    )).first()
    assert qb_box is not None
    assert qb_box.pos == "QB"
    assert qb_box.pass_yds == 245
    assert qb_box.pass_td == 2
    
    wr_box = seeded_db.exec(select(PlayerBox).where(
        PlayerBox.game_id == game_id, 
        PlayerBox.player_id == 201
    )).first()
    assert wr_box is not None
    assert wr_box.pos == "WR"
    assert wr_box.rec_yds == 110
    assert wr_box.rec_td == 1

def test_api_endpoints_exist():
    """Test that API endpoints are properly registered."""
    from app.main import app
    
    # Check that the router is registered
    routes = [route.path for route in app.routes]
    assert "/api/v1/schedule/week" in routes
    assert "/api/v1/schedule/team" in routes
    assert "/api/v1/results/box" in routes

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
