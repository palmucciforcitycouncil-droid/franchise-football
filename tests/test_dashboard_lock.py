import os
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from app.ui.api import app

client = TestClient(app)
def soup(txt): return BeautifulSoup(txt, "html.parser")

def test_lock_css_order_and_exists():
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    main_idx = html.find("/static/css/dashboard.css")
    lock_idx = html.find("/static/css/dashboard.lock.css")
    assert main_idx != -1 and lock_idx != -1 and lock_idx > main_idx
    assert os.path.exists(os.path.join("app","ui","static","css","dashboard.lock.css"))

def test_required_cards_and_areas_present():
    r = client.get("/"); s = soup(r.text)
    ids = ["standings-card","power-card","league-performers-card",
           "schedule-card","boxscore-card","pbp-card",
           "scout-card","team-performers-card"]
    for i in ids: assert s.select_one(f"#{i}") is not None
    areas = ["area-standings","area-power","area-league",
             "area-schedule","area-box","area-pbp",
             "area-scout","area-team"]
    for a in areas: assert s.select_one(f".{a}") is not None

def test_standings_locked_current_impl():
    r = client.get("/"); s = soup(r.text)
    std = s.select_one('#standings-card[data-lock="standings-v1"]')
    assert std is not None, "Standings lock marker missing"
    assert s.select_one("#standings-card .std-table") is not None
    # hook present so CSS can hide the long name (we keep abbr-only)
    assert "std-name" in r.text

def test_schedule_locked_current_impl():
    r = client.get("/"); s = soup(r.text)
    sch = s.select_one('#schedule-card[data-lock="schedule-v1"]')
    assert sch is not None, "Schedule lock marker missing"
    assert s.select_one("#schedule-card #schedule-scroll") is not None
    assert s.select_one("#schedule-card #sched-list") is not None

def test_boxscore_shell_exists():
    r = client.get("/"); s = soup(r.text)
    assert s.select_one("#boxscore-card .qtable")
    assert s.select_one("#boxscore-card #cmp-list")
    assert s.select_one("#boxscore-card #leaders")