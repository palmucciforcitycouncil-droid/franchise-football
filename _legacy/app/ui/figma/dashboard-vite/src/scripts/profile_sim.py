import cProfile, pstats, io
from fastapi.testclient import TestClient
from app.main import app
from app.data.session import engine
from sqlmodel import SQLModel

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)

def run():
    init_db(drop_all=True)
    c = TestClient(app)
    c.post("/api/sim/seed-teams")
    c.post("/api/roster/seed")
    c.post("/api/admin/season/init/2025?seed=123")
    for _ in range(4):  # shorter run for profile
        c.post("/api/admin/season/2025/advance")

def main():
    pr = cProfile.Profile()
    pr.enable()
    run()
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("tottime")
    ps.print_stats(25)
    print(s.getvalue())

if __name__ == "__main__":
    main()
