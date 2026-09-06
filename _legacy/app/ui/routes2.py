from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Franchise Football — Test UI v2</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  body { font-family: system-ui,Segoe UI,Roboto,Arial,sans-serif; margin: 24px; }
  h1 { margin-top: 0; }
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
<h1>Franchise Football — Local Test UI v2</h1>

<div class="row">
  <button id="btn-seed">Seed Teams</button>
  <input id="season" value="2025" />
  <button id="btn-sched1">Build Week 1</button>
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
  <button id="btn-health">Health</button>
  <button id="btn-mod">Modules</button>
  <button id="btn-cal">Calibration</button>
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
const log = (o)=>document.getElementById('log').textContent=(typeof o==='string')?o:JSON.stringify(o,null,2);
async function call(m,p){ const r=await fetch(p,{method:m}); const t=await r.text(); try{return{status:r.status,json:JSON.parse(t)}}catch{return{status:r.status,text:t}}}
function statusDot(r){ document.getElementById('status').innerHTML=(r.status===200)?'<span class="ok">OK</span>':'<span class="fail">FAIL</span>'; }

async function seed(){ const r=await call('POST','/api/sim/seed-teams'); log(r); statusDot(r); }
async function sched1(){ const s=season.value||'2025'; const r=await call('POST',`/api/sim/schedule/${s}`); log(r); statusDot(r); }
async function schedAll(){ const s=season.value||'2025'; const r=await call('POST',`/api/sim/schedule-all/${s}`); log(r); statusDot(r); }
async function play(){ const s=season.value||'2025'; const w=week.value||'1'; const r=await call('POST',`/api/sim/play-week/${s}/${w}`); log(r); statusDot(r); }
async function playSeason(){ const s=season.value||'2025'; const r=await call('POST',`/api/sim/play-season/${s}`); log(r); statusDot(r); }
async function loadGames(){
  const s=season.value||'2025', w=week.value||'1';
  const r=await call('GET',`/api/sim/games/${s}/${w}`); log(r); statusDot(r);
  if(r.json&&r.json.games){
    const body=document.querySelector('#games tbody'); body.innerHTML='';
    for(const g of r.json.games){
      const tr=document.createElement('tr');
      tr.innerHTML=`<td>${g.id}</td><td>${g.season}</td><td>${g.week}</td><td>${g.home_team_id}</td><td>${g.away_team_id}</td><td>${g.home_score}</td><td>${g.away_score}</td><td>${g.status}</td>`;
      body.appendChild(tr);
    }
  }
}
async function pbp(){ const s=season.value||'2025', w=week.value||'1'; const r=await call('GET',`/api/sim/pbp/${s}/${w}`); log(r); statusDot(r); }
async function team(){ const s=season.value||'2025', w=week.value||'1'; const r=await call('GET',`/api/sim/team-stats/${s}/${w}`); log(r); statusDot(r); }
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
document.getElementById('btn-standings').onclick=async()=>{
  const s=season.value||'2025';
  const r=await call('GET',`/api/sim/standings/${s}`); log(r); statusDot(r);
  if(r.json&&r.json.standings){
    const body=document.querySelector('#standings tbody'); body.innerHTML='';
    for(const row of r.json.standings){
      const tr=document.createElement('tr');
      tr.innerHTML=`<td>${row.rank}</td><td>${row.abbr}</td><td>${row.wins}</td><td>${row.losses}</td><td>${row.ties}</td><td>${row.pf}</td><td>${row.pa}</td><td>${row.power}</td>`;
      body.appendChild(tr);
    }
  }
};

health();
</script>
</body></html>
"""
@router.get("/ui2", response_class=HTMLResponse)
def ui2_root():
    return HTMLResponse(content=_HTML)
