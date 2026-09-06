from app.db import init_db
from app.main import app
from fastapi.testclient import TestClient

GOLDEN_KEYS = {"rounds","in_the_hunt"}

def test_bracket_dto_golden_shape_and_counts():
    init_db(drop_all=True)
    c = TestClient(app)
    c.post("/api/sim/seed-teams")
    c.post("/api/roster/seed")
    c.post("/api/admin/season/init/2025?seed=123")
    # play enough weeks to produce standings signal
    for _ in range(8):
        c.post("/api/admin/season/2025/advance")
    c.post("/api/playoffs/build/2025")
    dto = c.get("/api/playoffs/bracket/2025").json()
    assert set(dto.keys()) == GOLDEN_KEYS
    # ensure presence of three AFC/NFC rounds + SB
    names = [r["round_name"] for r in dto["rounds"]]
    assert names.count("WC") == 2 and names.count("DIV") == 2 and names.count("CONF") == 2 and "SB" in names

