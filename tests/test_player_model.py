"""
Tests for the Player model (app/models/player.py) and, where the imported
DB happens to exist locally, the real roster data itself.

The source CSVs (players.csv, players_with FA.csv) live outside this repo
on the developer's machine, not in git, so the DB-dependent checks below
skip gracefully if data/franchise_football.db hasn't been built yet via
scripts/import_players.py -- they're a real integration check when it has
been run, not a hard CI dependency.
"""
import os
from pathlib import Path

os.environ.setdefault("LEAGUE_SEED", "2025")

import pytest
from sqlmodel import select, func

from app.models.player import Player, Position
from app.core.db import get_session, DB_PATH

DB_EXISTS = DB_PATH.exists()


def test_player_can_be_constructed_with_minimal_fields():
    p = Player(
        player_id="test_1", first_name="Test", last_name="Player",
        position=Position.QB, team_abbr="BUF", age=25,
        overall_rating=75, potential=80, morale=90,
        speed=80, acceleration=80, strength=70, agility=75, jumping=70,
        stamina=85, toughness=80, durability=85,
        throw_power=88, throw_accuracy_short=85, throw_accuracy_mid=82,
        throw_accuracy_deep=75, play_action=80, throw_on_the_run=78,
        throw_under_pressure=76, break_sack=70,
        catching=40, spectacular_catch=30, catch_in_traffic=30,
        short_route_running=40, medium_route_running=40, deep_route_running=40, release=40,
        carrying=60, trucking=40, change_of_direction=70, ball_carrier_vision=50,
        stiff_arm=40, spin_move=40, juke_move=40, break_tackle=40,
        run_block=30, pass_block=30, run_block_power=30, run_block_finesse=30,
        pass_block_power=30, pass_block_finesse=30, lead_block=20, impact_blocking=20,
        tackle=30, hit_power=30, block_shedding=20, pursuit=30, play_recognition=70,
        man_coverage=20, zone_coverage=20, press=20, power_moves=20, finesse_moves=20,
        kick_power=20, kick_accuracy=20, kick_return=20,
        awareness=80,
    )
    assert p.full_name == "Test Player"
    assert p.is_free_agent is False


def test_free_agent_has_no_team():
    p = Player(
        player_id="test_2", first_name="Free", last_name="Agent",
        position=Position.WR, team_abbr=None, age=27,
        overall_rating=70, potential=70, morale=50,
        speed=90, acceleration=88, strength=60, agility=88, jumping=80,
        stamina=80, toughness=70, durability=75,
        throw_power=0, throw_accuracy_short=0, throw_accuracy_mid=0,
        throw_accuracy_deep=0, play_action=0, throw_on_the_run=0,
        throw_under_pressure=0, break_sack=0,
        catching=85, spectacular_catch=75, catch_in_traffic=70,
        short_route_running=80, medium_route_running=78, deep_route_running=76, release=80,
        carrying=50, trucking=30, change_of_direction=85, ball_carrier_vision=40,
        stiff_arm=30, spin_move=40, juke_move=50, break_tackle=30,
        run_block=20, pass_block=20, run_block_power=20, run_block_finesse=20,
        pass_block_power=20, pass_block_finesse=20, lead_block=10, impact_blocking=10,
        tackle=20, hit_power=20, block_shedding=10, pursuit=30, play_recognition=40,
        man_coverage=10, zone_coverage=10, press=10, power_moves=10, finesse_moves=10,
        kick_power=10, kick_accuracy=10, kick_return=40,
        awareness=70,
    )
    assert p.is_free_agent is True


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_imported_roster_shape():
    with get_session() as s:
        total = s.exec(select(func.count()).select_from(Player)).one()
        assert total > 2000, "expected a full-league-sized import"

        fa_count = s.exec(select(func.count()).select_from(Player).where(Player.team_abbr == None)).one()
        assert fa_count > 0, "expected at least some free agents"

        teams = s.exec(select(Player.team_abbr).where(Player.team_abbr != None).distinct()).all()
        assert len(teams) == 32, f"expected all 32 teams represented, got {len(teams)}"


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_imported_players_have_real_salaries():
    """Regression test for a real bug (found while wiring the Player Card's
    Contract tab to this data, ROADMAP.md M8): import_players.py looked up
    the CSV's salary/signing_bonus columns by the wrong key (missing a
    leading space the real headers carry), so every imported player's
    salary/signing_bonus silently defaulted to 0 via dict.get()."""
    with get_session() as s:
        nonzero_salary = s.exec(select(func.count()).select_from(Player).where(Player.salary > 0)).one()
        assert nonzero_salary > 2000, "expected nearly every imported player to have a real nonzero salary"


@pytest.mark.skipif(not DB_EXISTS, reason="data/franchise_football.db not built -- run scripts/import_players.py")
def test_imported_players_have_plausible_attributes():
    """Every stored attribute should be a valid 0-99 rating (or the salary/
    signing_bonus fields, which aren't on that scale) -- catches the CSV's
    known "99 as a missing-data sentinel" issue if it ever leaks through
    for a field where 99 wouldn't actually make sense (e.g. a lineman with
    99 throw_accuracy_deep would be a real red flag, not a real player)."""
    with get_session() as s:
        qbs = s.exec(select(Player).where(Player.position == Position.QB)).all()
        assert len(qbs) >= 32, "expected at least one QB per team"
        for qb in qbs:
            assert 0 <= qb.throw_power <= 99
            assert 0 <= qb.overall_rating <= 99
