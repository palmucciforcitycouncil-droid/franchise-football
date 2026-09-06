from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")

_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Franchise Football - Local Test UI</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  body { font-family: system-ui,Segoe UI,Roboto,Arial,sans-serif; margin: 24px; }
  .row { display:flex; flex-wrap:wrap; gap:12px; margin-bottom:12px; }
  button { padding:8px 12px; border-radius:8px; border:1px solid #ccc; cursor:pointer; }
  input { padding:8px; border-radius:6px; border:1px solid #ccc; width:110px; }
  pre { background:#111; color:#0f0; padding:12px; border-radius:8px; max-height:260px; overflow:auto; }
  table { border-collapse:collapse; width:100%; margin-top:12px; }
  th, td { border:1px solid #ddd; padding:6px 8px; text-align:left; }
  th { background:#f4f4f4; }
  .ok { color:#067d00; font-weight:600; }
  .fail { color:#b10000; font-weight:600; }
</style>
</head>
<body>
<h1>Franchise Football - Local Test UI</h1>

<div class="row">
  <button id="btn-seed">Seed Teams (32)</button>
  <input id="season" value="2025" />
  <button id="btn-sched1">Build Week 1 Schedule</button>
  <button id="btn-schedAll">Build Full Schedule (18w)</button>
  <input id="week" value="1" />
  <button id="btn-play">Play Week</button>
  <button id="btn-playSeason">Play Season</button>
  <button id="btn-load">View Games</button>
  <button id="btn-pbp">View PBP</button>
  <button id="btn-team">Team Stats</button>
  <button id="btn-standings">Standings</button>
</div>

<div class="row">
  <button id="btn-health">Check Health</button>
  <button id="btn-mod">Check Modules</button>
  <button id="btn-cal">Check Calibration</button>
  <span id="status"></span>
</div>

<pre id="log"></pre>

<table id="games">
  <thead>
    <tr><th>ID</th><th>Season</th><th>Week</th><th>Home</th><th>Away</th><th>H</th><th>A</th><th>Status</th></tr>
  </thead><tbody></tbody>
</table>

<table id="standings" style="margin-top:16px">
  <thead>
    <tr><th>Rank</th><th>Team</th><th>W</th><th>L</th><th>T</th><th>PF</th><th>PA</th><th>Power</th></tr>
  </thead><tbody></tbody>
</table>

<script>
const log = (o) => document.getElementById('log').textContent = (typeof o==='string')?o:JSON.stringify(o,null,2);
async function call(m, p){ const r=await fetch(p,{method:m}); const t=await r.text(); try{ return {status:r.status,json:JSON.parse(t)} }catch{ return {status:r.status,text:t} } }
function statusDot(r){ document.getElementById('status').innerHTML=(r.status===200)?'<span class="ok">OK</span>':'<span class="fail">FAIL</span>'; }

function S(){ return (document.getElementById('season').value || '2025').trim(); }
function W(){
  // force integer 1..18
  const raw = (document.getElementById('week').value || '1').trim();
  let n = parseInt(raw, 10);
  if (Number.isNaN(n)) n = 1;
  if (n < 1) n = 1;
  if (n > 18) n = 18;
  document.getElementById('week').value = String(n); // normalize field
  return n;
}

async function seed(){ const r=await call('POST','/api/sim/seed-teams'); log(r); statusDot(r); }
async function sched1(){ const r=await call('POST',/api/sim/schedule/); log(r); statusDot(r); }
async function schedAll(){ const r=await call('POST',/api/sim/schedule-all/); log(r); statusDot(r); }
async function play(){ const r=await call('POST',/api/sim/play-week//); log(r); statusDot(r); }
async function playSeason(){ const r=await call('POST',/api/sim/play-season/); log(r); statusDot(r); }

async function loadGames(){
  const r=await call('GET',/api/sim/games//); log(r); statusDot(r);
  if(r.json&&r.json.games){
    const body=document.querySelector('#games tbody'); body.innerHTML='';
    for(const g of r.json.games){
      const tr=document.createElement('tr');
      tr.innerHTML=<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>;
      body.appendChild(tr);
    }
  }
}
async function pbp(){ const r=await call('GET',/api/sim/pbp//); log(r); statusDot(r); }
async function team(){ const r=await call('GET',/api/sim/team-stats//); log(r); statusDot(r); }
async function health(){ const r=await call('GET','/diag/health'); log(r); statusDot(r); }
async function modules(){ const r=await call('GET','/diag/modules'); log(r); statusDot(r); }
async function calib(){ const r=await call('GET','/diag/calibration'); log(r); statusDot(r); }

document.getElementById('btn-seed').onclick=seed;
document.getElementById('btn-sched1').onclick=sched1;
document.getElementById('btn-schedAll').onclick=schedAll;
document.getElementById('btn-play').onclick=play;
document.getElementById('btn-playSeason').onclick=playSeason;
document.getElementById('btn-load').onclick=loadGames;
document.getElementById('btn-pbp').onclick=pbp;
document.getElementById('btn-team').onclick=team;
document.getElementById('btn-standings').onclick=async ()=>{
  const r=await call('GET',/api/sim/standings/); log(r); statusDot(r);
  if(r.json&&r.json.standings){
    const body=document.querySelector('#standings tbody'); body.innerHTML='';
    for(const row of r.json.standings){
      const tr=document.createElement('tr');
      tr.innerHTML=<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>;
      body.appendChild(tr);
    }
  }
};

health();
</script>
</body></html>
"""

@router.get("/ui", response_class=HTMLResponse)
def ui_root():
    return HTMLResponse(content=_HTML, headers={"Cache-Control": "no-store"})

@router.get("/draft", response_class=HTMLResponse)
async def draft_page(request: Request):
    # Mock data - in real implementation, get from database
    context = {
        "request": request,
        "user_team_id": 1,  # Get from user context
        "current_season": 2025,  # Get from league state
    }
    return templates.TemplateResponse("draft.html", context)
