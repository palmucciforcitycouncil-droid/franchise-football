# tests/test_draft_compare.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db import get_engine
from app.services.draft import generate_draft_class, assign_picks
from app.models.draft import Prospect
from app.services.draft_compare import compare_prospects, board_score

client = TestClient(app)

def test_board_score_calculation():
    """Test board score calculation."""
    from app.models.draft import Prospect
    
    # Create a test prospect
    prospect = Prospect(
        name="Test QB",
        pos="QB",
        season=2025,
        overall=85,
        potential=90,
        speed=80,
        agility=75,
        strength=70,
        awareness=88
    )
    
    score = board_score(prospect)
    assert isinstance(score, float)
    assert score > 0
    # Score should be weighted toward overall and potential
    assert 80 <= score <= 90

def test_compare_prospects_service():
    """Test the compare_prospects service function."""
    season = 2034
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=1234)
        assign_picks(s, season)
        
        # Get some WR prospects
        wrs = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="WR").order_by(Prospect.overall.desc())).all()
        assert len(wrs) >= 3
        
        ids = [wrs[0].id, wrs[1].id, wrs[2].id]
        
        # Test the service function
        result = compare_prospects(s, season, ids)
        
        # Check structure
        assert "season" in result
        assert "count" in result
        assert "items" in result
        assert "diff" in result
        
        assert result["season"] == season
        assert result["count"] == 3
        assert len(result["items"]) == 3
        
        # Check items structure
        for item in result["items"]:
            assert "id" in item
            assert "name" in item
            assert "pos" in item
            assert "metrics" in item
            assert "board_score" in item
            assert "percentiles_pos" in item
            
            # Check metrics
            metrics = item["metrics"]
            for field in ["overall", "potential", "speed", "agility", "strength", "awareness"]:
                assert field in metrics
            
            # Check percentiles
            percentiles = item["percentiles_pos"]
            for field in ["overall", "potential", "speed", "agility", "strength", "awareness", "board_score"]:
                assert field in percentiles
                assert 0 <= percentiles[field] <= 100
        
        # Check diff structure
        diff = result["diff"]
        assert "baseline_id" in diff
        assert "rows" in diff
        assert len(diff["rows"]) == 2  # 3 prospects - 1 baseline = 2 comparisons
        
        for row in diff["rows"]:
            assert "id" in row
            assert "name" in row
            assert "pos" in row
            assert "deltas" in row
            
            # Check deltas
            deltas = row["deltas"]
            for field in ["overall", "potential", "speed", "agility", "strength", "awareness", "board_score"]:
                assert field in deltas
                assert isinstance(deltas[field], (int, float))

def test_compare_endpoint():
    """Test the compare API endpoint."""
    season = 2035
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=1234)
        assign_picks(s, season)
        wrs = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="WR").order_by(Prospect.overall.desc())).all()
        assert len(wrs) >= 3
        ids = [wrs[0].id, wrs[1].id, wrs[2].id]
    
    # Test valid request
    r = client.get(f"/draft/{season}/board/compare?ids={','.join(map(str, ids))}")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 3
    assert "items" in data and "diff" in data
    
    # Check percentiles exist
    p0 = data["items"][0]["percentiles_pos"]
    assert "board_score" in p0 and "overall" in p0
    
    # Test with different positions
    qbs = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="QB").order_by(Prospect.overall.desc())).all()
    if len(qbs) >= 2:
        qb_ids = [qbs[0].id, qbs[1].id]
        r = client.get(f"/draft/{season}/board/compare?ids={','.join(map(str, qb_ids))}")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 2

def test_compare_endpoint_validation():
    """Test endpoint validation and error handling."""
    season = 2036
    
    # Test invalid IDs format
    r = client.get(f"/draft/{season}/board/compare?ids=invalid")
    assert r.status_code == 422
    
    # Test too few IDs
    r = client.get(f"/draft/{season}/board/compare?ids=1")
    assert r.status_code == 400
    
    # Test empty IDs
    r = client.get(f"/draft/{season}/board/compare?ids=")
    assert r.status_code == 400
    
    # Test non-existent IDs
    r = client.get(f"/draft/{season}/board/compare?ids=99999,99998")
    assert r.status_code == 404

def test_percentile_calculation():
    """Test percentile rank calculation."""
    from app.services.draft_compare import _pct_rank
    
    # Test basic percentile calculation
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    
    # Test values at different percentiles
    assert _pct_rank(10, values) == 5.0  # Lowest value
    assert _pct_rank(100, values) == 95.0  # Highest value
    assert _pct_rank(50, values) == 50.0  # Median
    
    # Test with ties
    values_with_ties = [10, 20, 20, 30, 40]
    assert _pct_rank(20, values_with_ties) == 30.0  # Average rank for ties
    
    # Test empty list
    assert _pct_rank(50, []) == 0.0
    
    # Test single value
    assert _pct_rank(50, [50]) == 50.0

def test_positional_buckets():
    """Test positional bucket collection."""
    from app.services.draft_compare import _collect_pos_bucket
    
    season = 2037
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=1234)
        
        # Test collecting QB bucket
        bucket = _collect_pos_bucket(s, season, "QB")
        
        assert isinstance(bucket, dict)
        assert "board_score" in bucket
        
        # Check that all core fields are present
        for field in ["overall", "potential", "speed", "agility", "strength", "awareness"]:
            assert field in bucket
            assert isinstance(bucket[field], list)
        
        # Check board_score is calculated
        assert isinstance(bucket["board_score"], list)
        assert len(bucket["board_score"]) > 0
        
        # All values should be numeric
        for field_values in bucket.values():
            for value in field_values:
                assert isinstance(value, (int, float))

def test_mixed_position_comparison():
    """Test comparing prospects from different positions."""
    season = 2038
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=1234)
        
        # Get one QB and one WR
        qb = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="QB").order_by(Prospect.overall.desc())).first()
        wr = s.exec(select(Prospect).where(Prospect.season==season, Prospect.pos=="WR").order_by(Prospect.overall.desc())).first()
        
        if qb and wr:
            ids = [qb.id, wr.id]
            
            result = compare_prospects(s, season, ids)
            
            assert result["count"] == 2
            assert len(result["items"]) == 2
            
            # Check that percentiles are calculated within each position
            qb_item = next(item for item in result["items"] if item["pos"] == "QB")
            wr_item = next(item for item in result["items"] if item["pos"] == "WR")
            
            # Both should have percentiles calculated
            assert "percentiles_pos" in qb_item
            assert "percentiles_pos" in wr_item
            
            # Percentiles should be calculated within their respective positions
            for field in ["overall", "potential", "speed", "agility", "strength", "awareness", "board_score"]:
                assert field in qb_item["percentiles_pos"]
                assert field in wr_item["percentiles_pos"]

def test_board_score_consistency():
    """Test that board scores are consistent and reasonable."""
    season = 2039
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=1234)
        
        prospects = s.exec(select(Prospect).where(Prospect.season == season)).all()
        
        scores = []
        for prospect in prospects[:10]:  # Test first 10
            score = board_score(prospect)
            scores.append(score)
            
            # Score should be reasonable
            assert 0 <= score <= 100
            assert isinstance(score, float)
        
        # Higher overall should generally have higher board score
        sorted_prospects = sorted(prospects[:10], key=lambda p: p.overall, reverse=True)
        sorted_scores = [board_score(p) for p in sorted_prospects]
        
        # Check that scores generally follow overall rating
        for i in range(len(sorted_scores) - 1):
            # Allow some flexibility due to weighting
            if sorted_prospects[i].overall - sorted_prospects[i+1].overall > 5:
                assert sorted_scores[i] >= sorted_scores[i+1] - 2  # Allow small variance

def test_api_response_structure():
    """Test that API response has the expected structure for UI consumption."""
    season = 2040
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=1234)
        prospects = s.exec(select(Prospect).where(Prospect.season == season)).all()
        
        if len(prospects) >= 3:
            ids = [prospects[0].id, prospects[1].id, prospects[2].id]
            
            r = client.get(f"/draft/{season}/board/compare?ids={','.join(map(str, ids))}")
            assert r.status_code == 200
            data = r.json()
            
            # Check top-level structure
            required_fields = ["season", "count", "items", "diff"]
            for field in required_fields:
                assert field in data
            
            # Check items structure
            for item in data["items"]:
                required_item_fields = ["id", "name", "pos", "season", "metrics", "board_score", "percentiles_pos"]
                for field in required_item_fields:
                    assert field in item
                
                # Check metrics structure
                metrics = item["metrics"]
                for field in ["overall", "potential", "speed", "agility", "strength", "awareness"]:
                    assert field in metrics
                    assert isinstance(metrics[field], (int, float, type(None)))
                
                # Check percentiles structure
                percentiles = item["percentiles_pos"]
                for field in ["overall", "potential", "speed", "agility", "strength", "awareness", "board_score"]:
                    assert field in percentiles
                    assert isinstance(percentiles[field], (int, float))
                    assert 0 <= percentiles[field] <= 100
            
            # Check diff structure
            diff = data["diff"]
            assert "baseline_id" in diff
            assert "rows" in diff
            assert isinstance(diff["rows"], list)
            
            for row in diff["rows"]:
                assert "id" in row
                assert "name" in row
                assert "pos" in row
                assert "deltas" in row
                
                deltas = row["deltas"]
                for field in ["overall", "potential", "speed", "agility", "strength", "awareness", "board_score"]:
                    assert field in deltas
                    assert isinstance(deltas[field], (int, float))
