// Standings widget with AFC/NFC segment + left/right division pager.
// Tries /api/standings?conf=AFC&div=East, falls back to per-division demo data.

const TBODY   = document.getElementById('std-tbody');
const DIVNAME = document.getElementById('std-division-name');
const DEMO    = document.getElementById('std-demo');

const BTN_AFC = document.getElementById('seg-afc');
const BTN_NFC = document.getElementById('seg-nfc');
const BTN_L   = document.getElementById('std-left');
const BTN_R   = document.getElementById('std-right');

// Order we cycle through
const ORDER = [
  {conf:'AFC', div:'East'}, {conf:'AFC', div:'North'}, {conf:'AFC', div:'South'}, {conf:'AFC', div:'West'},
  {conf:'NFC', div:'East'}, {conf:'NFC', div:'North'}, {conf:'NFC', div:'South'}, {conf:'NFC', div:'West'},
];
let idx = 0;

export async function initStandings(){
  wireControls();
  idx = 0; // start at AFC East
  await loadCurrent();
}

function wireControls(){
  BTN_AFC.addEventListener('click', async () => { idx = 0; await loadCurrent(); });
  BTN_NFC.addEventListener('click', async () => { idx = 4; await loadCurrent(); });
  BTN_L.addEventListener('click', async () => { if(idx>0){ idx--; await loadCurrent(); } });
  BTN_R.addEventListener('click', async () => { if(idx<ORDER.length-1){ idx++; await loadCurrent(); } });
  // Keyboard arrows when focused on any of these controls
  [BTN_AFC, BTN_NFC, BTN_L, BTN_R].forEach(b=>{
    b.addEventListener('keydown', async (e)=>{
      if(e.key==='ArrowLeft'){ BTN_L.click(); }
      if(e.key==='ArrowRight'){ BTN_R.click(); }
    });
  });
}

async function loadCurrent(){
  const {conf, div} = ORDER[idx];
  toggleSeg(conf);
  setArrows();
  DIVNAME.textContent = `${conf} ${div}`;
  let payload;
  try{
    DEMO.hidden = true;
    const url = `/api/standings?conf=${encodeURIComponent(conf)}&div=${encodeURIComponent(div)}`;
    const r = await fetch(url, {headers:{'Accept':'application/json'}});
   if(!r.ok) throw new Error('status '+r.status);
    payload = await r.json();
  }catch(_){
    DEMO.hidden = false;
    payload = demoStandings(conf, div);
  }
  renderStandings(payload);
}

function toggleSeg(conf){
  const isA = conf==='AFC';
  BTN_AFC.classList.toggle('active', isA);
  BTN_AFC.setAttribute('aria-selected', String(isA));
  BTN_NFC.classList.toggle('active', !isA);
  BTN_NFC.setAttribute('aria-selected', String(!isA));
}
function setArrows(){
  BTN_L.disabled = (idx===0);
  BTN_R.disabled = (idx===ORDER.length-1);
}

function renderStandings(data){
  const teams = Array.isArray(data?.teams) ? data.teams.slice() : [];
  teams.sort((a,b)=>{
    const pa = winPct(a), pb = winPct(b);
    if(pb !== pa) return pb - pa;
    const da = (a.pf||0)-(a.pa||0), db = (b.pf||0)-(b.pa||0);
    return db - da;
  });
  TBODY.innerHTML = teams.map(rowHtml).join('');
}

function rowHtml(t){
  const abbr = normalizeAbbr(t.abbr || t.team || '');
  const name = t.name || teamNameFromAbbr(abbr) || abbr;
  const w = t.w|0, l = t.l|0, tt = t.t|0;
  const pf = t.pf|0, pa = t.pa|0;
  const pct = toPct(winPct(t));
  const home = `${t.home_w|0}-${t.home_l|0}`;
  const away = `${t.away_w|0}-${t.away_l|0}`;
  const strkVal = Number.isFinite(t.streak) ? t.streak : 0;
  const strk = streakStr(strkVal);
  const strkClass = strkVal>=0 ? 'win':'loss';
  return `
    <tr>
      <td><div class="std-team"><span class="std-abbr">${abbr}</span><span class="std-name">${name}</span></div></td>
      <td>${w}</td><td>${l}</td><td>${tt}</td>
      <td class="std-pct">${pct}</td>
      <td>${pf}</td><td>${pa}</td>
      <td>${home}</td><td>${away}</td>
      <td class="std-strk ${strkClass}">${strk}</td>
    </tr>`;
}

function winPct(t){ const w=t.w|0,l=t.l|0,tt=t.t|0,g=w+l+tt; return g? (w+0.5*tt)/g : 0; }
function toPct(x){ return x===0 ? '.000' : ('.' + Math.round(x*1000).toString().padStart(3,'0')); }
function streakStr(s){ if(!s) return '–'; const n=Math.abs(s); return (s>0?'W':'L')+n; }
function normalizeAbbr(a){ const up=String(a||'').toUpperCase(); if(up==='BUFF') return 'BUF'; return up; }
function teamNameFromAbbr(ab){
  const map={
    // AFC
    NE:'Patriots', BUF:'Bills', MIA:'Dolphins', NYJ:'Jets',
    BAL:'Ravens', CIN:'Bengals', CLE:'Browns', PIT:'Steelers',
    JAX:'Jaguars', HOU:'Texans', IND:'Colts', TEN:'Titans',
    KC:'Chiefs', LAC:'Chargers', LV:'Raiders', DEN:'Broncos',
    // NFC
    DAL:'Cowboys', PHI:'Eagles', NYG:'Giants', WAS:'Commanders',
    GB:'Packers', DET:'Lions', MIN:'Vikings', CHI:'Bears',
    TB:'Buccaneers', ATL:'Falcons', CAR:'Panthers', NO:'Saints',
    SF:'49ers', SEA:'Seahawks', LAR:'Rams', ARI:'Cardinals'
  }; return map[ab];
}

function demoStandings(conf, div){
  // Minimal demo rows per division (numbers are placeholders)
  const bank = {
    'AFC East':  [['NE','Patriots'],['BUF','Bills'],['MIA','Dolphins'],['NYJ','Jets']],
    'AFC North': [['BAL','Ravens'],['CIN','Bengals'],['CLE','Browns'],['PIT','Steelers']],
    'AFC South': [['JAX','Jaguars'],['HOU','Texans'],['IND','Colts'],['TEN','Titans']],
    'AFC West':  [['KC','Chiefs'],['LAC','Chargers'],['LV','Raiders'],['DEN','Broncos']],
    'NFC East':  [['DAL','Cowboys'],['PHI','Eagles'],['NYG','Giants'],['WAS','Commanders']],
    'NFC North': [['GB','Packers'],['DET','Lions'],['MIN','Vikings'],['CHI','Bears']],
    'NFC South': [['TB','Buccaneers'],['ATL','Falcons'],['CAR','Panthers'],['NO','Saints']],
    'NFC West':  [['SF','49ers'],['SEA','Seahawks'],['LAR','Rams'],['ARI','Cardinals']],
  };
  const key = `${conf} ${div}`;
  const rows = (bank[key] || []).map(([abbr,name],i)=>({
    abbr, name,
    w: Math.max(0, 4 - i), l: Math.min(6, 2 + i), t: 0,
    pf: 150 - i*7, pa: 120 + i*8,
    home_w: Math.max(0, 2 - i%2), home_l: i%2 + 1,
    away_w: Math.max(0, 2 - (i>1?1:0)), away_l: (i>1?2:1),
    streak: i===0 ? 3 : -i  // W3, L1, L2, ...
  }));
  return { division: key, teams: rows };
}

// Auto-init when present
if (TBODY) { initStandings(); }