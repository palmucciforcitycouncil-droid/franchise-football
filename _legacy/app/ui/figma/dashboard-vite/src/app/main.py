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
from app.ui.api_gameplan import router as gameplan_router
from app.ui.api_debug_gameplan import router as debug_gp_router
from app.ui.api_gameplan_tools import router as gameplan_tools_router
from app.ui.api_coach_market import router as coach_market_router
from app.ui.api_save import router as save_router
from app.ui.api_trades import router as trades_router
from app.ui.api_injuries import router as injuries_router
from app.ui.api_expiring import router as expiring_router
from app.ui.api_standings import router as standings_router
from app.ui.api_players_fa import router as players_fa_router
from app.ui.api_roster_depth import router as roster_depth_router
from app.ui.api_cards import router as cards_router
from app.ui.api_schedule_results import router as schedule_results_router
from app.api.draft import router as new_draft_router
from app.ui.api_draft import router as draft_mvp_router
from app.ui.api_draft_admin import router as draft_admin_router
from app.ui.routers.gm import router as gm_router
from app.ui.api_cap import router as cap_router, router_roster as roster_size_router
from app.ui.api_awards_hof import router as awards_hof_router
from app.ui.api_season_close import router as season_close_router

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
app.include_router(gameplan_router)
app.include_router(debug_gp_router)
app.include_router(gameplan_tools_router)
app.include_router(coach_market_router)
app.include_router(save_router)
app.include_router(trades_router)
app.include_router(injuries_router)
app.include_router(expiring_router)
app.include_router(standings_router)
app.include_router(players_fa_router)
app.include_router(roster_depth_router)
app.include_router(cards_router)
app.include_router(schedule_results_router)
app.include_router(new_draft_router)
app.include_router(draft_mvp_router)
app.include_router(draft_admin_router)
app.include_router(gm_router)
app.include_router(cap_router)
app.include_router(roster_size_router)
app.include_router(awards_hof_router)
app.include_router(season_close_router)
