import re, os
from fastapi.testclient import TestClient

try:
    # app.ui.api should expose FastAPI instance "app"
    from app.ui.api import app
except Exception as e:
    raise SystemExit("FastAPI app import failed. Ensure app.ui.api:app exists.") from e

client = TestClient(app)

def _soup(resp_text):
    # Simple HTML parsing without BeautifulSoup
    class SimpleSoup:
        def __init__(self, html):
            self.html = html
        
        def select_one(self, selector):
            # Handle nested selectors like "#standings-card .std-table"
            if ' ' in selector:
                parts = selector.split(' ')
                # For nested selectors, just check if both parts exist
                for part in parts:
                    if not self.select_one(part):
                        return None
                return True
            
            if selector.startswith('.'):
                # class selector
                class_name = selector[1:]
                pattern = f'class="[^"]*{class_name}[^"]*"'
                if re.search(pattern, self.html):
                    return True
                return None
            elif selector.startswith('#'):
                # id selector
                id_name = selector[1:]
                pattern = f'id="{id_name}"'
                if re.search(pattern, self.html):
                    return True
                return None
            else:
                # element selector
                pattern = f'<{selector}[^>]*>'
                if re.search(pattern, self.html):
                    return True
                return None
    
    return SimpleSoup(resp_text)

def test_lock_css_linked_after_main():
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    # both CSS present
    assert "/static/css/dashboard.css" in html
    assert "/static/css/dashboard.lock.css" in html
    # lock should appear AFTER main css
    main_idx = html.find("/static/css/dashboard.css")
    lock_idx = html.find("/static/css/dashboard.lock.css")
    assert main_idx != -1 and lock_idx != -1 and lock_idx > main_idx

def test_grid_areas_and_columns_present():
    r = client.get("/")
    soup = _soup(r.text)
    grid = soup.select_one(".dashboard-grid")
    assert grid is not None, "dashboard-grid container missing"
    # required area cards exist
    for _id in ["standings-card","power-card","league-perf-card",
                "schedule-card","boxscore-card","pbp-card",
                "scouting-card","team-perf-card"]:
        assert soup.select_one(f"#{_id}") is not None, f"{_id} missing"
    # area classes present on the OUTER sections
    for _cls in ["area-standings","area-power","area-league",
                 "area-schedule","area-box","area-pbp",
                 "area-scout","area-team"]:
        assert soup.select_one(f".{_cls}") is not None, f"{_cls} missing"

def test_standings_abbr_only_and_table_present():
    r = client.get("/")
    soup = _soup(r.text)
    std = soup.select_one("#standings-card")
    assert std is not None
    # abbr-only lock: we expect std-name to exist in DOM OR be omitted,
    # but if present it must be hidden via CSS class (we only check presence of class hook)
    # Also ensure table structure exists
    assert soup.select_one("#standings-card .std-table") is not None
    # class hook that CSS hides:
    assert "std-name" in r.text, "std-name hook missing; keep it so CSS can hide names safely"

def test_boxscore_shell_exists():
    r = client.get("/")
    soup = _soup(r.text)
    box = soup.select_one("#boxscore-card")
    assert box is not None
    assert soup.select_one("#boxscore-card .qtable") is not None   # quarters table
    assert soup.select_one("#boxscore-card #cmp-list") is not None  # comparison list
    assert soup.select_one("#boxscore-card #leaders") is not None   # leaders container

def test_static_lock_file_exists_on_disk():
    # resolve absolute path to static folder based on common layout
    static_root = os.path.join(os.getcwd(), "app", "ui", "static", "css")
    lock_path = os.path.join(static_root, "dashboard.lock.css")
    assert os.path.exists(lock_path), f"Missing lock css at {lock_path}"
