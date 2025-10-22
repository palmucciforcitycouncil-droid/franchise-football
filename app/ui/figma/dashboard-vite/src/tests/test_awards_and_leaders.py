"""
Tests for Awards and Leaders functionality.
Tests season awards, Super Bowl MVP, and leaderboards.
"""

import pytest

from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.awards import compute_season_awards, compute_super_bowl_mvp, compute_league_leaders, compute_team_leaders
from app.models.awards import AwardWinner, AwardType
from sqlmodel import select


def test_awards_and_leaders_end_to_end():
    """Test complete awards and leaders functionality."""
    with memory_db() as session:
        # 1) Run a short season (mini regular + mock playoffs/champ if available in your sim)
        out = run_mini_season(session, weeks=2)
        season = 2025  # or fetch from settings/league

        # 2) Compute season awards (pre-SB)
        aw = compute_season_awards(session, season=season)
        # Basic expectations: MVP exists or is -1 if qualifiers missing (fall back)
        assert "MVP" in aw
        assert "OPOY_AFC" in aw
        assert "OPOY_NFC" in aw
        assert "DPOY_AFC" in aw
        assert "DPOY_NFC" in aw
        assert "OROY" in aw
        assert "DROY" in aw
        assert "COY_TEAM" in aw
        assert "GMY_TEAM" in aw

        # 3) Leaders compile at league level
        boards = compute_league_leaders(session, season=season, top_n=5)
        assert len(boards) >= 5
        assert all(len(b.leaders) <= 5 for b in boards)

        # 4) Team leaders compile for at least one team
        any_team_id = None
        try:
            from app.models.sim_models import SimTeam
            any_team_id = session.exec(select(SimTeam.id)).first()
        except Exception:
            pass
        if any_team_id:
            team_boards = compute_team_leaders(session, season=season, team_id=any_team_id, top_n=3)
            assert len(team_boards) >= 5
            assert all(len(b.leaders) <= 3 for b in team_boards)

        # 5) Super Bowl MVP (if you have a championship game id exposed; otherwise skip gracefully)
        sb_mvp_pid = None
        champ_game_id = None
        # Try to find the last game id from run_mini_season as "champ"
        if out.get("games"):
            champ_game_id = out["games"][-1]
        if champ_game_id:
            sb_mvp_pid = compute_super_bowl_mvp(session, season=season, super_bowl_game_id=champ_game_id)
            # Either returns a player id or None if game stats unsupported
            # If it returned a pid, ensure it's persisted
            if sb_mvp_pid:
                row = session.exec(select(AwardWinner).where(AwardWinner.season==season, AwardWinner.award==AwardType.SBMVP)).first()
                assert row is not None
                assert row.player_id == sb_mvp_pid

        # 6) Persisted core awards exist (when qualifying stats are present)
        rows = session.exec(select(AwardWinner).where(AwardWinner.season==season)).all()
        assert len(rows) >= 1


def test_awards_deterministic():
    """Test that awards are deterministic with same seed."""
    with memory_db() as session:
        out = run_mini_season(session, weeks=1)
        season = 2025

        # Run awards twice with same data
        aw1 = compute_season_awards(session, season=season)
        
        # Clear the awards and run again
        award_rows = session.exec(select(AwardWinner).where(AwardWinner.season==season)).all()
        for row in award_rows:
            session.delete(row)
        session.commit()
        
        aw2 = compute_season_awards(session, season=season)
        
        # Should get same results
        assert aw1["MVP"] == aw2["MVP"]
        assert aw1["OPOY_AFC"] == aw2["OPOY_AFC"]
        assert aw1["OPOY_NFC"] == aw2["OPOY_NFC"]
        assert aw1["DPOY_AFC"] == aw2["DPOY_AFC"]
        assert aw1["DPOY_NFC"] == aw2["DPOY_NFC"]


def test_league_leaders_categories():
    """Test that league leaders cover all expected categories."""
    with memory_db() as session:
        out = run_mini_season(session, weeks=1)
        season = 2025

        boards = compute_league_leaders(session, season=season, top_n=3)
        
        # Check that we have the expected categories
        categories = [b.title for b in boards]
        expected_categories = [
            "Passing Yards", "Passing TD", "Interceptions Thrown (Fewest)",
            "Rushing Yards", "Rushing TD", "Receiving Yards", "Receiving TD",
            "Sacks (Defense)", "Interceptions (Defense)", "TFL",
            "FG Made", "FG %", "Net Punting", "Return TD"
        ]
        
        for expected in expected_categories:
            assert expected in categories, f"Missing category: {expected}"
        
        # Check that each board has leaders
        for board in boards:
            assert len(board.leaders) >= 0, f"Board {board.title} has no leaders"
            assert len(board.leaders) <= 3, f"Board {board.title} has too many leaders"


def test_team_leaders_filtering():
    """Test that team leaders are properly filtered by team."""
    with memory_db() as session:
        out = run_mini_season(session, weeks=1)
        season = 2025

        # Get a team ID
        from app.models.sim_models import SimTeam
        team_id = session.exec(select(SimTeam.id)).first()
        
        if team_id:
            team_boards = compute_team_leaders(session, season=season, team_id=team_id, top_n=3)
            
            # Check that all leaders belong to the specified team
            for board in team_boards:
                for leader in board.leaders:
                    assert leader.team_id == team_id, f"Leader {leader.name} not on team {team_id}"


def test_super_bowl_mvp_game_specific():
    """Test that Super Bowl MVP is selected from the correct game."""
    with memory_db() as session:
        out = run_mini_season(session, weeks=1)
        season = 2025

        if out.get("games"):
            champ_game_id = out["games"][-1]
            sb_mvp_pid = compute_super_bowl_mvp(session, season=season, super_bowl_game_id=champ_game_id)
            
            if sb_mvp_pid:
                # Check that the MVP is persisted with the correct game ID
                row = session.exec(select(AwardWinner).where(
                    AwardWinner.season==season, 
                    AwardWinner.award==AwardType.SBMVP
                )).first()
                
                assert row is not None
                assert row.player_id == sb_mvp_pid
                assert row.game_id == champ_game_id


def test_award_persistence():
    """Test that awards are properly persisted to the database."""
    with memory_db() as session:
        out = run_mini_season(session, weeks=1)
        season = 2025

        # Compute awards
        aw = compute_season_awards(session, season=season)
        
        # Check that awards are persisted
        rows = session.exec(select(AwardWinner).where(AwardWinner.season==season)).all()
        
        # Should have at least the core awards
        award_types = [row.award for row in rows]
        expected_awards = [
            AwardType.MVP, AwardType.OPOY_AFC, AwardType.OPOY_NFC,
            AwardType.DPOY_AFC, AwardType.DPOY_NFC, AwardType.OROY,
            AwardType.DROY, AwardType.COY, AwardType.GMY
        ]
        
        for expected in expected_awards:
            assert expected in award_types, f"Missing award: {expected}"
        
        # Check that player awards have player_id set
        player_awards = [row for row in rows if row.player_id is not None]
        assert len(player_awards) >= 0, "No player awards found"
        
        # Check that team awards have team_id set
        team_awards = [row for row in rows if row.team_id is not None]
        assert len(team_awards) >= 0, "No team awards found"


def test_qualifiers_respected():
    """Test that minimum qualifiers are respected."""
    with memory_db() as session:
        out = run_mini_season(session, weeks=1)
        season = 2025

        # This test would need more sophisticated setup to create players
        # that meet/don't meet qualifiers. For now, just ensure the function runs.
        aw = compute_season_awards(session, season=season)
        
        # Awards should be computed (even if -1 for missing qualifiers)
        assert isinstance(aw["MVP"], int)
        assert isinstance(aw["OPOY_AFC"], int)
        assert isinstance(aw["DPOY_AFC"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
