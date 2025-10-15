from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

app = FastAPI(title="Franchise Football UI")

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
TPL_DIR = os.path.join(BASE_DIR, "templates")

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TPL_DIR)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "origin": request.base_url._url.rstrip("/")})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_v2(request: Request):
    return templates.TemplateResponse("dashboard_v2.html", {"request": request})

@app.get("/api/dashboard_demo", response_class=JSONResponse)
async def dashboard_demo():
    # Dummy data shaped to match the screenshots
    return JSONResponse({
        "standings": [
            {"team":"—","w":0,"l":0},
        ],
        "schedule": [
            {"week":"Week 1","home":True,"opp":"Buffalo","result":"W","line":"24—21"},
            {"week":"Week 2","home":False,"opp":"Miami","result":"L","line":"17—28"},
            {"week":"Week 3","home":True,"opp":"New York","result":"W","line":"31—14"},
            {"week":"Week 4","home":False,"opp":"Baltimore","result":"L","line":"20—27"},
            {"week":"Week 5","home":True,"opp":"Cincinnati","result":"W","line":"35—21"},
        ],
        "scouting": {
            "stats": [
                {"rank":"—","stat":"Points Per Game","value":"24.5"},
                {"rank":"—","stat":"Yards per Play","value":"5.8"},
                {"rank":"—","stat":"3rd Down Conversion %","value":"42.3%"},
                {"rank":"—","stat":"Red Zone TD %","value":"68.2%"},
                {"rank":"—","stat":"Turnovers Committed","value":"1.2"},
                {"rank":"—","stat":"OL Sack Rate %","value":"6.8%"},
                {"rank":"—","stat":"Yds Before Contact/Rush","value":"2.1"},
            ],
            "top": [
                {"name":"Mac Jones","pos":"QB","value":"QB Rating 103.8"},
                {"name":"R. Stevenson","pos":"RB","value":"Yards 1,122"},
                {"name":"J. Smith-Schuster","pos":"WR","value":"Yards 988"},
            ]
        },
        "power": [
            {"team":"—","score":"1500 → 0"},
            {"team":"—","score":"1500 → 0"},
            {"team":"—","score":"1500 → 0"},
            {"team":"—","score":"1500 → 0"},
            {"team":"—","score":"1500 → 0"},
            {"team":"—","score":"1500 → 0"},
        ],
        "box": {
            "home":{"abbr":"NE","name":"New England Patriots","quarters":[0,0,0,0],"total":0},
            "away":{"abbr":"BUF","name":"Buffalo Bills","quarters":[0,0,0,0],"total":0}
        },
        "teamTop": {
            "Passing":[{"name":"Casey Allen","pos":"QB","line":"0/0, 0 TD"}],
            "Rushing":[{"name":"Jordan Moss","pos":"RB","line":"0 att, 0 TD"}],
            "Receiving":[{"name":"Terry Hill","pos":"WR","line":"0 rec, 0 TD"}],
            "Defense":[
                {"name":"Chris Harris","pos":"LB","line":"0 sacks, 0 INT"},
                {"name":"Sam Jackson","pos":"DE","line":"1.8 sacks, 0 INT"},
                {"name":"Alex Brown","pos":"DB","line":"0 sacks, 1 INT"}
            ]
        },
        "leagueTop": [
            {"name":"Chris White","pos":"QB","id":"T231bb4f7-6537-4729-a456-87ab8e520378","value":"103.8"},
            {"name":"Casey Jones","pos":"QB","id":"Ta3420f4b-0c95-45a0-bafb-5a0b60d454b1","value":"102.6"},
            {"name":"Jalen Jackson","pos":"QB","id":"Tc00da1a6d-eea1-45d8-a30f-ca08f2f43809","value":"100.4"},
            {"name":"Devin Smith","pos":"QB","id":"T48f87c0a-3a42-4768-b0ff-27f01509dda7","value":"96.7"},
            {"name":"Derek White","pos":"QB","id":"T6ffe012b-d908-4d86-895f-760206234866","value":"96"}
        ]
    })

@app.get("/_health", response_class=HTMLResponse)
def health():
    return HTMLResponse("<pre>{\"ok\": true, \"ui\": \"templates\", \"port\": 8000}</pre>")
