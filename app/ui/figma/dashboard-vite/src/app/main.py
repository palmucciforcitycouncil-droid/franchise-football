# app/main.py
from fastapi import FastAPI
from app.api.routes.awards import router as awards_router
from app.api.routes.stats import router as stats_router
from app.api.routes.progression import router as progression_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.saves import router as saves_router
from app.api.routes.records import router as records_router
from app.api.routes.draft import router as draft_router

app = FastAPI(title="Franchise Football API", version="v1")

app.include_router(awards_router)
app.include_router(stats_router)
app.include_router(progression_router)
app.include_router(dashboard_router)
app.include_router(saves_router)
app.include_router(records_router)
app.include_router(draft_router)
