from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.ui.api_trades import router as trades_router, teams_router, season_router
import os

app = FastAPI(title="Franchise Football UI")

# Register routers
app.include_router(trades_router)
app.include_router(teams_router)
app.include_router(season_router)

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
TPL_DIR = os.path.join(BASE_DIR, "templates")

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TPL_DIR)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    # Serve the rebuilt Dashboard
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_v2(request: Request):
    return templates.TemplateResponse("dashboard_v2.html", {"request": request})

@app.get("/api/standings", response_class=JSONResponse)
async def get_standings():
    return JSONResponse([
        {"team":"New England Patriots","w":8,"l":2},
        {"team":"Buffalo Bills","w":7,"l":3},
        {"team":"Miami Dolphins","w":6,"l":4},
        {"team":"New York Jets","w":3,"l":7},
    ])

@app.get("/api/power", response_class=JSONResponse)
async def get_power_rankings():
    return JSONResponse([
        {"team":"Kansas City Chiefs","score":"1623 → +23"},
        {"team":"Buffalo Bills","score":"1598 → +12"},
        {"team":"Philadelphia Eagles","score":"1587 → +8"},
        {"team":"New England Patriots","score":"1567 → +15"},
        {"team":"Miami Dolphins","score":"1545 → -5"},
        {"team":"Dallas Cowboys","score":"1538 → +3"},
        {"team":"Cincinnati Bengals","score":"1523 → -12"},
        {"team":"San Francisco 49ers","score":"1518 → +18"},
        {"team":"Baltimore Ravens","score":"1508 → +2"},
        {"team":"Los Angeles Chargers","score":"1495 → -8"},
    ])

@app.get("/api/performers", response_class=JSONResponse)
async def get_league_performers():
    return JSONResponse([
        {"name":"Patrick Mahomes","pos":"QB","value":"108.2"},
        {"name":"Josh Allen","pos":"QB","value":"106.8"},
        {"name":"Jalen Hurts","pos":"QB","value":"105.4"},
        {"name":"Mac Jones","pos":"QB","value":"103.8"},
        {"name":"Tua Tagovailoa","pos":"QB","value":"102.6"},
        {"name":"Geno Smith","pos":"QB","value":"100.4"},
        {"name":"Kirk Cousins","pos":"QB","value":"98.7"},
        {"name":"Derek Carr","pos":"QB","value":"96.5"},
        {"name":"Russell Wilson","pos":"QB","value":"94.2"},
        {"name":"Aaron Rodgers","pos":"QB","value":"91.8"},
    ])

@app.get("/api/schedule", response_class=JSONResponse)
async def get_schedule():
    return JSONResponse([
        {"week":"Week 1","home":True,"opp":"Buffalo Bills","result":"W","line":"24—21"},
        {"week":"Week 2","home":False,"opp":"Miami Dolphins","result":"L","line":"17—28"},
        {"week":"Week 3","home":True,"opp":"New York Jets","result":"W","line":"31—14"},
        {"week":"Week 4","home":False,"opp":"Baltimore Ravens","result":"L","line":"20—27"},
        {"week":"Week 5","home":True,"opp":"Cincinnati Bengals","result":"W","line":"35—21"},
        {"week":"Week 6","home":False,"opp":"Pittsburgh Steelers","result":"W","line":"28—24"},
        {"week":"Week 7","home":True,"opp":"Cleveland Browns","result":"W","line":"31—17"},
        {"week":"Week 8","home":False,"opp":"Detroit Lions","result":"W","line":"27—20"},
        {"week":"Week 9","home":True,"opp":"Washington Commanders","result":"W","line":"24—13"},
        {"week":"Week 10","home":False,"opp":"Indianapolis Colts","result":"L","line":"21—28"},
        {"week":"Week 11","home":True,"opp":"Houston Texans","result":"W","line":"34—16"},
    ])

@app.get("/api/boxscore/last", response_class=JSONResponse)
async def get_last_boxscore():
    return JSONResponse({
        "home":{"abbr":"NE","name":"New England Patriots","quarters":[7,10,14,3],"total":34},
        "away":{"abbr":"HOU","name":"Houston Texans","quarters":[3,7,3,3],"total":16},
        "topPerformers": {
            "home": [
                {"name":"Mac Jones","line":"24/31, 287 yards, 3 TD"},
                {"name":"Rhamondre Stevenson","line":"18 att, 89 yards, 1 TD"},
                {"name":"JuJu Smith-Schuster","line":"6 rec, 98 yards, 1 TD"}
            ],
            "away": [
                {"name":"Davis Mills","line":"18/28, 156 yards, 1 TD, 1 INT"},
                {"name":"Dameon Pierce","line":"12 att, 45 yards, 0 TD"},
                {"name":"Brandin Cooks","line":"5 rec, 67 yards, 0 TD"}
            ]
        }
    })

@app.get("/api/pbp", response_class=JSONResponse)
async def get_play_by_play():
    return JSONResponse([
        {"time":"15:00","play":"Game starts with kickoff - Houston to receive"},
        {"time":"14:52","play":"Houston 1st and 10 at HOU 25"},
        {"time":"14:15","play":"Davis Mills pass complete to Brandin Cooks for 12 yards"},
        {"time":"13:38","play":"Houston 1st and 10 at HOU 37"},
        {"time":"13:02","play":"Dameon Pierce rush for 3 yards"},
        {"time":"12:45","play":"Houston 2nd and 7 at HOU 40"},
        {"time":"12:18","play":"Davis Mills pass incomplete to Nico Collins"},
        {"time":"12:12","play":"Houston 3rd and 7 at HOU 40"},
        {"time":"11:55","play":"Davis Mills pass complete to Jordan Akins for 8 yards"},
        {"time":"11:28","play":"Houston 1st and 10 at HOU 48"},
        {"time":"10:45","play":"Davis Mills pass intercepted by Jalen Mills at NE 32"},
        {"time":"10:38","play":"New England 1st and 10 at NE 32"},
        {"time":"10:15","play":"Mac Jones pass complete to Jakobi Meyers for 18 yards"},
        {"time":"9:52","play":"New England 1st and 10 at 50"},
        {"time":"9:30","play":"Rhamondre Stevenson rush for 5 yards"},
        {"time":"9:08","play":"New England 2nd and 5 at HOU 45"},
        {"time":"8:45","play":"Mac Jones pass complete to Hunter Henry for 12 yards"},
        {"time":"8:22","play":"New England 1st and 10 at HOU 33"},
        {"time":"7:58","play":"Rhamondre Stevenson rush for 8 yards"},
        {"time":"7:35","play":"New England 2nd and 2 at HOU 25"},
        {"time":"7:12","play":"Mac Jones pass complete to JuJu Smith-Schuster for 25 yards - TOUCHDOWN"},
        {"time":"7:05","play":"Nick Folk extra point is GOOD"},
    ])

@app.get("/api/scouting", response_class=JSONResponse)
async def get_scouting():
    return JSONResponse({
        "stats": [
            {"rank":"8","stat":"Points Per Game","value":"24.5"},
            {"rank":"12","stat":"Yards per Play","value":"5.8"},
            {"rank":"15","stat":"3rd Down Conversion %","value":"42.3%"},
            {"rank":"6","stat":"Red Zone TD %","value":"68.2%"},
            {"rank":"4","stat":"Turnovers Committed","value":"1.2"},
        ],
        "top": [
            {"name":"Mac Jones","pos":"QB","value":"QB Rating 103.8"},
            {"name":"Rhamondre Stevenson","pos":"RB","value":"1,122 rushing yards"},
            {"name":"JuJu Smith-Schuster","pos":"WR","value":"988 receiving yards"},
        ]
    })

@app.get("/api/team/performers", response_class=JSONResponse)
async def get_team_performers():
    return JSONResponse({
        "Passing":[
            {"name":"Mac Jones","pos":"QB","line":"24/31, 287 yards, 3 TD"},
            {"name":"Bailey Zappe","pos":"QB","line":"2/3, 15 yards, 0 TD"},
        ],
        "Rushing":[
            {"name":"Rhamondre Stevenson","pos":"RB","line":"18 att, 89 yards, 1 TD"},
            {"name":"Damien Harris","pos":"RB","line":"8 att, 34 yards, 0 TD"},
        ],
        "Receiving":[
            {"name":"JuJu Smith-Schuster","pos":"WR","line":"6 rec, 98 yards, 1 TD"},
            {"name":"Hunter Henry","pos":"TE","line":"4 rec, 67 yards, 1 TD"},
            {"name":"Jakobi Meyers","pos":"WR","line":"5 rec, 58 yards, 0 TD"},
        ]
    })

@app.get("/api/dashboard_demo", response_class=JSONResponse)
async def dashboard_demo():
    # Comprehensive dummy data for testing all dashboard modules
    return JSONResponse({
        "standings": [
            {"team":"New England Patriots","w":8,"l":2},
            {"team":"Buffalo Bills","w":7,"l":3},
            {"team":"Miami Dolphins","w":6,"l":4},
            {"team":"New York Jets","w":3,"l":7},
        ],
        "schedule": [
            {"week":"Week 1","home":True,"opp":"Buffalo Bills","result":"W","line":"24—21"},
            {"week":"Week 2","home":False,"opp":"Miami Dolphins","result":"L","line":"17—28"},
            {"week":"Week 3","home":True,"opp":"New York Jets","result":"W","line":"31—14"},
            {"week":"Week 4","home":False,"opp":"Baltimore Ravens","result":"L","line":"20—27"},
            {"week":"Week 5","home":True,"opp":"Cincinnati Bengals","result":"W","line":"35—21"},
            {"week":"Week 6","home":False,"opp":"Pittsburgh Steelers","result":"W","line":"28—24"},
            {"week":"Week 7","home":True,"opp":"Cleveland Browns","result":"W","line":"31—17"},
            {"week":"Week 8","home":False,"opp":"Detroit Lions","result":"W","line":"27—20"},
            {"week":"Week 9","home":True,"opp":"Washington Commanders","result":"W","line":"24—13"},
            {"week":"Week 10","home":False,"opp":"Indianapolis Colts","result":"L","line":"21—28"},
            {"week":"Week 11","home":True,"opp":"Houston Texans","result":"W","line":"34—16"},
        ],
        "scouting": {
            "stats": [
                {"rank":"8","stat":"Points Per Game","value":"24.5"},
                {"rank":"12","stat":"Yards per Play","value":"5.8"},
                {"rank":"15","stat":"3rd Down Conversion %","value":"42.3%"},
                {"rank":"6","stat":"Red Zone TD %","value":"68.2%"},
                {"rank":"4","stat":"Turnovers Committed","value":"1.2"},
                {"rank":"18","stat":"OL Sack Rate %","value":"6.8%"},
                {"rank":"22","stat":"Yds Before Contact/Rush","value":"2.1"},
                {"rank":"9","stat":"Time of Possession","value":"31:24"},
                {"rank":"11","stat":"Penalties per Game","value":"6.2"},
                {"rank":"7","stat":"Red Zone Defense %","value":"58.3%"},
            ],
            "top": [
                {"name":"Mac Jones","pos":"QB","value":"QB Rating 103.8"},
                {"name":"Rhamondre Stevenson","pos":"RB","value":"1,122 rushing yards"},
                {"name":"JuJu Smith-Schuster","pos":"WR","value":"988 receiving yards"},
                {"name":"Hunter Henry","pos":"TE","value":"7 touchdowns"},
                {"name":"Matthew Judon","pos":"LB","value":"12.5 sacks"},
                {"name":"Jalen Mills","pos":"CB","value":"4 interceptions"},
            ]
        },
        "power": [
            {"team":"Kansas City Chiefs","score":"1623 → +23"},
            {"team":"Buffalo Bills","score":"1598 → +12"},
            {"team":"Philadelphia Eagles","score":"1587 → +8"},
            {"team":"New England Patriots","score":"1567 → +15"},
            {"team":"Miami Dolphins","score":"1545 → -5"},
            {"team":"Dallas Cowboys","score":"1538 → +3"},
            {"team":"Cincinnati Bengals","score":"1523 → -12"},
            {"team":"San Francisco 49ers","score":"1518 → +18"},
            {"team":"Baltimore Ravens","score":"1508 → +2"},
            {"team":"Los Angeles Chargers","score":"1495 → -8"},
        ],
        "box": {
            "home":{"abbr":"NE","name":"New England Patriots","quarters":[7,10,14,3],"total":34},
            "away":{"abbr":"HOU","name":"Houston Texans","quarters":[3,7,3,3],"total":16}
        },
        "playbyplay": [
            {"time":"15:00","play":"Game starts with kickoff - Houston to receive"},
            {"time":"14:52","play":"Houston 1st and 10 at HOU 25"},
            {"time":"14:15","play":"Davis Mills pass complete to Brandin Cooks for 12 yards"},
            {"time":"13:38","play":"Houston 1st and 10 at HOU 37"},
            {"time":"13:02","play":"Dameon Pierce rush for 3 yards"},
            {"time":"12:45","play":"Houston 2nd and 7 at HOU 40"},
            {"time":"12:18","play":"Davis Mills pass incomplete to Nico Collins"},
            {"time":"12:12","play":"Houston 3rd and 7 at HOU 40"},
            {"time":"11:55","play":"Davis Mills pass complete to Jordan Akins for 8 yards"},
            {"time":"11:28","play":"Houston 1st and 10 at HOU 48"},
            {"time":"10:45","play":"Davis Mills pass intercepted by Jalen Mills at NE 32"},
            {"time":"10:38","play":"New England 1st and 10 at NE 32"},
            {"time":"10:15","play":"Mac Jones pass complete to Jakobi Meyers for 18 yards"},
            {"time":"9:52","play":"New England 1st and 10 at 50"},
            {"time":"9:30","play":"Rhamondre Stevenson rush for 5 yards"},
            {"time":"9:08","play":"New England 2nd and 5 at HOU 45"},
            {"time":"8:45","play":"Mac Jones pass complete to Hunter Henry for 12 yards"},
            {"time":"8:22","play":"New England 1st and 10 at HOU 33"},
            {"time":"7:58","play":"Rhamondre Stevenson rush for 8 yards"},
            {"time":"7:35","play":"New England 2nd and 2 at HOU 25"},
            {"time":"7:12","play":"Mac Jones pass complete to JuJu Smith-Schuster for 25 yards - TOUCHDOWN"},
            {"time":"7:05","play":"Nick Folk extra point is GOOD"},
        ],
        "teamTop": {
            "Passing":[
                {"name":"Mac Jones","pos":"QB","line":"24/31, 287 yards, 3 TD"},
                {"name":"Bailey Zappe","pos":"QB","line":"2/3, 15 yards, 0 TD"},
            ],
            "Rushing":[
                {"name":"Rhamondre Stevenson","pos":"RB","line":"18 att, 89 yards, 1 TD"},
                {"name":"Damien Harris","pos":"RB","line":"8 att, 34 yards, 0 TD"},
            ],
            "Receiving":[
                {"name":"JuJu Smith-Schuster","pos":"WR","line":"6 rec, 98 yards, 1 TD"},
                {"name":"Hunter Henry","pos":"TE","line":"4 rec, 67 yards, 1 TD"},
                {"name":"Jakobi Meyers","pos":"WR","line":"5 rec, 58 yards, 0 TD"},
            ],
            "Defense":[
                {"name":"Matthew Judon","pos":"LB","line":"2.0 sacks, 0 INT"},
                {"name":"Jalen Mills","pos":"CB","line":"0 sacks, 1 INT"},
                {"name":"Kyle Dugger","pos":"S","line":"8 tackles, 1 TFL"},
                {"name":"Josh Uche","pos":"LB","line":"1.5 sacks, 0 INT"},
            ]
        },
        "leagueTop": [
            {"name":"Patrick Mahomes","pos":"QB","id":"T231bb4f7-6537-4729-a456-87ab8e520378","value":"108.2"},
            {"name":"Josh Allen","pos":"QB","id":"Ta3420f4b-0c95-45a0-bafb-5a0b60d454b1","value":"106.8"},
            {"name":"Jalen Hurts","pos":"QB","id":"Tc00da1a6d-eea1-45d8-a30f-ca08f2f43809","value":"105.4"},
            {"name":"Mac Jones","pos":"QB","id":"T48f87c0a-3a42-4768-b0ff-27f01509dda7","value":"103.8"},
            {"name":"Tua Tagovailoa","pos":"QB","id":"T6ffe012b-d908-4d86-895f-760206234866","value":"102.6"},
            {"name":"Geno Smith","pos":"QB","id":"T7a1234cd-9e8f-4a5b-8c7d-6e5f4a3b2c1d","value":"100.4"},
            {"name":"Kirk Cousins","pos":"QB","id":"T8b2345de-0f9a-5b6c-9d8e-7f6a5b4c3d2e","value":"98.7"},
            {"name":"Derek Carr","pos":"QB","id":"T9c3456ef-1a0b-6c7d-0e9f-8a7b6c5d4e3f","value":"96.5"},
            {"name":"Russell Wilson","pos":"QB","id":"T0d4567fa-2b1c-7d8e-1f0a-9b8c7d6e5f4a","value":"94.2"},
            {"name":"Aaron Rodgers","pos":"QB","id":"T1e5678ab-3c2d-8e9f-2a1b-0c9d8e7f6a5b","value":"91.8"},
        ]
    })

@app.get("/playoffs", response_class=HTMLResponse)
def playoffs(request: Request):
    return templates.TemplateResponse("playoffs.html", {"request": request})

@app.get("/_health", response_class=HTMLResponse)
def health():
    return HTMLResponse("<pre>{\"ok\": true, \"ui\": \"templates\", \"port\": 8000}</pre>")
