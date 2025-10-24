# app/main.py
from fastapi import FastAPI
from app.api.routes.awards import router as awards_router
from app.api.routes.stats import router as stats_router
from app.api.routes.progression import router as progression_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.saves import router as saves_router
from app.api.routes.records import router as records_router
from app.api.routes.draft import router as draft_router
from app.api.routes.draft_integration import router as draft_integration_router
from app.api.routes.draft_compare import router as draft_compare_router
from app.api.routes.draft_pipeline import router as draft_pipeline_router
from app.api.routes.draft_extras import router as draft_extras_router
from app.api.routes.player_career import router as player_career_router
from app.api.routes.player_tabs import router as player_tabs_router
from app.api.routes.contracts_fa import router as contracts_fa_router
from app.api.routes.cap_resign import router as cap_resign_router
from app.api.routes.contracts_api import router as contracts_api_router
from app.api.routes.ui import router as ui_router
from app.api.routes.staff_api import router as staff_api_router
from app.api.routes.coach_focus_api import router as coach_focus_api_router
from app.ui.api_stats import router as stats_api_router
from app.ui.api_hof import router as hof_api_router
from app.ui.api_awards import router as awards_api_router
from app.ui.api_stats_derived import router as stats_derived_router
from app.ui.api_gm_expiring import router as gm_expiring_router
from app.ui.api_coach_focus import router as coach_focus_router

app = FastAPI(title="Franchise Football API", version="v1")

app.include_router(awards_router)
app.include_router(stats_router)
app.include_router(progression_router)
app.include_router(dashboard_router)
app.include_router(saves_router)
app.include_router(records_router)
app.include_router(draft_router)
app.include_router(draft_integration_router)
app.include_router(draft_compare_router)
app.include_router(draft_pipeline_router)
app.include_router(draft_extras_router)
app.include_router(player_career_router)
app.include_router(player_tabs_router)
app.include_router(contracts_fa_router)
app.include_router(cap_resign_router)
app.include_router(contracts_api_router)
app.include_router(ui_router)
app.include_router(staff_api_router)
app.include_router(coach_focus_api_router)
app.include_router(stats_api_router)
app.include_router(hof_api_router)
app.include_router(awards_api_router)
app.include_router(stats_derived_router)
app.include_router(gm_expiring_router)
app.include_router(coach_focus_router)
