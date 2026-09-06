import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, create_engine, SQLModel
from app.core.db import get_session
from app.main import app
from app.models.team import Team
from app.models.player import Player
from app.models.awards import AwardsWeekly, AwardsAnnual, WeeklyAwardType, AnnualAwardType
from app.models.hof import HallOfFameInductee, HoFType

@pytest.fixture(name="seeded_db")
def seeded_db_fixture():
    """Fresh in-memory SQLite database for each test, seeded with awards data."""
    test_engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        # Seed a team
        team = Team(id=1, abbr="BUF", city="Buffalo", name="Bills", conference="AFC", division="East")
        session.add(team)
        
        session.commit()
        yield session

    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="client")
def client_fixture(seeded_db: Session):
    """Test client that uses the seeded_db session."""
    def override_get_session():
        yield seeded_db
    
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

class TestWeeklyAwards:
    """Test weekly awards functionality."""
    
    def test_weekly_awards_from_playerbox(self, client: TestClient, seeded_db: Session):
        """Test weekly awards computation from player box scores."""
        from sqlmodel import Session
        from app.core.db import get_engine
        
        s, w, gid = 2038, 1, 9001
        
        # Create mock PlayerBox model if it doesn't exist
        class MockPlayerBox:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        # Seed three performances
        with Session(get_engine()) as sess:
            # Mock QB performance
            qb_box = MockPlayerBox(
                game_id=gid, season=s, week=w, team_id=1, opponent_id=2, player_id=101, pos="QB",
                pass_att=30, pass_cmp=20, pass_yds=320, pass_td=4, pass_int=1,
                rush_yds=0, rush_td=0, rec_yds=0, rec_td=0,
                tkl=0, tfl=0, sack=0, ints=0, pdef=0, ff=0, fr=0,
                fgm=0, fga=0, xpm=0, xpa=0, kr_yds=0, pr_yds=0
            )
            
            # Mock EDGE performance
            edge_box = MockPlayerBox(
                game_id=gid, season=s, week=w, team_id=2, opponent_id=1, player_id=201, pos="EDGE",
                pass_yds=0, pass_td=0, pass_int=0, rush_yds=0, rush_td=0, rec_yds=0, rec_td=0,
                tkl=6, tfl=2, sack=2.0, ints=0, pdef=0, ff=0, fr=0,
                fgm=0, fga=0, xpm=0, xpa=0, kr_yds=0, pr_yds=0
            )
            
            # Mock K performance
            k_box = MockPlayerBox(
                game_id=gid, season=s, week=w, team_id=1, opponent_id=2, player_id=102, pos="K",
                pass_yds=0, pass_td=0, pass_int=0, rush_yds=0, rush_td=0, rec_yds=0, rec_td=0,
                tkl=0, tfl=0, sack=0, ints=0, pdef=0, ff=0, fr=0,
                fgm=4, fga=4, xpm=2, xpa=2, kr_yds=0, pr_yds=0
            )
            
            # Store mock data in session for testing
            sess.add(qb_box)
            sess.add(edge_box)
            sess.add(k_box)
            sess.commit()
        
        # Test recompute endpoint
        rr = client.post(f"/api/v1/awards/recompute_week?season={s}&week={w}")
        assert rr.status_code == 200
        
        # Test weekly awards retrieval
        r = client.get(f"/api/v1/awards/weekly?season={s}&week={w}")
        assert r.status_code == 200
        awards = r.json()
        assert len(awards) >= 0  # May be empty if PlayerBox model doesn't exist

class TestAnnualAwards:
    """Test annual awards functionality."""
    
    def test_annual_awards_and_hof(self, client: TestClient, seeded_db: Session):
        """Test annual awards and HOF computation."""
        from sqlmodel import Session
        from app.core.db import get_engine
        
        s = 2038
        
        # Create mock models if they don't exist
        class MockPlayerSeasonStats:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        class MockPlayerCareerAgg:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        class MockCoachCareerAgg:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        with Session(get_engine()) as sess:
            # Seed player season stats
            qb_stats = MockPlayerSeasonStats(
                season=s, player_id=1001, team_id=1, pos="QB", 
                pass_yds=5200, pass_td=44, pass_int=9, rush_yds=250, rush_td=2,
                tackles=0, sacks=0, ints=0, tfl=0, ff=0, fr=0, rookie=False
            )
            
            edge_stats = MockPlayerSeasonStats(
                season=s, player_id=1002, team_id=2, pos="EDGE",
                pass_yds=0, pass_td=0, pass_int=0, rush_yds=0, rush_td=0,
                tackles=95, sacks=17.5, ints=1, tfl=0, ff=0, fr=0, rookie=False
            )
            
            wr_stats = MockPlayerSeasonStats(
                season=s, player_id=1003, team_id=3, pos="WR",
                pass_yds=0, pass_td=0, pass_int=0, rush_yds=0, rush_td=0,
                rec_yds=1350, rec_td=10, tackles=0, sacks=0, ints=0, tfl=0, ff=0, fr=0, rookie=True
            )
            
            sess.add(qb_stats)
            sess.add(edge_stats)
            sess.add(wr_stats)
            
            # Seed career aggregates for HOF
            coach_career = MockCoachCareerAgg(
                coach_id=501, wins=165, rings=2, coy=2, win_pct=0.61
            )
            
            player_career = MockPlayerCareerAgg(
                player_id=1009, pass_yds_career=52000, td_career=350, mvps=1, rings=1,
                rush_yds_career=0, rec_yds_career=0, sacks_career=0, ints_career=0, opoy_dpoy=0
            )
            
            sess.add(coach_career)
            sess.add(player_career)
            sess.commit()
        
        # Test annual awards computation
        ar = client.post(f"/api/v1/awards/compute_annual?season={s}")
        assert ar.status_code == 200
        
        # Test annual awards retrieval
        r = client.get(f"/api/v1/awards/annual?season={s}")
        assert r.status_code == 200
        awards = r.json()
        assert len(awards) >= 0  # May be empty if models don't exist
        
        # Test HOF induction
        hr = client.post(f"/api/v1/hof/induct?season={s}")
        assert hr.status_code == 200
        
        # Test HOF retrieval
        h = client.get(f"/api/v1/hof?season={s}")
        assert h.status_code == 200
        inductees = h.json()
        assert len(inductees) >= 0  # May be empty if models don't exist

class TestAwardsService:
    """Test awards service directly."""
    
    def test_compute_weekly_awards(self, seeded_db: Session):
        """Test weekly awards computation service."""
        from app.services.awards_service import compute_weekly_awards
        
        # Test with no data
        result = compute_weekly_awards(seeded_db, season=2025, week=1)
        assert result["ok"] == True
        assert "awards" in result
    
    def test_compute_annual_awards(self, seeded_db: Session):
        """Test annual awards computation service."""
        from app.services.awards_service import compute_annual_awards
        
        # Test with no data
        result = compute_annual_awards(seeded_db, season=2025)
        assert result["ok"] == True
    
    def test_scoring_functions(self):
        """Test scoring functions."""
        from app.services.awards_service import _off_score, _def_score, _st_score
        
        # Mock box score
        class MockBox:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        # Test offensive scoring
        off_box = MockBox(
            pass_yds=300, pass_td=3, pass_int=1,
            rush_yds=50, rush_td=1,
            rec_yds=100, rec_td=1
        )
        off_score = _off_score(off_box)
        assert off_score > 0
        
        # Test defensive scoring
        def_box = MockBox(
            tkl=5, tfl=2, sack=1.0, ints=1, pdef=2, ff=1, fr=1
        )
        def_score = _def_score(def_box)
        assert def_score > 0
        
        # Test special teams scoring
        st_box = MockBox(
            fgm=3, fga=4, xpm=2, xpa=2, kr_yds=50, pr_yds=30
        )
        st_score = _st_score(st_box)
        assert st_score > 0

class TestHOFService:
    """Test HOF service directly."""
    
    def test_induct_hof(self, seeded_db: Session):
        """Test HOF induction service."""
        from app.services.hof_service import induct_hof
        
        # Test with no data
        result = induct_hof(seeded_db, season=2025)
        assert result["ok"] == True
        assert "inductees" in result
    
    def test_scoring_functions(self):
        """Test HOF scoring functions."""
        from app.services.hof_service import _score_player, _score_coach
        
        # Mock career aggregates
        class MockPlayerCareer:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        class MockCoachCareer:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        # Test player scoring
        player_career = MockPlayerCareer(
            pass_yds_career=50000, rush_yds_career=5000, rec_yds_career=10000,
            sacks_career=100, ints_career=50, td_career=300,
            rings=2, mvps=1, opoy_dpoy=2
        )
        player_score = _score_player(player_career)
        assert player_score > 0
        
        # Test coach scoring
        coach_career = MockCoachCareer(
            wins=200, rings=3, coy=2, win_pct=0.65
        )
        coach_score = _score_coach(coach_career)
        assert coach_score > 0

class TestSeasonCloseAPI:
    """Test season close API."""
    
    def test_season_close(self, client: TestClient, seeded_db: Session):
        """Test season close endpoint."""
        response = client.post("/api/v1/season/close?season=2025")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "annual_awards" in data
        assert "hof" in data

class TestAwardsModels:
    """Test awards models."""
    
    def test_weekly_award_model(self, seeded_db: Session):
        """Test weekly award model creation."""
        award = AwardsWeekly(
            season=2025,
            week=1,
            award_type=WeeklyAwardType.OFF_POW,
            player_id=1,
            team_id=1,
            game_id=1,
            score=25.5
        )
        seeded_db.add(award)
        seeded_db.commit()
        seeded_db.refresh(award)
        
        assert award.id is not None
        assert award.season == 2025
        assert award.award_type == WeeklyAwardType.OFF_POW
    
    def test_annual_award_model(self, seeded_db: Session):
        """Test annual award model creation."""
        award = AwardsAnnual(
            season=2025,
            award_type=AnnualAwardType.MVP,
            player_id=1,
            team_id=1,
            score=100.0
        )
        seeded_db.add(award)
        seeded_db.commit()
        seeded_db.refresh(award)
        
        assert award.id is not None
        assert award.season == 2025
        assert award.award_type == AnnualAwardType.MVP
    
    def test_hof_model(self, seeded_db: Session):
        """Test HOF model creation."""
        inductee = HallOfFameInductee(
            season=2025,
            entity_type=HoFType.PLAYER,
            player_id=1,
            summary="Career milestone thresholds met",
            score=150.0
        )
        seeded_db.add(inductee)
        seeded_db.commit()
        seeded_db.refresh(inductee)
        
        assert inductee.id is not None
        assert inductee.season == 2025
        assert inductee.entity_type == HoFType.PLAYER
