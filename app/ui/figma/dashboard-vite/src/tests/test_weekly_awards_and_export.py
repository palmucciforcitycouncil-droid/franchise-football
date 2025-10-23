"""
Tests for Weekly Awards and Season Export.
"""

import os
import json
import pytest
from pathlib import Path
from sqlmodel import Session, create_engine, select

from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.weekly_awards import compute_weekly_awards
from app.models.weekly_awards import WeeklyAward, WeeklyAwardType
from app.services.season_export import export_season_summary


def test_weekly_awards_and_export_end_to_end(tmp_path: Path):
    """Test weekly awards and season export end-to-end."""
    with memory_db() as session:
        out = run_mini_season(session, weeks=2)
        season = 2025

        winners = compute_weekly_awards(session, season)
        # Expect at least some weeks produce awards (if stats available)
        # Not strict on count because minimal sim can be sparse
        assert winners is not None

        # Verify persisted rows, if any
        rows = session.exec(select(WeeklyAward).where(WeeklyAward.season == season)).all()
        # If we had any winners, they should be in DB
        if winners:
            assert len(rows) >= len(winners)

        # Export should not crash and should create JSON file
        out_json = tmp_path / "season_summary.json"
        payload = export_season_summary(session, season, out_json=str(out_json))
        assert out_json.exists()
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data.get("season") == season
        assert "leaders" in data
        assert "awards" in data


def test_weekly_awards_scoring():
    """Test that weekly award scoring functions work correctly."""
    from app.services.weekly_awards import _score_off, _score_def, _score_st
    
    # Mock row objects for testing
    class MockRow:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    # Test offensive scoring
    off_row = MockRow(
        rush_td=1, pass_td=2, rec_td=1,
        rush_yards=50, pass_yards=200, rec_yards=75,
        epa_total=5.0
    )
    off_score = _score_off(off_row)
    assert off_score > 0
    
    # Test defensive scoring
    def_row = MockRow(
        sacks=2, ints=1, tfl=3, pbu=2,
        epa_def_total=-2.0
    )
    def_score = _score_def(def_row)
    assert def_score > 0
    
    # Test special teams scoring
    st_row = MockRow(
        fgm=3, fga=4, punts=5, net_punt=40.0, ret_td=1
    )
    st_score = _score_st(st_row)
    assert st_score > 0


def test_season_export_structure():
    """Test that season export produces correct structure."""
    with memory_db() as session:
        out = run_mini_season(session, weeks=1)
        season = 2025
        
        payload = export_season_summary(session, season)
        
        # Check required keys
        assert "season" in payload
        assert "standings" in payload
        assert "awards" in payload
        assert "awards_persisted" in payload
        assert "weekly_awards" in payload
        assert "leaders" in payload
        
        # Check season matches
        assert payload["season"] == season
        
        # Check types
        assert isinstance(payload["standings"], list)
        assert isinstance(payload["awards"], dict)
        assert isinstance(payload["awards_persisted"], list)
        assert isinstance(payload["weekly_awards"], list)
        assert isinstance(payload["leaders"], list)


def test_weekly_awards_deterministic():
    """Test that weekly awards are deterministic."""
    with memory_db() as session:
        out = run_mini_season(session, weeks=2, seed=2025)
        season = 2025
        
        # Run twice with same seed
        winners1 = compute_weekly_awards(session, season)
        
        # Clear and run again
        existing = session.exec(select(WeeklyAward).where(WeeklyAward.season == season)).all()
        for row in existing:
            session.delete(row)
        session.commit()
        
        winners2 = compute_weekly_awards(session, season)
        
        # Should produce same results
        assert len(winners1) == len(winners2)
        
        # Check that awards are the same
        for w1, w2 in zip(winners1, winners2):
            assert w1.season == w2.season
            assert w1.week == w2.week
            assert w1.award == w2.award
            assert w1.player_id == w2.player_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
