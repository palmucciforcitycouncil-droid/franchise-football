# app/api/routes/ui.py
from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter(tags=["ui"])

# Set up templates
templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "templates")
templates = Jinja2Templates(directory=templates_dir)

@router.get("/gm", response_class=HTMLResponse)
async def gm_page(request: Request):
    # Mock data - in real implementation, get from database
    context = {
        "request": request,
        "user_team_id": 1,  # Get from user context
        "current_season": 2025,  # Get from league state
    }
    return templates.TemplateResponse("gm.html.j2", context)

@router.get("/draft", response_class=HTMLResponse)
async def draft_page(request: Request):
    # Mock data - in real implementation, get from database
    context = {
        "request": request,
        "user_team_id": 1,  # Get from user context
        "current_season": 2024,  # Get from league state
    }
    return templates.TemplateResponse("draft.html", context)

