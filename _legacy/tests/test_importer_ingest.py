import os
import tempfile
import csv
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.services.importer.generator import make_league, write_csvs
from app.services.importer.ingest import import_roster
from app.models.database import create_db_and_tables, get_session
from app.models import Team, Player, DepthChart

def test_import_full_league_and_idempotency():
    create_db_and_tables()
    with get_session() as session:
        teams, players, depth = make_league(seed=42)
        res1 = import_roster(session, teams=teams, players=players, depth_chart=depth, upsert=True)
        # Counts should be sensible (>= 32 teams, many players)
        assert res1["created"] > 32
        # Re-run import, no duplicates
        res2 = import_roster(session, teams=teams, players=players, depth_chart=depth, upsert=True)
        assert res2["created"] == 0

        # FK integrity: sample starter exists and matches same team
        any_dc = session.scalar(select(DepthChart).limit(1))
        assert any_dc is not None
        starter = session.get(Player, any_dc.starter_player_id)
        assert starter is not None
        assert starter.team_id == any_dc.team_id

def test_bad_age_raises():
    create_db_and_tables()
    with get_session() as session:
        teams, players, depth = make_league(seed=99)
        # force a bad age
        players[0].age = 17
        try:
            import_roster(session, teams=teams, players=players, depth_chart=depth, upsert=True)
        except ValueError as e:
            assert "age" in str(e)
        else:
            raise AssertionError("Expected ValueError for age < 18")

def test_cross_team_depthchart_rejected():
    create_db_and_tables()
    with get_session() as session:
        teams, players, depth = make_league(seed=101)
        # first team key and second team key
        tk1 = f"{teams[0].location_name}|{teams[0].nickname}"
        tk2 = f"{teams[1].location_name}|{teams[1].nickname}"

        # Import teams + players first (no depth)
        res = import_roster(session, teams=teams, players=players, depth_chart=[], upsert=True)
        assert res["created"] > 0

        # Create a depth chart entry that points to jersey from another team
        # pick a jersey from team2 but attach under team1
        jersey_from_team2 = next(p.jersey for p in players if p.team_key == tk2)
        bad_depth = [d for d in depth if d.team_key == tk1][:1]
        bad_depth[0].starter_jersey = jersey_from_team2

        try:
            import_roster(session, teams=[], players=[], depth_chart=bad_depth, upsert=True)
        except ValueError as e:
            assert "starter jersey" in str(e) or "not found on team" in str(e)
        else:
            raise AssertionError("Expected ValueError for cross-team depth chart")

def test_bad_rating_raises():
    create_db_and_tables()
    with get_session() as session:
        teams, players, depth = make_league(seed=55)
        players[0].speed = 101  # invalid > 100
        try:
            import_roster(session, teams=teams, players=players, depth_chart=depth, upsert=True)
        except ValueError as e:
            assert "rating" in str(e)
        else:
            raise AssertionError("Expected ValueError for rating > 100")
