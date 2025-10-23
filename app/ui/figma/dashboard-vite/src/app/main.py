# app/main.py
from fastapi import FastAPI
from app.api.routes.awards import router as awards_router
from app.api.routes.stats import router as stats_router

app = FastAPI(title="Franchise Football API", version="v1")

app.include_router(awards_router)
app.include_router(stats_router)
