import pytest
from sqlmodel import Session, select, create_engine, SQLModel
from app.models.standings import Standings
from app.models.schedule import Game, GameResult
from app.models.playoffs import PlayoffBracket
from app.services.standings_service import (
    apply_result, recompute_sos, get_standings, get_power_rankings,
    calculate_win_percentage, get_standings_summary
)
from app.services.seeding_service import (
    seed_conference, seed_both_conferences, get_playoff_seeds,
    validate_playoff_seeds, _win_pct, _sort_key
)
from app.services.bracket_service import (
    generate_bracket, get_bracket_seeds, get_detailed_bracket,
    create_playoff_matchups, get_playoff_summary, is_playoff_team
)
from app.services.results_pipeline import (
    on_game_final, get_standings_snapshot, get_weekly_summary,
    validate_standings, reset_standings, initialize_standings
)

@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_apply_result_updates_pr_and_wins(client, seeded_db):
    """Test that applying game results updates power ratings and wins."""
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.team import Team
    from app.models.schedule import Game, GameResult
    from app.models.standings import Standings
    from app.services.results_pipeline import on_game_final

    season = 2033
    with Session(get_engine()) as sess:
        t1 = Team(team_id=101, name="A", conference="AFC", division="E")
        t2 = Team(team_id=102, name="B", conference="AFC", division="E")
        sess.add(t1)
        sess.add(t2)
        sess.commit()
        
        g = Game(season=season, week=1, home_team_id=101, away_team_id=102)
        sess.add(g)
        sess.commit()
        sess.refresh(g)
        
        r = GameResult(game_id=g.id, home_score=24, away_score=17)
        sess.add(r)
        sess.commit()

        on_game_final(sess, season, g.id, week=1)

        s1 = sess.exec(select(Standings).where(Standings.season == season, Standings.team_id == 101)).first()
        s2 = sess.exec(select(Standings).where(Standings.season == season, Standings.team_id == 102)).first()
        
        assert s1 and s1.wins == 1 and s2 and s2.losses == 1
        assert abs(s1.power_rating - 1500.0) > 0.1 and abs(s2.power_rating - 1500.0) > 0.1

def test_bracket_generation(client, seeded_db):
    """Test playoff bracket generation."""
    from sqlmodel import Session
    from app.db import get_engine
    from app.models.team import Team
    from app.models.standings import Standings
    from app.services.bracket_service import generate_bracket

    season = 2033
    with Session(get_engine()) as sess:
        # Seed 8 AFC teams with different records
        divs = ["N", "E", "S", "W"]
        for i in range(1, 9):
            sess.add(Team(team_id=200+i, name=f"T{i}", conference="AFC", division=divs[(i-1)%4]))
            s = Standings(
                season=season, 
                team_id=200+i, 
                wins=10-(i//2), 
                losses=6+(i//2), 
                power_rating=1500+i*5
            )
            sess.add(s)
        sess.commit()
        
        b = generate_bracket(sess, season)
        assert b and b.afc_seeds_csv

    r = client.get(f"/api/v1/standings/bracket?season={season}")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["afc_seeds"], list)

def test_win_percentage_calculation():
    """Test win percentage calculation."""
    standings = Standings(
        season=2024,
        team_id=1,
        wins=10,
        losses=6,
        ties=0,
        power_rating=1500.0
    )
    
    win_pct = calculate_win_percentage(standings)
    assert win_pct == 10.0 / 16.0
    
    # Test with ties
    standings.ties = 2
    win_pct = calculate_win_percentage(standings)
    assert win_pct == (10.0 + 0.5 * 2) / 18.0

def test_power_rating_elo_calculation(session: Session):
    """Test ELO power rating calculations."""
    # Create test teams and game
    team1 = Standings(season=2024, team_id=1, power_rating=1500.0)
    team2 = Standings(season=2024, team_id=2, power_rating=1500.0)
    
    session.add(team1)
    session.add(team2)
    session.commit()
    
    # Create game and result
    game = Game(season=2024, week=1, home_team_id=1, away_team_id=2)
    session.add(game)
    session.commit()
    session.refresh(game)
    
    result = GameResult(game_id=game.id, home_score=24, away_score=17)
    session.add(result)
    session.commit()
    
    # Apply result
    apply_result(session, 2024, game.id)
    
    # Check power ratings changed
    updated_team1 = session.get(Standings, team1.id)
    updated_team2 = session.get(Standings, team2.id)
    
    assert updated_team1.power_rating > 1500.0  # Home team won
    assert updated_team2.power_rating < 1500.0  # Away team lost
    assert updated_team1.wins == 1
    assert updated_team2.losses == 1

def test_conference_seeding(session: Session):
    """Test conference seeding logic."""
    # Create test teams with different records
    teams = []
    for i in range(8):
        team = Standings(
            season=2024,
            team_id=i+1,
            wins=10-i,
            losses=6+i,
            power_rating=1500.0 + i*10
        )
        teams.append(team)
        session.add(team)
    
    session.commit()
    
    # Test seeding
    seeds = seed_conference(session, 2024, "AFC")
    assert len(seeds) <= 7  # Max 7 playoff teams per conference

def test_playoff_bracket_generation(session: Session):
    """Test playoff bracket generation."""
    # Create test teams
    teams = []
    for i in range(16):  # 8 AFC + 8 NFC
        conference = "AFC" if i < 8 else "NFC"
        team = Standings(
            season=2024,
            team_id=i+1,
            wins=10-(i%4),
            losses=6+(i%4),
            power_rating=1500.0 + i*5
        )
        teams.append(team)
        session.add(team)
    
    session.commit()
    
    # Generate bracket
    bracket = generate_bracket(session, 2024)
    assert bracket is not None
    assert bracket.season == 2024
    assert bracket.afc_seeds_csv
    assert bracket.nfc_seeds_csv

def test_standings_api_endpoints(client, seeded_db):
    """Test standings API endpoints."""
    # Test league standings
    r = client.get("/api/v1/standings/league?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test power rankings
    r = client.get("/api/v1/standings/power_rankings?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    # Test playoff seeds
    r = client.get("/api/v1/standings/seeds?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "AFC" in data
    assert "NFC" in data
    
    # Test playoff bracket
    r = client.get("/api/v1/standings/bracket?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "season" in data
    assert "afc_seeds" in data
    assert "nfc_seeds" in data

def test_conference_standings_api(client, seeded_db):
    """Test conference standings API."""
    r = client.get("/api/v1/standings/conference/AFC?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    
    r = client.get("/api/v1/standings/conference/NFC?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_division_standings_api(client, seeded_db):
    """Test division standings API."""
    r = client.get("/api/v1/standings/division/AFC/E?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_team_standings_api(client, seeded_db):
    """Test team standings API."""
    r = client.get("/api/v1/standings/team/1?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "team_id" in data
    assert "standings" in data
    assert "playoff_info" in data

def test_standings_snapshot_api(client, seeded_db):
    """Test standings snapshot API."""
    r = client.get("/api/v1/standings/snapshot?season=2024&week=1")
    assert r.status_code == 200
    data = r.json()
    assert "season" in data
    assert "week" in data
    assert "standings" in data
    assert "power_rankings" in data

def test_weekly_summary_api(client, seeded_db):
    """Test weekly summary API."""
    r = client.get("/api/v1/standings/weekly_summary?season=2024&week=1")
    assert r.status_code == 200
    data = r.json()
    assert "season" in data
    assert "week" in data
    assert "standings_summary" in data
    assert "playoff_summary" in data

def test_validate_standings_api(client, seeded_db):
    """Test standings validation API."""
    r = client.get("/api/v1/standings/validate?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "valid" in data
    assert "issues" in data
    assert "season" in data

def test_generate_bracket_api(client, seeded_db):
    """Test bracket generation API."""
    r = client.post("/api/v1/standings/generate_bracket", json={"season": 2024})
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert "season" in data

def test_reset_standings_api(client, seeded_db):
    """Test reset standings API."""
    r = client.post("/api/v1/standings/reset", json={"season": 2024})
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert "season" in data

def test_initialize_standings_api(client, seeded_db):
    """Test initialize standings API."""
    r = client.post("/api/v1/standings/initialize", json={
        "season": 2024,
        "team_ids": [1, 2, 3, 4]
    })
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert "season" in data
    assert "teams" in data

def test_playoff_teams_api(client, seeded_db):
    """Test playoff teams API."""
    r = client.get("/api/v1/standings/playoff_teams?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "AFC" in data
    assert "NFC" in data

def test_is_playoff_team_api(client, seeded_db):
    """Test is playoff team API."""
    r = client.get("/api/v1/standings/is_playoff_team/1?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "team_id" in data
    assert "season" in data
    assert "is_playoff_team" in data
    assert "playoff_seed" in data

def test_standings_summary_api(client, seeded_db):
    """Test standings summary API."""
    r = client.get("/api/v1/standings/summary?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "season" in data
    assert "total_teams" in data

def test_playoff_summary_api(client, seeded_db):
    """Test playoff summary API."""
    r = client.get("/api/v1/standings/playoff_summary?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "season" in data
    assert "generated" in data

def test_detailed_bracket_api(client, seeded_db):
    """Test detailed bracket API."""
    r = client.get("/api/v1/standings/detailed_bracket?season=2024")
    assert r.status_code == 200
    data = r.json()
    assert "season" in data
    assert "seeds" in data
    assert "detailed_seeds" in data

def test_playoff_matchups_api(client, seeded_db):
    """Test playoff matchups API."""
    r = client.get("/api/v1/standings/matchups?season=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_standings_models(session: Session):
    """Test standings model creation and validation."""
    standings = Standings(
        season=2024,
        team_id=1,
        wins=10,
        losses=6,
        ties=0,
        points_for=300,
        points_against=250,
        division_wins=4,
        division_losses=2,
        conference_wins=8,
        conference_losses=4,
        sos=0.05,
        power_rating=1550.0
    )
    
    session.add(standings)
    session.commit()
    session.refresh(standings)
    
    assert standings.id is not None
    assert standings.season == 2024
    assert standings.team_id == 1
    assert standings.wins == 10
    assert standings.power_rating == 1550.0

def test_game_models(session: Session):
    """Test game and game result models."""
    game = Game(
        season=2024,
        week=1,
        home_team_id=1,
        away_team_id=2
    )
    
    session.add(game)
    session.commit()
    session.refresh(game)
    
    result = GameResult(
        game_id=game.id,
        home_score=24,
        away_score=17
    )
    
    session.add(result)
    session.commit()
    session.refresh(result)
    
    assert game.id is not None
    assert result.id is not None
    assert result.game_id == game.id

def test_playoff_bracket_model(session: Session):
    """Test playoff bracket model."""
    bracket = PlayoffBracket(
        season=2024,
        afc_seeds_csv="1,2,3,4,5,6,7",
        nfc_seeds_csv="8,9,10,11,12,13,14"
    )
    
    session.add(bracket)
    session.commit()
    session.refresh(bracket)
    
    assert bracket.id is not None
    assert bracket.season == 2024
    assert bracket.afc_seeds_csv == "1,2,3,4,5,6,7"
    assert bracket.nfc_seeds_csv == "8,9,10,11,12,13,14"

def test_sos_recomputation(session: Session):
    """Test strength of schedule recomputation."""
    # Create teams with different power ratings
    teams = []
    for i in range(4):
        team = Standings(
            season=2024,
            team_id=i+1,
            power_rating=1500.0 + i*100
        )
        teams.append(team)
        session.add(team)
    
    session.commit()
    
    # Create games between teams
    games = [
        Game(season=2024, week=1, home_team_id=1, away_team_id=2),
        Game(season=2024, week=1, home_team_id=3, away_team_id=4),
    ]
    
    for game in games:
        session.add(game)
    
    session.commit()
    
    # Recompute SOS
    recompute_sos(session, 2024)
    
    # Check SOS was updated
    updated_teams = list(session.exec(select(Standings).where(Standings.season == 2024)))
    for team in updated_teams:
        assert team.sos is not None

def test_standings_validation(session: Session):
    """Test standings validation."""
    # Create valid standings
    standings = Standings(
        season=2024,
        team_id=1,
        wins=10,
        losses=6,
        power_rating=1500.0
    )
    session.add(standings)
    session.commit()
    
    # Validate
    validation = validate_standings(session, 2024)
    assert validation["season"] == 2024
    assert "valid" in validation
    assert "issues" in validation

def test_reset_and_initialize_standings(session: Session):
    """Test reset and initialize standings."""
    # Create standings
    standings = Standings(season=2024, team_id=1, power_rating=1500.0)
    session.add(standings)
    session.commit()
    
    # Reset
    success = reset_standings(session, 2024)
    assert success is True
    
    # Check standings were deleted
    remaining = list(session.exec(select(Standings).where(Standings.season == 2024)))
    assert len(remaining) == 0
    
    # Initialize
    success = initialize_standings(session, 2024, [1, 2, 3])
    assert success is True
    
    # Check standings were created
    new_standings = list(session.exec(select(Standings).where(Standings.season == 2024)))
    assert len(new_standings) == 3

def test_playoff_seed_validation(session: Session):
    """Test playoff seed validation."""
    # Create teams
    teams = []
    for i in range(8):
        team = Standings(
            season=2024,
            team_id=i+1,
            wins=10-i,
            losses=6+i,
            power_rating=1500.0 + i*10
        )
        teams.append(team)
        session.add(team)
    
    session.commit()
    
    # Validate seeds
    validation = validate_playoff_seeds(session, 2024)
    assert validation["season"] == 2024
    assert "valid" in validation
    assert "issues" in validation

def test_standings_sorting(session: Session):
    """Test standings sorting logic."""
    # Create teams with different records
    teams = [
        Standings(season=2024, team_id=1, wins=12, losses=4, power_rating=1600.0),
        Standings(season=2024, team_id=2, wins=10, losses=6, power_rating=1550.0),
        Standings(season=2024, team_id=3, wins=8, losses=8, power_rating=1500.0),
    ]
    
    for team in teams:
        session.add(team)
    
    session.commit()
    
    # Test sorting
    standings = get_standings(session, 2024)
    standings.sort(key=lambda s: (
        (s.wins + 0.5 * s.ties) / max(1, (s.wins + s.losses + s.ties)),
        s.power_rating
    ), reverse=True)
    
    assert standings[0].team_id == 1  # Best record
    assert standings[1].team_id == 2  # Second best
    assert standings[2].team_id == 3  # Worst record

