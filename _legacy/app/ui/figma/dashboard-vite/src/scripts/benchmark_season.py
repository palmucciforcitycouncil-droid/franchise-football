import time
from sqlmodel import Session
from app.data.session import get_db, engine
from app.data.session import engine
from sqlmodel import SQLModel
from app.main import app
from fastapi.testclient import TestClient

def init_db(drop_all=False):
    if drop_all:
        SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)

def main():
    init_db(drop_all=True)
    c = TestClient(app)
    c.post("/api/sim/seed-teams")
    c.post("/api/roster/seed")
    c.post("/api/admin/season/init/2025?seed=123")
    t0 = time.time()
    for _ in range(16):
        c.post("/api/admin/season/2025/advance")
    t1 = time.time()
    print(f"Simulated 16 weeks in {t1-t0:.2f}s")
    # Playoffs
    c.post("/api/playoffs/build/2025")
    c.post("/api/playoffs/run/2025?seed=999")
    t2 = time.time()
    print(f"Playoffs in {t2-t1:.2f}s")
    print(f"Total: {t2-t0:.2f}s")

if __name__ == "__main__":
    main()
