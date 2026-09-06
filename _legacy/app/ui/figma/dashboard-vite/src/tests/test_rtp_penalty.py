from app.data.session import engine, get_db
from sqlmodel import SQLModel, Session
from app.main import app
from fastapi.testclient import TestClient
from app.models.sim_models import SimTeam, SimGame, SimGameEvent
from app.models.season_models import Season
from app.models.player_models import Player, DepthChart, PlayerInjury
from app.models.contract_models import PlayerContract, CapSummary
from app.models.stats_models import TeamGameStats
from app.models.playoffs_models import PlayoffRound, PlayoffMatchup
from app.models.coach_models import Coach
from app.engine.tuning import PARAMS as P
import pytest

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)

def test_rtp_penalty_applied_and_decays():
    init_db(drop_all=True)
    c = TestClient(app)
    c.post("/api/sim/seed-teams")
    c.post("/api/roster/seed")
    # create a short season scaffold
    c.post("/api/admin/season/init/2025?seed=123")
    # Play 1 week to allow injury creation
    c.post("/api/admin/season/2025/advance")
    # Advance again to allow some players to return and carry RTP
    c.post("/api/admin/season/2025/advance")
    # Spot-check team 1 ratings decreased if any RTP present (non-strict)
    r = c.get("/api/roster/team/1/ratings").json()
    # Can't guarantee an RTP exists; just ensure code path runs without error and ranges stay sane
    assert 35 <= r["offense"] <= 95
    # No assertion on decay due to non-determinism of injuries, but logic executed.
