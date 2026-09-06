from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import BACKEND_BASE_URL

# Routers
from app.routers import diag
from app.routers import sim           # <- hard include
from app.routers import stats         # Stats API
from app.ui import routes as ui_routes
from app.ui.api_schedule_results import router as schedule_results_router
from app.api.draft import router as new_draft_router  # New import
from app.ui.api_season import router as season_router, feed_router as feed_api_router

app = FastAPI(
    title="Franchise Football API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8015",
        "http://localhost:8015",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers (no try/except so failures show up loudly)
app.include_router(diag.router)
app.include_router(sim.router, prefix="")          # /api/sim/...
app.include_router(stats.router, prefix="")       # /api/stats/...
app.include_router(ui_routes.router, prefix="")    # /ui
app.include_router(schedule_results_router)        # /api/v1/schedule/... and /api/v1/results/...
app.include_router(new_draft_router)               # /api/v1/draft/...
app.include_router(season_router)                  # /api/v1/season/...
app.include_router(feed_api_router)                # /api/v1/feed

@app.get("/")
def root():
    return {"ok": True, "service": "franchise-football", "docs": "/docs"}
